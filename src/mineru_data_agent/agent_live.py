"""LLM-driven Agent loop with real OpenAI-compatible tool calling.

This is the live counterpart to the deterministic Agent in ``agent.py``.
The LLM is the planner: it picks which tool to call next, when to validate,
when to retry, when to recover, and when to stop. Tools wrap the existing
parser, validator, extractor, retrieval and recovery modules so the LLM
operates on the same surface the rule-based Agent does.

Design constraints:
- No new third-party deps. Uses ``httpx`` which is already a project dep.
- API key is read from env only. Never written to artifacts.
- Every LLM turn and tool call is recorded with timestamps, token usage,
  and full I/O previews. The resulting trace is what reviewers should
  read to verify "the LLM, not a hard-coded rule, made these decisions".
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from .extractors import (
    build_extracted_view,
    extract_docx,
    extract_html,
    extract_pptx,
    read_content_list,
    read_markdown,
)
from .llm_client import _chat_completions_url, _sanitize_error_text
from .mineru_client import MinerURunner
from .recovery import clean_text_artifacts
from .retrieval_exporter import build_retrieval_export
from .validators import build_quality_report


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MAX_TURNS = 12
DEFAULT_MAX_TOKENS = 1024
DEFAULT_TIMEOUT = 120.0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _preview(value: Any, limit: int = 1200) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    text = _scrub_text(text)
    if len(text) <= limit:
        return text
    return text[:limit] + f"... [truncated, total {len(text)} chars]"


def _scrub_text(text: str, api_key: str | None = None) -> str:
    clean = text
    for raw in {str(PROJECT_ROOT), str(PROJECT_ROOT).replace("\\", "\\\\"), str(Path.home()), str(Path.home()).replace("\\", "\\\\")}:
        clean = clean.replace(raw, "<PROJECT_ROOT>" if "data_agent" in raw else "<USER_HOME>")
    if api_key:
        clean = _sanitize_error_text(clean, api_key=api_key)
    return clean


def _display_path(path: str | Path) -> str:
    target = Path(path)
    try:
        return str(target.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")
    except Exception:
        return _scrub_text(str(path))


def _scrub_json_value(value: Any) -> Any:
    if isinstance(value, str):
        return _scrub_text(value)
    if isinstance(value, list):
        return [_scrub_json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _scrub_json_value(item) for key, item in value.items()}
    return value


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


class AgentState:
    """Mutable workspace the tools read/write."""

    def __init__(self, *, input_path: Path, output_dir: Path) -> None:
        self.input_path = input_path
        self.output_dir = output_dir
        self.parses: dict[str, dict[str, Any]] = {}
        self.extracted: dict[str, Any] | None = None
        self.quality: dict[str, Any] | None = None
        self.retrieval: dict[str, Any] | None = None
        self.notes: list[str] = []


def _resolve_path(raw: str | None, state: AgentState) -> Path:
    if raw is None:
        target = state.input_path.resolve()
    else:
        candidate = Path(raw)
        if candidate.is_absolute():
            target = candidate.resolve()
        else:
            target = (state.input_path.parent / candidate).resolve()
    allowed_root = state.input_path.parent.resolve()
    if not target.is_relative_to(allowed_root):
        raise ValueError("path outside allowed input directory")
    if not target.exists():
        raise ValueError("path does not exist in allowed input directory")
    if target.is_dir():
        raise ValueError("path points to a directory, not a file")
    return target


def _tool_parse_html(state: AgentState, *, path: str | None = None) -> dict[str, Any]:
    target = _resolve_path(path, state)
    if not target.exists():
        return {"ok": False, "error": f"file not found: {target}"}
    if target.suffix.lower() not in {".html", ".htm"}:
        return {"ok": False, "error": f"not an HTML file: {target.suffix}"}
    markdown, content = extract_html(target)
    state.parses["html"] = {"markdown": markdown, "content_list": content, "source": str(target)}
    return {
        "ok": True,
        "markdown_chars": len(markdown),
        "blocks": len(content),
        "preview": markdown[:600],
    }


def _tool_parse_office(state: AgentState, *, path: str | None = None) -> dict[str, Any]:
    target = _resolve_path(path, state)
    if not target.exists():
        return {"ok": False, "error": f"file not found: {target}"}
    suffix = target.suffix.lower()
    if suffix == ".docx":
        markdown, content = extract_docx(target)
        kind = "docx"
    elif suffix == ".pptx":
        markdown, content = extract_pptx(target)
        kind = "pptx"
    else:
        return {"ok": False, "error": f"unsupported office suffix: {suffix}"}
    state.parses[kind] = {"markdown": markdown, "content_list": content, "source": str(target)}
    return {
        "ok": True,
        "kind": kind,
        "markdown_chars": len(markdown),
        "blocks": len(content),
        "preview": markdown[:600],
    }


def _tool_parse_pdf(state: AgentState, runner: MinerURunner, *, path: str | None = None, method: str = "auto", lang: str = "ch") -> dict[str, Any]:
    target = _resolve_path(path, state)
    if not target.exists():
        return {"ok": False, "error": f"file not found: {target}"}
    if target.suffix.lower() != ".pdf":
        return {"ok": False, "error": f"not a PDF: {target.suffix}"}
    try:
        artifacts, tool_call = runner.parse(
            input_path=target,
            output_dir=state.output_dir / "mineru",
            method=method,
            lang=lang,
        )
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"mineru runner failed: {exc}"}
    markdown = read_markdown(artifacts.markdown_path)
    content = read_content_list(artifacts.content_list_path)
    state.parses["pdf"] = {
        "markdown": markdown,
        "content_list": content,
        "source": str(target),
        "artifacts": artifacts.to_jsonable(),
    }
    return {
        "ok": True,
        "kind": "pdf",
        "markdown_chars": len(markdown),
        "blocks": len(content),
        "preview": markdown[:600],
        "tool_status": tool_call.status,
        "elapsed_seconds": tool_call.elapsed_seconds,
    }


def _tool_build_extracted(state: AgentState) -> dict[str, Any]:
    if not state.parses:
        return {"ok": False, "error": "no parsed document yet; call a parse_* tool first"}
    primary = next(iter(state.parses.values()))
    extracted = build_extracted_view(
        markdown=primary["markdown"],
        content_list=primary["content_list"],
    )
    state.extracted = extracted
    summary = {
        "ok": True,
        "sections": len(extracted.get("sections", [])),
        "tables": len(extracted.get("tables", [])),
        "numeric_facts": len(extracted.get("numeric_facts", [])),
        "key_values": len(extracted.get("key_values", [])),
    }
    return summary


def _tool_validate_quality(state: AgentState, *, profile: str = "general_document", task: str = "") -> dict[str, Any]:
    if not state.extracted:
        return {"ok": False, "error": "extracted view not built; call build_extracted first"}
    primary = next(iter(state.parses.values()))
    quality = build_quality_report(primary["markdown"], state.extracted, profile, task)
    state.quality = quality
    return {
        "ok": True,
        "score": quality["score"],
        "status": quality["status"],
        "issue_count": quality["issue_count"],
        "issue_codes": [i["code"] for i in quality["issues"]],
    }


def _tool_clean_text(state: AgentState) -> dict[str, Any]:
    if not state.parses:
        return {"ok": False, "error": "nothing to clean; parse first"}
    primary_key = next(iter(state.parses))
    primary = state.parses[primary_key]
    cleaned_markdown, cleaned_content = clean_text_artifacts(primary["markdown"], primary["content_list"])
    delta = len(primary["markdown"]) - len(cleaned_markdown)
    primary["markdown"] = cleaned_markdown
    primary["content_list"] = cleaned_content
    state.extracted = None
    state.quality = None
    return {"ok": True, "removed_chars": delta, "new_length": len(cleaned_markdown), "blocks": len(cleaned_content)}


def _tool_export_retrieval(state: AgentState) -> dict[str, Any]:
    if not state.extracted:
        return {"ok": False, "error": "no extracted view; build_extracted first"}
    primary = next(iter(state.parses.values()))
    retrieval_dir = state.output_dir / "retrieval"
    retrieval_dir.mkdir(parents=True, exist_ok=True)
    export = build_retrieval_export(
        markdown=primary["markdown"],
        content_list=primary["content_list"],
        output_dir=retrieval_dir,
        doc_id=state.input_path.stem,
        source_file=state.input_path,
    )
    state.retrieval = export
    return {
        "ok": True,
        "chunks": export.get("stats", {}).get("total_chunks", 0),
        "manifest": export.get("manifest_path"),
    }


def _tool_query_extracted(state: AgentState, *, query: str, limit: int = 5) -> dict[str, Any]:
    if not state.extracted:
        return {"ok": False, "error": "no extracted view"}
    primary = next(iter(state.parses.values()))
    text = primary["markdown"].lower()
    q = query.lower().strip()
    hits = []
    if not q:
        return {"ok": False, "error": "query must not be empty"}
    for section in state.extracted.get("sections", [])[:200]:
        body = (section.get("text") or "").lower()
        if q in body or q in section.get("title", "").lower():
            hits.append({"type": "section", "title": section.get("title"), "snippet": (section.get("text") or "")[:300]})
        if len(hits) >= limit:
            break
    if len(hits) < limit:
        for table in state.extracted.get("tables", [])[:50]:
            table_text = json.dumps(table, ensure_ascii=False).lower()
            if q in table_text:
                hits.append({"type": "table", "title": table.get("title"), "snippet": json.dumps(table, ensure_ascii=False)[:500]})
            if len(hits) >= limit:
                break
    if len(hits) < limit:
        for item in state.extracted.get("key_values", [])[:200]:
            item_text = json.dumps(item, ensure_ascii=False).lower()
            if q in item_text:
                hits.append({"type": "key_value", "snippet": json.dumps(item, ensure_ascii=False)[:300]})
            if len(hits) >= limit:
                break
    if len(hits) < limit:
        for item in state.extracted.get("numeric_facts", [])[:200]:
            item_text = json.dumps(item, ensure_ascii=False).lower()
            if q in item_text:
                hits.append({"type": "numeric_fact", "snippet": json.dumps(item, ensure_ascii=False)[:300]})
            if len(hits) >= limit:
                break
    return {"ok": True, "matches": hits, "raw_text_match_count": text.count(q)}


def _tool_finalize(state: AgentState, *, answer: str, evidence: list[str] | None = None) -> dict[str, Any]:
    state.notes.append(f"final_answer: {answer}")
    return {"ok": True, "answer": answer, "evidence": evidence or []}


TOOL_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "parse_html",
            "description": "Parse an HTML/HTM file. Omit path to use the input file from the user message.",
            "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "Optional relative path under the input file directory. Omit to use the default input file."}}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "parse_office",
            "description": "Parse a DOCX or PPTX file. Omit path to use the input file from the user message.",
            "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "Optional relative path under the input file directory. Omit to use the default input file."}}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "parse_pdf",
            "description": "Parse a PDF with MinerU. Omit path to use the input file. Prefer method=ocr for scanned or low-quality PDFs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Optional relative path under the input file directory. Omit to use the default input file."},
                    "method": {"type": "string", "enum": ["auto", "ocr", "txt"]},
                    "lang": {"type": "string", "enum": ["ch", "en"]},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "build_extracted",
            "description": "Build structured view (sections, tables, key_values, numeric_facts, semantic_signals) from the current parse.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "validate_quality",
            "description": "Run validators to score quality, detect mojibake, missing page provenance, weak structure, numeric anomalies. Returns issue codes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "profile": {"type": "string"},
                    "task": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "clean_text",
            "description": "Recovery: strip mojibake/encoding noise from current markdown. Use when validate_quality reports text_encoding_noise. After cleaning, you MUST call build_extracted and validate_quality again.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "export_retrieval",
            "description": "Export retrieval chunks (JSONL + manifest) for downstream RAG/search. Call once near the end.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_extracted",
            "description": "Search the current extracted view by keyword. Returns matching sections with snippets. Use to ground your final answer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finalize",
            "description": "Submit the final answer for the user task. Provide the answer and an evidence list (snippets/section titles you grounded on). After calling this the agent loop ends.",
            "parameters": {
                "type": "object",
                "properties": {
                    "answer": {"type": "string"},
                    "evidence": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["answer"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# LLM driver
# ---------------------------------------------------------------------------


@dataclass
class LiveTurn:
    turn_index: int
    role: str
    started_at: str
    ended_at: str | None = None
    request_messages_preview: list[dict[str, Any]] = field(default_factory=list)
    response_message: dict[str, Any] | None = None
    tool_call: dict[str, Any] | None = None
    tool_result_preview: str | None = None
    usage: dict[str, int] | None = None
    error: str | None = None


@dataclass
class LiveAgentTrace:
    run_id: str
    task: str
    input_file: str
    output_dir: str
    provider: str
    model: str
    started_at: str
    turns: list[LiveTurn] = field(default_factory=list)
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    finished_at: str | None = None
    final_answer: str | None = None
    final_evidence: list[str] = field(default_factory=list)
    status: str = "running"
    error: str | None = None

    def to_jsonable(self) -> dict[str, Any]:
        return _scrub_json_value(asdict(self))


def live_trace_to_jsonable(
    trace: LiveAgentTrace,
    *,
    output_root: str | Path | None = None,
    display_paths: bool = False,
) -> dict[str, Any]:
    output_dir = Path(trace.output_dir)
    path_value = _display_path if display_paths else lambda value: str(Path(value))
    tool_sequence = [turn.tool_call["name"] for turn in trace.turns if turn.tool_call]
    tool_call_completed = trace.status == "completed" and trace.total_tokens > 0 and "finalize" in tool_sequence
    quality_status = "unreviewed" if tool_call_completed else "not_applicable"
    notes = ["answer quality requires manual or benchmark review"] if tool_call_completed else []
    response = {
        "agent_mode": "live_tool_calling",
        "status": trace.status,
        "run_id": trace.run_id,
        "provider": trace.provider,
        "model": trace.model,
        "task": trace.task,
        "input_file": path_value(trace.input_file),
        "output_dir": path_value(output_dir),
        "tool_sequence": tool_sequence,
        "tool_call_completed": tool_call_completed,
        "live_evidence": tool_call_completed,
        "answer_quality_pass": None,
        "quality_review": {"status": quality_status, "notes": notes},
        "turns": len(trace.turns),
        "tokens": {
            "prompt": trace.prompt_tokens,
            "completion": trace.completion_tokens,
            "total": trace.total_tokens,
        },
        "final_answer": trace.final_answer,
        "evidence": trace.final_evidence,
        "trace_path": path_value(output_dir / "live_agent_trace.json"),
        "summary_path": path_value(output_dir / "live_agent_summary.md"),
        "result_path": path_value(output_dir / "result.json"),
        "error": trace.error,
    }
    if output_root is not None:
        response["api_output_root"] = path_value(Path(output_root))
    return _scrub_json_value(response)


def _system_prompt() -> str:
    return (
        "You are MinerU Data Agent — a tool-using planner for document understanding tasks.\n"
        "You receive a user task and an input file path. Decide which tools to call and in what order.\n\n"
        "WORKFLOW:\n"
        "1. Call the appropriate parser (parse_pdf / parse_html / parse_office) first. "
        "Do NOT pass any path argument — omit 'path' entirely to use the default input file.\n"
        "2. Call build_extracted, then validate_quality with the right profile and task description.\n"
        "3. If validate_quality reports 'text_encoding_noise' or 'mojibake', call clean_text then re-run build_extracted+validate_quality.\n"
        "4. Use query_extracted to ground specific facts before answering.\n"
        "5. Call export_retrieval once near the end.\n"
        "6. Call finalize with a concrete answer plus an evidence list.\n\n"
        "RULES:\n"
        "- Only ONE tool call per turn.\n"
        "- Never invent values. If information is not in the document, call finalize with an explicit 'not_found' explanation.\n"
        "- Keep reasoning concise.\n"
    )


def _post_chat(
    *,
    api_key: str,
    base_url: str,
    model: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    max_tokens: int,
    timeout: float,
) -> dict[str, Any]:
    url = _chat_completions_url(base_url)
    payload = {
        "model": model,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
        "max_tokens": max_tokens,
    }
    last_error: str | None = None
    for attempt in range(5):
        try:
            response = httpx.post(
                url,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=timeout,
            )
            if response.status_code == 429:
                last_error = f"HTTP 429: {_scrub_text(response.text[-500:], api_key)}"
                backoff = 2.0 * (attempt + 1) + 1.0
                time.sleep(backoff)
                continue
            response.raise_for_status()
            try:
                return response.json()
            except ValueError as exc:
                last_error = f"invalid JSON response: {_scrub_text(response.text[-500:], api_key)}"
                raise RuntimeError(last_error) from exc
        except httpx.HTTPStatusError as exc:
            last_error = f"HTTP {exc.response.status_code}: {_scrub_text(exc.response.text[-500:], api_key)}"
            if exc.response.status_code in {429, 500, 502, 503, 504}:
                time.sleep(2.0 * (attempt + 1))
                continue
            raise
        except httpx.HTTPError as exc:
            last_error = repr(exc)
            time.sleep(2.0 * (attempt + 1))
            continue
    raise RuntimeError(f"chat request failed after retries: {last_error}")


def run_live_agent(
    *,
    input_file: str | Path,
    output_root: str | Path,
    task: str,
    provider: str = "modelscope",
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    max_turns: int = DEFAULT_MAX_TURNS,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    timeout: float = DEFAULT_TIMEOUT,
    mineru_runner: MinerURunner | None = None,
    run_id: str | None = None,
) -> LiveAgentTrace:
    if provider == "modelscope":
        api_key = api_key or os.getenv("MODELSCOPE_API_KEY")
        base_url = base_url or os.getenv("MODELSCOPE_BASE_URL") or "https://api-inference.modelscope.cn/v1"
        model = model or os.getenv("MODELSCOPE_MODEL") or "deepseek-ai/DeepSeek-V4-Flash"
        key_env = "MODELSCOPE_API_KEY"
    elif provider == "deepseek":
        api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        base_url = base_url or os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com/v1"
        model = model or os.getenv("DEEPSEEK_MODEL") or "deepseek-v4-flash"
        key_env = "DEEPSEEK_API_KEY"
    else:
        raise ValueError(f"Unsupported provider: {provider}")
    if not api_key:
        raise RuntimeError(f"{key_env} is required for live agent runs")

    run_id = run_id or uuid.uuid4().hex[:12]
    input_path = Path(input_file).expanduser().resolve()
    output_dir = Path(output_root).expanduser().resolve() / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    state = AgentState(input_path=input_path, output_dir=output_dir)
    runner = mineru_runner or MinerURunner()

    trace = LiveAgentTrace(
        run_id=run_id,
        task=task,
        input_file=str(input_path),
        output_dir=str(output_dir),
        provider=provider,
        model=model,
        started_at=_now(),
    )

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _system_prompt()},
        {
            "role": "user",
            "content": (
                f"Task: {task}\n"
                f"Input file: {input_path.name} (suffix={input_path.suffix})\n"
                f"Input path is available to tools; do not repeat local filesystem paths in the final answer.\n"
                f"Plan and execute. End by calling finalize."
            ),
        },
    ]

    for turn_index in range(max_turns):
        turn = LiveTurn(
            turn_index=turn_index,
            role="assistant",
            started_at=_now(),
            request_messages_preview=[
                {"role": m["role"], "preview": _preview(m.get("content") or m.get("tool_calls") or "", 400)}
                for m in messages[-4:]
            ],
        )
        try:
            data = _post_chat(
                api_key=api_key,
                base_url=base_url,
                model=model,
                messages=messages,
                tools=TOOL_SCHEMA,
                max_tokens=max_tokens,
                timeout=timeout,
            )
        except Exception as exc:  # noqa: BLE001
            turn.error = f"chat request failed: {exc}"
            turn.ended_at = _now()
            trace.turns.append(turn)
            trace.status = "failed"
            trace.error = turn.error
            break

        usage = data.get("usage") or {}
        turn.usage = {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
        }
        trace.prompt_tokens += turn.usage["prompt_tokens"]
        trace.completion_tokens += turn.usage["completion_tokens"]
        trace.total_tokens += turn.usage["total_tokens"]

        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        turn.response_message = {
            "content": _preview(message.get("content") or "", 1000),
            "reasoning_preview": _preview(message.get("reasoning_content") or "", 600),
            "finish_reason": choice.get("finish_reason"),
            "has_tool_calls": bool(message.get("tool_calls")),
        }

        tool_calls = message.get("tool_calls") or []
        content_text = (message.get("content") or "").strip()
        # ModelScope sometimes returns HTTP 200 with an empty body when rate-limited
        # or when the model decides not to emit. Treat fully-empty turns as a soft
        # retry signal instead of silently ending the run.
        if not tool_calls and not content_text and (turn.usage or {}).get("total_tokens", 0) == 0:
            turn.error = "empty_response_likely_throttled"
            turn.ended_at = _now()
            trace.turns.append(turn)
            if turn_index < max_turns - 1:
                time.sleep(8.0 + 2.0 * turn_index)
                continue
            trace.status = "failed_empty_response"
            break
        if not tool_calls:
            turn.ended_at = _now()
            trace.turns.append(turn)
            messages.append({"role": "assistant", "content": content_text})
            if turn_index < max_turns - 1:
                messages.append(
                    {
                        "role": "user",
                        "content": "You answered without calling the finalize tool. Call finalize now with your answer and evidence.",
                    }
                )
                continue
            trace.final_answer = content_text
            trace.status = "assistant_answer_without_finalize"
            break

        call = tool_calls[0]
        fn = call.get("function") or {}
        name = fn.get("name", "")
        try:
            args = json.loads(fn.get("arguments") or "{}")
        except json.JSONDecodeError:
            args = {}
        call_id = call.get("id") or f"call_{turn_index}"

        result = _dispatch_tool(name, args, state=state, runner=runner)
        turn.tool_call = {"name": name, "arguments": args, "id": call_id}
        turn.tool_result_preview = _preview(result, 1000)
        turn.ended_at = _now()
        trace.turns.append(turn)

        assistant_msg = {
            "role": "assistant",
            "content": message.get("content") or "",
            "tool_calls": [
                {
                    "id": call_id,
                    "type": "function",
                    "function": {"name": name, "arguments": fn.get("arguments") or "{}"},
                }
            ],
        }
        tool_msg = {
            "role": "tool",
            "tool_call_id": call_id,
            "content": json.dumps(result, ensure_ascii=False, default=str)[:4000],
        }
        messages.append(assistant_msg)
        messages.append(tool_msg)

        # Anti-loop nudge: if same tool used 3+ times in a row without finalize, push the model toward finishing.
        recent = [t.tool_call["name"] for t in trace.turns[-4:] if t.tool_call]
        if len(recent) >= 3 and len(set(recent[-3:])) == 1 and recent[-1] not in {"finalize"}:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"You have called `{recent[-1]}` {len(recent)} times in a row. "
                        "Stop searching. Use what you already have, call `export_retrieval` if you haven't, "
                        "then call `finalize` with your best answer. If the information is genuinely not in the document, "
                        "finalize with an explicit 'not_found' explanation listing what IS in the document."
                    ),
                }
            )

        if name == "finalize" and result.get("ok"):
            trace.final_answer = result.get("answer")
            trace.final_evidence = result.get("evidence") or []
            trace.status = "completed"
            break
    else:
        trace.status = "max_turns_exceeded"

    trace.finished_at = _now()

    # Persist artifacts
    trace_path = output_dir / "live_agent_trace.json"
    trace_path.write_text(json.dumps(trace.to_jsonable(), ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    if state.extracted is not None:
        (output_dir / "extracted.json").write_text(
            json.dumps(_scrub_json_value(state.extracted), ensure_ascii=False, indent=2, default=str), encoding="utf-8"
        )
    if state.quality is not None:
        (output_dir / "quality.json").write_text(
            json.dumps(_scrub_json_value(state.quality), ensure_ascii=False, indent=2, default=str), encoding="utf-8"
        )
    summary = _build_summary(trace, state)
    (output_dir / "live_agent_summary.md").write_text(summary, encoding="utf-8")
    (output_dir / "result.json").write_text(
        json.dumps(live_trace_to_jsonable(trace), ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return trace


def _dispatch_tool(name: str, args: dict[str, Any], *, state: AgentState, runner: MinerURunner) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        if name == "parse_html":
            result = _tool_parse_html(state, **args)
        elif name == "parse_office":
            result = _tool_parse_office(state, **args)
        elif name == "parse_pdf":
            result = _tool_parse_pdf(state, runner, **args)
        elif name == "build_extracted":
            result = _tool_build_extracted(state)
        elif name == "validate_quality":
            result = _tool_validate_quality(state, **args)
        elif name == "clean_text":
            result = _tool_clean_text(state)
        elif name == "export_retrieval":
            result = _tool_export_retrieval(state)
        elif name == "query_extracted":
            result = _tool_query_extracted(state, **args)
        elif name == "finalize":
            result = _tool_finalize(state, **args)
        else:
            result = {"ok": False, "error": f"unknown tool: {name}"}
    except TypeError as exc:
        result = {"ok": False, "error": f"bad arguments for {name}: {exc}"}
    except Exception as exc:  # noqa: BLE001
        result = {"ok": False, "error": f"tool {name} raised: {exc}"}
    result.setdefault("_elapsed_seconds", round(time.perf_counter() - started, 4))
    return result


def _build_summary(trace: LiveAgentTrace, state: AgentState) -> str:
    lines = [
        f"# Live Agent Run {trace.run_id}",
        "",
        f"- Provider: `{trace.provider}` model `{trace.model}`",
        f"- Status: **{trace.status}**",
        f"- Task: {trace.task}",
        f"- Input: `{_display_path(trace.input_file)}`",
        f"- Started: {trace.started_at}",
        f"- Finished: {trace.finished_at}",
        f"- Turns: {len(trace.turns)}",
        f"- Tokens: prompt={trace.prompt_tokens}, completion={trace.completion_tokens}, total={trace.total_tokens}",
        "",
        "## Tool-call sequence",
        "",
    ]
    for turn in trace.turns:
        if not turn.tool_call:
            continue
        lines.append(
            f"- turn {turn.turn_index}: `{turn.tool_call['name']}` args={json.dumps(turn.tool_call['arguments'], ensure_ascii=False)}"
        )
    lines.append("")
    if trace.final_answer:
        lines.append("## Final answer")
        lines.append("")
        lines.append(trace.final_answer)
        lines.append("")
        if trace.final_evidence:
            lines.append("### Evidence")
            for ev in trace.final_evidence:
                lines.append(f"- {ev}")
    if state.quality:
        lines.append("")
        lines.append("## Quality")
        lines.append(f"- score: {state.quality.get('score')}")
        lines.append(f"- status: {state.quality.get('status')}")
        codes = [i["code"] for i in state.quality.get("issues", [])]
        lines.append(f"- issue codes: {codes}")
    return "\n".join(lines)
