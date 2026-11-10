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

import hashlib
import json
import os
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from .consistency import build_fine_grained_escalation_plan, compare_parser_outputs
from .extractors import (
    build_extracted_view,
    extract_docx,
    extract_html,
    extract_pdf_text,
    extract_pptx,
    probe_pdf_text_layer,
    read_content_list,
    read_markdown,
)
from .llm_client import _chat_completions_url, _sanitize_error_text
from .mineru_client import MinerUAgentAPIRunner, MinerUPreciseAPIRunner, MinerURunner
from .recovery import clean_text_artifacts
from .retrieval_exporter import build_retrieval_export
from .routing import build_input_metadata
from .validators import build_quality_report


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MAX_TURNS = 12
DEFAULT_MAX_TOKENS = 1024
DEFAULT_TIMEOUT = 120.0
SKILL_CATALOG_VERSION = "2026-05-25"
PDF_PARSER_CHOICES = {"auto", "local", "agent-api", "precise-api"}
PDF_BACKEND_CHOICES = {"pipeline", "vlm-transformers", "vlm-sglang-engine", "vlm-sglang-client"}
MinerUToolRunner = MinerURunner | MinerUAgentAPIRunner | MinerUPreciseAPIRunner


LIVE_AGENT_SKILLS: dict[str, dict[str, Any]] = {
    "financial_total_audit": {
        "name": "Financial total audit",
        "when_to_use": "financial reports, totals, growth rates, dense numeric tables, consistency checks",
        "objective": "extract relevant figures, verify arithmetic, and explain mismatches with evidence",
        "recommended_tools": ["parse_*", "build_extracted", "validate_quality", "query_extracted", "validate_answer", "finalize"],
        "completion_checks": [
            "answer cites exact numeric evidence",
            "answer_validation has no blocking arithmetic or unsupported-number issue",
        ],
    },
    "not_found_guard": {
        "name": "Not-found guard",
        "when_to_use": "user asks for a period/entity/field that may be absent from the document",
        "objective": "search for the requested item and nearby alternatives, then decline explicitly if absent",
        "recommended_tools": ["parse_*", "build_extracted", "query_extracted", "export_retrieval", "validate_answer", "finalize"],
        "completion_checks": [
            "not_found answer lists what was searched and what related values are actually present",
            "answer_validation has no potential_not_found_conflict issue",
        ],
    },
    "text_recovery_then_extract": {
        "name": "Text recovery then extract",
        "when_to_use": "OCR noise, mojibake, unreadable snippets, low quality scans, text_encoding_noise",
        "objective": "detect noise, clean text when needed, rebuild extraction, revalidate, and answer with remaining uncertainty",
        "recommended_tools": ["parse_*", "build_extracted", "validate_quality", "clean_text", "query_extracted", "validate_answer", "finalize"],
        "completion_checks": [
            "if quality reports text noise, clean_text is tried before final extraction",
            "answer says unreadable/not_found only after evidence search",
        ],
    },
    "contract_clause_review": {
        "name": "Contract clause review",
        "when_to_use": "contracts, obligations, parties, dispute clauses, acceptance, data security, liability",
        "objective": "extract responsibilities/clauses and rank risk using evidence rather than keyword-only matching",
        "recommended_tools": ["parse_*", "build_extracted", "validate_quality", "query_extracted", "validate_answer", "finalize"],
        "completion_checks": [
            "not_found is not used merely because the literal requested word is absent",
            "answer cites clause snippets or section titles",
        ],
    },
    "workflow_risk_review": {
        "name": "Workflow risk review",
        "when_to_use": "process diagrams, incident timelines, workflow reports, SLA or responsibility gaps",
        "objective": "reconstruct steps or timeline, identify risk nodes, and prioritize actions",
        "recommended_tools": ["parse_*", "build_extracted", "query_extracted", "export_retrieval", "validate_answer", "finalize"],
        "completion_checks": [
            "answer lists ordered steps or timeline items",
            "risk ranking is grounded in document snippets",
        ],
    },
    "structured_extraction": {
        "name": "Structured extraction",
        "when_to_use": "general key-value, table, profile, or summary extraction tasks",
        "objective": "produce structured fields/tables with evidence and quality status",
        "recommended_tools": ["parse_*", "build_extracted", "validate_quality", "query_extracted", "export_retrieval", "validate_answer", "finalize"],
        "completion_checks": [
            "answer includes requested fields or an explicit not_found for missing fields",
            "answer_validation reports no missing evidence",
        ],
    },
}


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
    """Mutable workspace the tools read/write.

    ``input_path`` is the *current* document for the turn and may be ``None`` at
    the start of an interactive session before any document is named.
    ``workspace_root`` bounds which files tools may read; it defaults to the
    input file's directory (single-shot ``run_live_agent``) or the current
    working directory (a persistent chat session).
    """

    def __init__(
        self,
        *,
        output_dir: Path,
        input_path: Path | None = None,
        workspace_root: Path | None = None,
        default_pdf_parser: str = "auto",
    ) -> None:
        self.output_dir = output_dir
        self.input_path = Path(input_path).resolve() if input_path is not None else None
        if workspace_root is not None:
            self.workspace_root = Path(workspace_root).resolve()
        elif self.input_path is not None:
            self.workspace_root = self.input_path.parent
        else:
            self.workspace_root = Path.cwd().resolve()
        self.default_pdf_parser = default_pdf_parser if default_pdf_parser in PDF_PARSER_CHOICES else "auto"
        self.parses: dict[str, dict[str, Any]] = {}
        self.extracted: dict[str, Any] | None = None
        self.quality: dict[str, Any] | None = None
        self.retrieval: dict[str, Any] | None = None
        self.selected_skill: dict[str, Any] | None = None
        self.skill_history: list[dict[str, Any]] = []
        self.answer_validation: dict[str, Any] | None = None
        self.consistency: dict[str, Any] | None = None
        self.notes: list[str] = []
        self.runtime_harness_events: list[dict[str, Any]] = []

    def clear_document_outputs(self) -> None:
        self.parses.clear()
        self.extracted = None
        self.quality = None
        self.retrieval = None
        self.answer_validation = None
        self.consistency = None


def _resolve_path(raw: str | None, state: AgentState) -> Path:
    allowed_root = state.workspace_root
    if raw is None:
        if state.input_path is None:
            raise ValueError("no current document set; name a file path first")
        target = state.input_path.resolve()
    else:
        candidate = Path(raw)
        if candidate.is_absolute():
            target = candidate.resolve()
        else:
            target = (allowed_root / candidate).resolve()
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


def _tool_parse_url(
    state: AgentState,
    runners: dict[str, MinerUToolRunner],
    *,
    url: str,
    parser: str = "precise-api",
) -> dict[str, Any]:
    clean_url = url.strip()
    if not re.match(r"^https?://", clean_url, flags=re.I):
        return {"ok": False, "error": "only http(s) URLs are supported"}
    selected_parser = parser if parser in {"precise-api", "agent-api"} else "precise-api"
    runner = runners.get(selected_parser)
    if runner is None:
        return {"ok": False, "error": f"no runner available for parser={selected_parser}", "available": sorted(runners)}
    try:
        response = httpx.get(clean_url, timeout=30.0, follow_redirects=True)
        response.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"url download failed: {exc}"}
    suffix = ".html" if "html" in response.headers.get("content-type", "").lower() or clean_url.lower().endswith((".html", ".htm")) else ".pdf"
    downloads = state.output_dir / "url_inputs"
    downloads.mkdir(parents=True, exist_ok=True)
    target = downloads / f"url_{hashlib.sha256(clean_url.encode('utf-8')).hexdigest()[:12]}{suffix}"
    target.write_bytes(response.content)
    state.input_path = target
    if suffix in {".html", ".htm"} and selected_parser == "precise-api":
        backend = "pipeline"  # MinerUPreciseAPIRunner maps HTML suffix to MinerU-HTML.
    else:
        backend = "pipeline"
    if suffix in {".html", ".htm"} and selected_parser == "agent-api":
        return {"ok": False, "error": "online HTML requires precise-api/MinerU-HTML", "downloaded_path": str(target)}
    try:
        artifacts, tool_call = runner.parse(
            input_path=target,
            output_dir=state.output_dir / "mineru_url",
            backend=backend,
            method="auto",
            lang="ch",
        )
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "parser": selected_parser, "error": f"url parser failed: {exc}", "downloaded_path": str(target)}
    markdown = read_markdown(artifacts.markdown_path)
    content = read_content_list(artifacts.content_list_path)
    state.parses["url"] = {
        "markdown": markdown,
        "content_list": content,
        "source": clean_url,
        "downloaded_path": str(target),
        "parser": selected_parser,
        "backend": "MinerU-HTML" if suffix in {".html", ".htm"} else backend,
        "artifacts": artifacts.to_jsonable(),
        "tool_call": asdict(tool_call),
    }
    return {
        "ok": True,
        "kind": "url",
        "url": clean_url,
        "downloaded_suffix": suffix,
        "parser": selected_parser,
        "backend": "MinerU-HTML" if suffix in {".html", ".htm"} else backend,
        "mineru_tool": tool_call.tool,
        "markdown_chars": len(markdown),
        "blocks": len(content),
        "preview": markdown[:600],
    }


def _tool_parse_pdf(
    state: AgentState,
    runners: dict[str, MinerUToolRunner],
    *,
    path: str | None = None,
    parser: str = "auto",
    backend: str = "pipeline",
    method: str = "auto",
    lang: str = "ch",
    start_page: int | None = None,
    end_page: int | None = None,
) -> dict[str, Any]:
    target = _resolve_path(path, state)
    if not target.exists():
        return {"ok": False, "error": f"file not found: {target}"}
    if target.suffix.lower() != ".pdf":
        return {"ok": False, "error": f"not a PDF: {target.suffix}"}
    if backend not in PDF_BACKEND_CHOICES:
        backend = "pipeline"
    selected_parser = _select_pdf_parser(target, parser=parser, backend=backend, state=state, runners=runners)
    gate = _live_pdf_text_layer_harness_gate(target, selected_parser=selected_parser, runners=runners)
    if gate.get("blocked"):
        selected_parser = str(gate.get("target") or selected_parser)
        backend = str(gate.get("backend") or backend)
        state.runtime_harness_events.append(gate)
        state.notes.append(
            "harness_gate_blocked_pdf_text_layer:"
            f" {target.name} local-pdf-text -> {selected_parser}; {gate.get('reason', '')}"
        )

    if selected_parser == "local":
        try:
            markdown, content, meta = extract_pdf_text(target)
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "parser": "local",
                "error": f"local pdf text extraction failed: {exc}",
                "hint": "Retry with parser=agent-api (<=20 pages) or parser=precise-api.",
            }
        if not meta.get("has_text_layer"):
            return {
                "ok": False,
                "parser": "local",
                "reason": "no_text_layer",
                "page_count": meta.get("page_count"),
                "hint": "This PDF looks scanned (no usable text layer). Call parse_pdf again with "
                "parser=agent-api for <=20 pages, or parser=precise-api for larger/complex scans.",
            }
        state.parses["pdf"] = {
            "markdown": markdown,
            "content_list": content,
            "source": str(target),
            "parser": "local",
            "backend": "local-text-layer",
            "meta": meta,
        }
        return {
            "ok": True,
            "kind": "pdf",
            "parser": "local",
            "page_count": meta.get("page_count"),
            "markdown_chars": len(markdown),
            "blocks": len(content),
            "preview": markdown[:600],
        }

    selected_runner = runners.get(selected_parser)
    if selected_runner is None:
        return {
            "ok": False,
            "parser": selected_parser,
            "error": f"no online runner available for parser={selected_parser}",
            "available": sorted(runners),
        }
    try:
        artifacts, tool_call = selected_runner.parse(
            input_path=target,
            output_dir=state.output_dir / "mineru",
            backend=backend,
            method=method,
            lang=lang,
            start_page=start_page,
            end_page=end_page,
        )
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "parser": selected_parser, "backend": backend, "error": f"mineru runner failed: {exc}"}
    markdown = read_markdown(artifacts.markdown_path)
    content = read_content_list(artifacts.content_list_path)
    state.parses["pdf"] = {
        "markdown": markdown,
        "content_list": content,
        "source": str(target),
        "parser": selected_parser,
        "backend": backend,
        "artifacts": artifacts.to_jsonable(),
        "tool_call": asdict(tool_call),
    }
    if gate.get("blocked"):
        state.parses["pdf"]["harness_gate"] = gate
    return {
        "ok": True,
        "kind": "pdf",
        "parser": selected_parser,
        "backend": backend,
        "harness_gate": gate if gate.get("blocked") else None,
        "mineru_tool": tool_call.tool,
        "start_page": start_page,
        "end_page": end_page,
        "markdown_chars": len(markdown),
        "blocks": len(content),
        "preview": markdown[:600],
        "tool_status": tool_call.status,
        "elapsed_seconds": tool_call.elapsed_seconds,
    }


def _build_live_mineru_runners(primary: MinerUToolRunner | None = None) -> dict[str, MinerUToolRunner]:
    """Online MinerU runners only. Local CLI (self-hosted MinerU) is retired:
    born-digital PDFs are parsed locally via the text layer, scans go online."""
    return {
        "agent-api": primary if isinstance(primary, MinerUAgentAPIRunner) else MinerUAgentAPIRunner(),
        "precise-api": primary if isinstance(primary, MinerUPreciseAPIRunner) else MinerUPreciseAPIRunner(),
    }


def _select_pdf_parser(
    target: Path,
    *,
    parser: str,
    backend: str,
    state: AgentState,
    runners: dict[str, MinerUToolRunner],
) -> str:
    requested = parser if parser in PDF_PARSER_CHOICES else "auto"
    if requested == "auto" and state.default_pdf_parser != "auto":
        requested = state.default_pdf_parser
    if requested == "auto":
        requested = _auto_pdf_parser(target, backend=backend)
    if requested == "local":
        return "local"
    if requested not in runners:
        # Local MinerU CLI is retired; fall back to the cheapest available online runner.
        requested = "agent-api" if "agent-api" in runners else next(iter(runners), "agent-api")
    return requested


def _auto_pdf_parser(target: Path, *, backend: str) -> str:
    token = bool(os.getenv("MINERU_PRECISE_API_TOKEN") or os.getenv("MINERU_API_TOKEN"))
    # Explicit VLM backend = user wants the high-fidelity online model.
    if backend.startswith("vlm"):
        return "precise-api" if token else "agent-api"
    # Born-digital PDFs with a real text layer are parsed locally: cheap, no OCR, no hallucination.
    page_count, has_text = probe_pdf_text_layer(target)
    if has_text:
        return "local"
    # Scanned / image PDFs need online OCR. Small ones fit the free lightweight API (<=20 pages).
    if page_count is not None and page_count <= 20:
        return "agent-api"
    if token:
        return "precise-api"
    return "agent-api"


def _live_pdf_text_layer_harness_gate(
    target: Path,
    *,
    selected_parser: str,
    runners: dict[str, MinerUToolRunner],
) -> dict[str, Any]:
    if selected_parser != "local":
        return {"blocked": False, "initial_decision": "local-pdf-text"}
    try:
        metadata = build_input_metadata(target)
    except Exception as exc:  # noqa: BLE001
        return {
            "blocked": False,
            "initial_decision": "local-pdf-text",
            "probe_error": str(exc)[-200:],
        }
    if metadata.get("has_text_layer") is not True:
        return {"blocked": False, "initial_decision": "local-pdf-text"}

    reasons: list[str] = []
    layout_risk = bool(
        metadata.get("is_complex_layout")
        or metadata.get("layout_risk") == "reading_order_risk"
        or metadata.get("layout_type") == "multi_column"
    )
    table_risk = bool(metadata.get("has_tables") or metadata.get("table_risk") == "table_structure_or_numeric_risk")
    if layout_risk:
        sampled = metadata.get("layout_sampled_pages") or "?"
        multi = metadata.get("multi_column_pages") or "?"
        reasons.append(f"复杂/双栏版式可能破坏本地文字层阅读顺序 ({multi}/{sampled} 页)")
    if table_risk:
        pages = metadata.get("table_pages") if isinstance(metadata.get("table_pages"), list) else []
        page_text = f" {pages}" if pages else ""
        reasons.append(f"检测到表格页{page_text}，需要保持行列结构并校验数字")
    if not reasons:
        return {"blocked": False, "initial_decision": "local-pdf-text"}

    target_parser, backend = _live_harness_gate_target(metadata, runners=runners, table_risk=table_risk)
    table_pages = metadata.get("table_pages") if isinstance(metadata.get("table_pages"), list) else []
    actions = [
        {
            "action": "layout_aware_parse",
            "parser": target_parser,
            "backend": backend,
            "reason": "用 MinerU 版面解析保留段落、双栏阅读顺序和页面结构",
        }
    ]
    if table_risk:
        actions.extend(
            [
                {
                    "action": "vlm_table_review",
                    "parser": "precise-api" if "precise-api" in runners else target_parser,
                    "backend": "vlm-transformers" if "precise-api" in runners else backend,
                    "pages": table_pages,
                    "reason": "表格页使用 VLM 保持行列结构和跨行/跨列关系",
                },
                {
                    "action": "ocr_or_text_numeric_check",
                    "parser": "pipeline/text-layer",
                    "method": "ocr_or_text",
                    "pages": table_pages,
                    "reason": "表格数字必须由 OCR 或文字层进行二次校验，不默认相信 VLM 数字",
                },
            ]
        )
    return {
        "blocked": True,
        "source_file": target.name,
        "initial_decision": "local-pdf-text",
        "target": target_parser,
        "backend": backend,
        "reason": "；".join(reasons),
        "metadata": {
            "page_count": metadata.get("page_count"),
            "layout_type": metadata.get("layout_type"),
            "layout_risk": metadata.get("layout_risk"),
            "multi_column_pages": metadata.get("multi_column_pages"),
            "layout_sampled_pages": metadata.get("layout_sampled_pages"),
            "table_pages": table_pages,
            "table_count": metadata.get("table_count"),
        },
        "actions": actions,
        "policy": "Harness keeps local text-layer as the initial low-cost path, then blocks it during execution when layout/table risks require structured parsing and independent evidence.",
    }


def _live_harness_gate_target(
    metadata: dict[str, Any],
    *,
    runners: dict[str, MinerUToolRunner],
    table_risk: bool,
) -> tuple[str, str]:
    precise_available = "precise-api" in runners and bool(os.getenv("MINERU_PRECISE_API_TOKEN") or os.getenv("MINERU_API_TOKEN"))
    agent_available = "agent-api" in runners
    page_count = metadata.get("page_count") if isinstance(metadata.get("page_count"), int) else None
    if table_risk and precise_available:
        return "precise-api", "vlm-transformers"
    if agent_available and (page_count is None or page_count <= 20):
        return "agent-api", "pipeline"
    if precise_available:
        return "precise-api", "pipeline"
    if agent_available:
        return "agent-api", "pipeline"
    return next(iter(runners), "agent-api"), "pipeline"


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


def _tool_plan_escalation(state: AgentState) -> dict[str, Any]:
    if not state.extracted:
        return {"ok": False, "error": "no extracted view; build_extracted first"}
    plan = build_fine_grained_escalation_plan(
        extracted=state.extracted,
        quality=state.quality or {"issues": []},
        input_metadata={},
    )
    state.notes.append(f"fine_grained_escalation_plan: {plan.get('status')}")
    return {"ok": True, **plan}


def _tool_compare_parsers(
    state: AgentState,
    *,
    candidate_text: str,
    candidate_parser: str = "mineru-vlm",
) -> dict[str, Any]:
    if not state.parses:
        return {"ok": False, "error": "no parsed document yet; call a parse_* tool first"}
    primary = next(iter(state.parses.values()))
    current_parser = str(primary.get("parser") or primary.get("backend") or primary.get("source") or "current")
    report = compare_parser_outputs(
        [
            {"name": current_parser, "role": current_parser, "text": primary.get("markdown", "")},
            {"name": candidate_parser, "role": candidate_parser, "text": candidate_text},
        ]
    )
    state.consistency = report
    if report.get("hallucination_risks"):
        state.notes.append("vlm_hallucination_risk_detected")
    return {"ok": True, **report}


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


def _tool_select_skill(
    state: AgentState,
    *,
    skill_id: str,
    reason: str,
    plan: list[str] | None = None,
) -> dict[str, Any]:
    if skill_id not in LIVE_AGENT_SKILLS:
        return {
            "ok": False,
            "error": f"unknown skill_id: {skill_id}",
            "available_skill_ids": sorted(LIVE_AGENT_SKILLS),
        }
    skill = LIVE_AGENT_SKILLS[skill_id]
    record = {
        "skill_id": skill_id,
        "name": skill["name"],
        "reason": reason,
        "plan": plan or [],
        "selected_at": _now(),
    }
    state.selected_skill = record
    state.skill_history.append(record)
    state.notes.append(f"selected_skill: {skill_id} :: {reason}")
    return {
        "ok": True,
        "selected_skill": record,
        "skill_policy": skill,
        "instruction": "Follow this skill, but switch skill if the evidence contradicts the initial choice.",
    }


def _normalize_number_token(token: str) -> float | None:
    clean = token.replace(",", "").replace("，", "").strip()
    clean = clean.rstrip("%")
    try:
        return float(clean)
    except ValueError:
        return None


def _number_tokens(text: str) -> list[str]:
    return re.findall(r"[-+]?\d[\d,，]*(?:\.\d+)?%?", text)


def _number_in_text(token: str, text: str) -> bool:
    plain = token.replace(",", "").replace("，", "")
    compact_text = text.replace(",", "").replace("，", "")
    return token in text or plain in compact_text


def _answer_fingerprint(answer: str) -> str:
    return hashlib.sha256(answer.encode("utf-8")).hexdigest()


def _evidence_fingerprint(evidence: list[str]) -> str:
    payload = json.dumps(evidence, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _arithmetic_issues(answer: str) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for match in re.finditer(r"([-\d,，.\s+]+)=\s*([-+]?\d[\d,，]*(?:\.\d+)?)", answer):
        left_tokens = _number_tokens(match.group(1))
        right_tokens = _number_tokens(match.group(2))
        if len(left_tokens) < 2 or not right_tokens:
            continue
        left_values = [_normalize_number_token(item) for item in left_tokens]
        right_value = _normalize_number_token(right_tokens[-1])
        if any(value is None for value in left_values) or right_value is None:
            continue
        total = sum(value for value in left_values if value is not None)
        tolerance = max(0.01, abs(right_value) * 0.0001)
        is_equal = abs(total - right_value) <= tolerance
        window = answer[max(0, match.start() - 30): min(len(answer), match.end() + 30)]
        if is_equal and any(term in window for term in ["不等于", "不一致", "mismatch", "does not equal", "!="]):
            issues.append(
                {
                    "code": "self_contradictory_arithmetic",
                    "severity": "error",
                    "message": "The answer says the equation does not match, but the displayed arithmetic balances.",
                    "expression": match.group(0),
                    "computed_sum": total,
                    "reported_total": right_value,
                }
            )
        if not is_equal and any(term in window for term in ["一致", "相等", "无异常", "match", "equals"]):
            issues.append(
                {
                    "code": "incorrect_arithmetic_match_claim",
                    "severity": "error",
                    "message": "The answer claims arithmetic consistency, but the displayed equation does not balance.",
                    "expression": match.group(0),
                    "computed_sum": total,
                    "reported_total": right_value,
                }
            )
    return issues


def _tool_validate_answer(
    state: AgentState,
    *,
    answer: str,
    evidence: list[str] | None = None,
    claims: list[str] | None = None,
) -> dict[str, Any]:
    evidence = evidence or []
    claims = claims or []
    primary = next(iter(state.parses.values()), {})
    markdown = primary.get("markdown") or ""
    corpus = markdown + "\n" + json.dumps(state.extracted or {}, ensure_ascii=False, default=str)
    issues: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    if not state.selected_skill:
        issues.append(
            {
                "code": "missing_selected_skill",
                "severity": "error",
                "message": "The live Agent must call select_skill before answer validation.",
            }
        )
    if not state.parses:
        issues.append(
            {
                "code": "missing_parse",
                "severity": "error",
                "message": "The live Agent must parse the input document before validating the final answer.",
            }
        )
    if not answer.strip():
        issues.append({"code": "empty_answer", "severity": "error", "message": "Answer is empty."})
    if not evidence:
        warnings.append({"code": "missing_evidence_list", "severity": "warning", "message": "No evidence list was supplied."})

    lower_answer = answer.lower()
    is_not_found_answer = "not_found" in lower_answer or "未找到" in answer or "无法提取" in answer
    support_text = corpus
    if is_not_found_answer:
        support_text = "\n".join([corpus, *evidence, *claims])

    unsupported_numbers = [token for token in _number_tokens(answer) if not _number_in_text(token, support_text)]
    if unsupported_numbers:
        issues.append(
            {
                "code": "unsupported_numbers",
                "severity": "error",
                "message": "Some numbers in the answer were not found in parsed evidence.",
                "numbers": unsupported_numbers[:10],
            }
        )

    for issue in _arithmetic_issues(answer):
        issues.append(issue)

    if is_not_found_answer:
        if not evidence and not claims:
            issues.append(
                {
                    "code": "not_found_without_search_record",
                    "severity": "error",
                    "message": "A not_found answer must include searched evidence or claims.",
                }
            )
        contract_markers = ["责任", "义务", "应当", "需", "必须", "服务范围", "数据安全", "验收", "异常处理"]
        if state.selected_skill and state.selected_skill.get("skill_id") == "contract_clause_review":
            present = [marker for marker in contract_markers if marker in corpus]
            if present:
                issues.append(
                    {
                        "code": "potential_not_found_conflict",
                        "severity": "error",
                        "message": "Contract responsibility markers exist in the document, so not_found is likely too strong.",
                        "markers": present[:8],
                    }
                )

    if state.quality and state.quality.get("status") == "needs_review":
        warnings.append(
            {
                "code": "quality_needs_review",
                "severity": "warning",
                "message": "Current extraction quality is needs_review; final answer should state uncertainty.",
            }
        )

    result = {
        "ok": not issues,
        "blocking_issues": issues,
        "warnings": warnings,
        "selected_skill_id": state.selected_skill.get("skill_id") if state.selected_skill else None,
        "checked_claims": claims,
        "recommendation": "finalize" if not issues else "revise_or_gather_more_evidence",
    }
    state.answer_validation = {
        **result,
        "answer_full": answer,
        "answer_preview": answer[:600],
        "answer_sha256": _answer_fingerprint(answer),
        "answer_length": len(answer),
        "evidence_full": evidence,
        "evidence_sha256": _evidence_fingerprint(evidence),
        "evidence_count": len(evidence),
        "validated_at": _now(),
    }
    return result


def _tool_finalize(state: AgentState, *, answer: str, evidence: list[str] | None = None) -> dict[str, Any]:
    validation = state.answer_validation
    evidence = evidence or []
    if not validation or validation.get("answer_sha256") != _answer_fingerprint(answer) or validation.get("answer_length") != len(answer):
        return {
            "ok": False,
            "error": "finalize requires validate_answer for the exact answer first",
            "required_tool": "validate_answer",
        }
    if validation.get("evidence_sha256") != _evidence_fingerprint(evidence):
        return {
            "ok": False,
            "error": "finalize requires validate_answer for the exact evidence list first",
            "required_tool": "validate_answer",
        }
    if validation.get("blocking_issues"):
        return {
            "ok": False,
            "error": "answer validation has blocking issues; revise or gather more evidence before finalizing",
            "blocking_issues": validation.get("blocking_issues"),
            "required_tool": "validate_answer",
        }
    state.notes.append(f"final_answer: {answer}")
    return {"ok": True, "answer": answer, "evidence": evidence}


TOOL_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "select_skill",
            "description": "Select or switch a high-level task skill. Call this before parsing, and call it again if evidence shows the first skill was wrong.",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_id": {"type": "string", "enum": sorted(LIVE_AGENT_SKILLS)},
                    "reason": {"type": "string"},
                    "plan": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["skill_id", "reason"],
            },
        },
    },
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
            "name": "parse_url",
            "description": "Parse an online HTML/PDF URL. Online HTML uses MinerU precise-api with MinerU-HTML routing; downloaded PDFs use the selected online parser.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "parser": {"type": "string", "enum": ["precise-api", "agent-api"]},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "parse_pdf",
            "description": "Parse a PDF. Omit path to use the input file. Choose parser=local for born-digital/vector PDFs that have a text layer (free, no OCR, no hallucination); parser=agent-api for scanned PDFs up to 20 pages; parser=precise-api with backend=vlm-transformers for large or complex scans. parser=auto picks local when a text layer exists, otherwise online MinerU.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Optional relative path under the input file directory. Omit to use the default input file."},
                    "parser": {"type": "string", "enum": ["auto", "local", "agent-api", "precise-api"]},
                    "backend": {"type": "string", "enum": ["pipeline", "vlm-transformers", "vlm-sglang-engine", "vlm-sglang-client"]},
                    "method": {"type": "string", "enum": ["auto", "ocr", "txt"]},
                    "lang": {"type": "string", "enum": ["ch", "en"]},
                    "start_page": {"type": "integer", "description": "Optional 1-based first page for a focused online MinerU parse."},
                    "end_page": {"type": "integer", "description": "Optional 1-based last page for a focused online MinerU parse."},
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
            "name": "plan_escalation",
            "description": "Plan page-level OCR/VLM escalation from quality issues, tables, weak provenance, and extracted page signals. Use before expensive VLM retries.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_parsers",
            "description": "Compare current parse text with a candidate OCR/VLM text. If VLM diverges from OCR/text-layer output, mark VLM hallucination risk.",
            "parameters": {
                "type": "object",
                "properties": {
                    "candidate_text": {"type": "string"},
                    "candidate_parser": {"type": "string"},
                },
                "required": ["candidate_text"],
            },
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
            "description": "Submit the final answer for the user task. You must call validate_answer for the exact answer first. Provide the answer and an evidence list. After a successful finalize the agent loop ends.",
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
    {
        "type": "function",
        "function": {
            "name": "validate_answer",
            "description": "Validate the proposed final answer before finalize. Checks evidence support, unsupported numbers, simple arithmetic contradictions, and not_found conflicts for the selected skill.",
            "parameters": {
                "type": "object",
                "properties": {
                    "answer": {"type": "string"},
                    "evidence": {"type": "array", "items": {"type": "string"}},
                    "claims": {"type": "array", "items": {"type": "string"}, "description": "Short claim list or searched terms to audit, especially for not_found answers."},
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
    selected_skill: dict[str, Any] | None = None
    skill_history: list[dict[str, Any]] = field(default_factory=list)
    answer_validation: dict[str, Any] | None = None
    autonomy_controls: dict[str, Any] = field(default_factory=dict)
    parse_runtime: dict[str, Any] = field(default_factory=dict)
    runtime_harness_events: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
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
    harness_assisted_finalize = "harness_assisted_finalize_after_validated_answer" in trace.notes
    tool_call_completed = trace.status == "completed" and trace.total_tokens > 0 and ("finalize" in tool_sequence or harness_assisted_finalize)
    validation_ok = bool(trace.answer_validation and trace.answer_validation.get("ok"))
    quality_status = "tool_validated_unreviewed" if tool_call_completed and validation_ok else "unreviewed" if tool_call_completed else "not_applicable"
    notes = ["answer passed built-in validate_answer but still requires manual or benchmark review"] if tool_call_completed and validation_ok else ["answer quality requires manual or benchmark review"] if tool_call_completed else []
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
        "selected_skill": trace.selected_skill,
        "skill_history": trace.skill_history,
        "skill_catalog_version": SKILL_CATALOG_VERSION,
        "autonomy_controls": trace.autonomy_controls,
        "parse_runtime": trace.parse_runtime,
        "runtime_harness_events": trace.runtime_harness_events,
        "notes": trace.notes,
        "harness_assisted_finalize": harness_assisted_finalize,
        "tool_call_completed": tool_call_completed,
        "live_evidence": tool_call_completed,
        "answer_quality_pass": None,
        "quality_review": {"status": quality_status, "notes": notes},
        "answer_validation": trace.answer_validation,
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
    skills = "\n".join(
        f"- {skill_id}: {skill['name']} | use for {skill['when_to_use']} | objective: {skill['objective']}"
        for skill_id, skill in LIVE_AGENT_SKILLS.items()
    )
    return (
        "You are MinerU Data Agent — a tool-using planner for document understanding tasks.\n"
        "You receive a user task and an input file path. You must autonomously choose a high-level skill, then decide which tools to call.\n\n"
        "AVAILABLE SKILLS:\n"
        f"{skills}\n\n"
        "OPERATING LOOP:\n"
        "1. First call select_skill with the skill that best matches the task. You may call select_skill again to switch skills when evidence contradicts your initial choice.\n"
        "2. Pick the parser that matches the source: local HTML uses parse_html; online http(s) HTML/PDF uses parse_url; Office uses parse_office; PDFs use parse_pdf. Omit path unless the user explicitly asks for a sibling file.\n"
        "3. Build extraction and validate quality when it helps. If quality is weak, call plan_escalation before any expensive VLM retry, then retry only the listed page ranges.\n"
        "4. If a VLM retry disagrees with local text-layer or OCR text, call compare_parsers and treat the VLM text as hallucination risk unless OCR/text evidence confirms it.\n"
        "5. Use query_extracted to ground facts; use export_retrieval when retrieval artifacts help review.\n"
        "6. Draft the exact final answer, call validate_answer with that exact answer and evidence, then revise or gather more evidence if validation reports blocking issues.\n"
        "7. Only after validate_answer passes, call finalize with the same answer and evidence.\n\n"
        "RULES:\n"
        "- Only ONE tool call per turn.\n"
        "- For online HTML URLs, use parse_url(parser=precise-api); precise-api routes HTML through MinerU-HTML.\n"
        "- For PDF parsing, choose parse_pdf.parser by cost and fidelity: parser=local for born-digital/vector PDFs that have a text layer (free, no OCR, no hallucination); parser=agent-api for scanned PDFs up to 20 pages; parser=precise-api for larger scans or when a tokened precise API is needed. Prefer pipeline/OCR for text, and use backend=vlm-transformers only for tables, charts, layout-heavy pages, cross-page evidence, or quality-degraded page chunks.\n"
        "- Do not run whole-document VLM by default. Use plan_escalation and parse_pdf(start_page=..., end_page=..., backend=vlm-transformers) for focused page chunks.\n"
        "- When VLM and OCR/text-layer outputs conflict, default to OCR/text-layer evidence and mark the VLM output as hallucination risk via compare_parsers.\n"
        "- Never invent values. If information is not in the document, validate a not_found answer with searched terms and evidence before finalizing.\n"
        "- For arithmetic, use validate_answer; do not claim totals match or mismatch without tool validation.\n"
        "- For contract tasks, do not answer not_found merely because the literal word '义务' is absent; search responsibilities, shall/must language, service scope, security, acceptance, and dispute clauses.\n"
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


def _resolve_provider(
    provider: str,
    *,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> tuple[str, str, str, str]:
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
    return provider, model, api_key, base_url


class LiveAgentSession:
    """A persistent live-agent conversation.

    Unlike the one-shot ``run_live_agent`` it keeps ``messages`` and ``state``
    across ``send`` calls, so follow-up instructions ("export the last doc as a
    skill", "re-run page 3 with the precise API") reuse the prior parse/extract
    state instead of starting over. Each ``send`` runs the LLM tool loop until
    finalize / max_turns and can be interrupted with KeyboardInterrupt.
    """

    def __init__(
        self,
        *,
        output_dir: Path,
        provider: str,
        model: str,
        api_key: str,
        base_url: str,
        max_turns: int,
        max_tokens: int,
        timeout: float,
        runners: dict[str, MinerUToolRunner],
        workspace_root: Path,
        default_pdf_parser: str = "auto",
        run_id: str | None = None,
        task: str = "",
        input_path: Path | None = None,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.max_turns = max_turns
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.runners = runners
        self.run_id = run_id or uuid.uuid4().hex[:12]
        default_pdf_parser = default_pdf_parser if default_pdf_parser in PDF_PARSER_CHOICES else "auto"
        self.state = AgentState(
            output_dir=output_dir,
            input_path=input_path,
            workspace_root=workspace_root,
            default_pdf_parser=default_pdf_parser,
        )
        self._turn_counter = 0
        self.messages: list[dict[str, Any]] = [{"role": "system", "content": _system_prompt()}]
        self.trace = LiveAgentTrace(
            run_id=self.run_id,
            task=task,
            input_file=str(self.state.input_path) if self.state.input_path else "",
            output_dir=str(output_dir),
            provider=provider,
            model=model,
            started_at=_now(),
            autonomy_controls={
                "mode": "skill_guided_tool_calling",
                "skill_catalog_version": SKILL_CATALOG_VERSION,
                "llm_must_select_skill": True,
                "llm_may_switch_skill": True,
                "finalize_requires_validate_answer": True,
                "one_tool_call_per_turn": True,
                "default_pdf_parser": default_pdf_parser,
                "available_pdf_parsers": sorted(runners),
                "session_memory": True,
                "interruptible": True,
            },
        )

    def set_current_document(self, path: str | Path, *, default_pdf_parser: str = "auto", routing_note: str = "") -> None:
        resolved = Path(path).expanduser().resolve()
        previous = self.state.input_path
        if previous is None or previous != resolved:
            self.state.clear_document_outputs()
            self.state.notes.append(f"current_document_changed: {resolved.name}")
        self.state.input_path = resolved
        self.state.default_pdf_parser = default_pdf_parser if default_pdf_parser in PDF_PARSER_CHOICES else "auto"
        if not self.trace.input_file:
            self.trace.input_file = str(resolved)
        note = routing_note or f"router default PDF parser: {self.state.default_pdf_parser}"
        self.messages.append(
            {
                "role": "user",
                "content": (
                    f"Current document is now: {resolved.name} (suffix={resolved.suffix}). {note} "
                    "You may override the PDF parser via parse_pdf(parser=...). "
                    "Reuse already-parsed content for follow-up requests instead of re-parsing when possible."
                ),
            }
        )

    def send(self, user_text: str) -> dict[str, Any]:
        first = self._turn_counter == 0
        self.trace.status = "running"
        self.trace.error = None
        self.trace.final_answer = None
        self.trace.final_evidence = []
        self.messages.append({"role": "user", "content": self._format_user(user_text, first=first)})
        try:
            self._run_loop()
        except KeyboardInterrupt:
            self.trace.status = "interrupted"
            self.state.notes.append("user_interrupted")
        self._finalize_trace()
        self.persist()
        return self._result()

    def _format_user(self, user_text: str, *, first: bool) -> str:
        if first and self.state.input_path is not None:
            return (
                f"Task: {user_text}\n"
                f"Input file: {self.state.input_path.name} (suffix={self.state.input_path.suffix})\n"
                f"Input path is available to tools; do not repeat local filesystem paths in the final answer.\n"
                f"Choose a skill with select_skill, plan, execute, validate the answer, then call finalize."
            )
        return user_text

    def _run_loop(self) -> None:
        state = self.state
        trace = self.trace
        messages = self.messages
        runners = self.runners
        turns_this_send = 0
        while turns_this_send < self.max_turns:
            turn_index = self._turn_counter
            self._turn_counter += 1
            turns_this_send += 1
            is_last = turns_this_send >= self.max_turns
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
                    api_key=self.api_key,
                    base_url=self.base_url,
                    model=self.model,
                    messages=messages,
                    tools=TOOL_SCHEMA,
                    max_tokens=self.max_tokens,
                    timeout=self.timeout,
                )
            except Exception as exc:  # noqa: BLE001
                turn.error = f"chat request failed: {exc}"
                turn.ended_at = _now()
                trace.turns.append(turn)
                trace.status = "failed"
                trace.error = turn.error
                return

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
                if not is_last:
                    time.sleep(8.0 + 2.0 * (turns_this_send - 1))
                    continue
                trace.status = "failed_empty_response"
                return
            if not tool_calls:
                turn.ended_at = _now()
                trace.turns.append(turn)
                messages.append({"role": "assistant", "content": content_text})
                if not is_last:
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                "You answered without using the required tool chain. If you have not selected a skill, call "
                                "`select_skill`; if you have not parsed the document, call the parser; then call "
                                "`validate_answer` for your exact answer and evidence before `finalize`."
                            ),
                        }
                    )
                    continue
                trace.final_answer = content_text
                trace.status = "assistant_answer_without_finalize"
                return

            call = tool_calls[0]
            fn = call.get("function") or {}
            name = fn.get("name", "")
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            call_id = call.get("id") or f"call_{turn_index}"

            result = _dispatch_tool(name, args, state=state, runners=runners)
            trace.selected_skill = state.selected_skill
            trace.skill_history = list(state.skill_history)
            trace.answer_validation = state.answer_validation
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

            if name == "validate_answer" and result.get("ok"):
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Answer validation passed. Your next tool call must be `finalize` with the exact same "
                            "`answer` and `evidence` values you just validated. Do not call query_extracted, "
                            "export_retrieval, or validate_answer again unless validation reported blocking issues."
                        ),
                    }
                )

            # Anti-loop nudge: if same tool used 3+ times in a row without finalize, push the model toward finishing.
            recent = [t.tool_call["name"] for t in trace.turns[-4:] if t.tool_call]
            if len(recent) >= 3 and len(set(recent[-3:])) == 1 and recent[-1] not in {"finalize"}:
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            f"You have called `{recent[-1]}` {len(recent)} times in a row. "
                            "Stop repeating. Use what you already have, call `export_retrieval` if useful, "
                            "then call `validate_answer` for your exact answer. If validation passes, call `finalize`; "
                            "if the information is genuinely not in the document, validate a not_found answer listing what IS in the document."
                        ),
                    }
                )

            if name == "finalize" and result.get("ok"):
                trace.final_answer = result.get("answer")
                trace.final_evidence = result.get("evidence") or []
                trace.status = "completed"
                return

        # Ran out of turns for this send without an explicit finalize.
        if state.answer_validation and state.answer_validation.get("ok"):
            trace.final_answer = state.answer_validation.get("answer_full") or state.answer_validation.get("answer_preview")
            trace.final_evidence = state.answer_validation.get("evidence_full") or []
            trace.status = "completed"
            state.notes.append("harness_assisted_finalize_after_validated_answer")
        elif state.parses and state.extracted:
            answer, evidence = _fallback_parsed_document_answer(state, self.trace.task)
            state.answer_validation = {
                "ok": True,
                "blocking_issues": [],
                "warnings": [
                    {
                        "code": "harness_generated_parse_summary",
                        "severity": "info",
                        "message": "Harness summarized execution state after the model exhausted turns without finalizing.",
                    }
                ],
                "recommendation": "completed_with_parse_summary",
                "answer_full": answer,
                "answer_preview": answer[:600],
                "answer_sha256": _answer_fingerprint(answer),
                "answer_length": len(answer),
                "evidence_full": evidence,
                "evidence_sha256": _evidence_fingerprint(evidence),
                "evidence_count": len(evidence),
                "validated_at": _now(),
            }
            trace.answer_validation = state.answer_validation
            trace.final_answer = answer
            trace.final_evidence = evidence
            trace.status = "completed"
            state.notes.append("harness_assisted_finalize_after_parse_summary")
        else:
            trace.status = "max_turns_exceeded"

    def _finalize_trace(self) -> None:
        self.trace.finished_at = _now()
        self.trace.selected_skill = self.state.selected_skill
        self.trace.skill_history = list(self.state.skill_history)
        self.trace.answer_validation = self.state.answer_validation
        self.trace.parse_runtime = _live_parse_runtime_summary(self.state)
        self.trace.runtime_harness_events = list(self.state.runtime_harness_events)
        self.trace.notes = list(self.state.notes)

    def persist(self) -> None:
        output_dir = self.output_dir
        trace = self.trace
        state = self.state
        (output_dir / "live_agent_trace.json").write_text(
            json.dumps(trace.to_jsonable(), ensure_ascii=False, indent=2, default=str), encoding="utf-8"
        )
        if state.extracted is not None:
            (output_dir / "extracted.json").write_text(
                json.dumps(_scrub_json_value(state.extracted), ensure_ascii=False, indent=2, default=str), encoding="utf-8"
            )
        if state.quality is not None:
            (output_dir / "quality.json").write_text(
                json.dumps(_scrub_json_value(state.quality), ensure_ascii=False, indent=2, default=str), encoding="utf-8"
            )
        (output_dir / "live_agent_summary.md").write_text(_build_summary(trace, state), encoding="utf-8")
        (output_dir / "result.json").write_text(
            json.dumps(live_trace_to_jsonable(trace), ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    def _result(self) -> dict[str, Any]:
        return live_trace_to_jsonable(self.trace, display_paths=True)


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
    mineru_runner: MinerUToolRunner | None = None,
    mineru_runners: dict[str, MinerUToolRunner] | None = None,
    default_pdf_parser: str = "auto",
    run_id: str | None = None,
) -> LiveAgentTrace:
    """Single-shot live agent: one document, one task. Thin wrapper over LiveAgentSession."""
    provider, model, api_key, base_url = _resolve_provider(provider, model=model, base_url=base_url, api_key=api_key)

    run_id = run_id or uuid.uuid4().hex[:12]
    input_path = Path(input_file).expanduser().resolve()
    output_dir = Path(output_root).expanduser().resolve() / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    if default_pdf_parser not in PDF_PARSER_CHOICES:
        default_pdf_parser = "auto"
    runners = mineru_runners or _build_live_mineru_runners(mineru_runner)

    session = LiveAgentSession(
        output_dir=output_dir,
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=base_url,
        max_turns=max_turns,
        max_tokens=max_tokens,
        timeout=timeout,
        runners=runners,
        workspace_root=input_path.parent,
        input_path=input_path,
        default_pdf_parser=default_pdf_parser,
        run_id=run_id,
        task=task,
    )
    session.send(task)
    return session.trace


def _live_parse_runtime_summary(state: AgentState) -> dict[str, Any]:
    if not state.parses:
        return {}
    key = next(iter(state.parses))
    primary = state.parses[key]
    if not isinstance(primary, dict):
        return {"kind": key}
    summary: dict[str, Any] = {
        "kind": key,
        "parser": primary.get("parser") or key,
        "backend": primary.get("backend") or "",
        "source": primary.get("source") or "",
        "markdown_chars": len(str(primary.get("markdown") or "")),
        "blocks": len(primary.get("content_list") or []) if isinstance(primary.get("content_list"), list) else None,
    }
    artifacts = primary.get("artifacts")
    if isinstance(artifacts, dict):
        summary["artifacts"] = {
            "markdown_path": artifacts.get("markdown_path"),
            "content_list_path": artifacts.get("content_list_path"),
        }
    meta = primary.get("meta")
    if isinstance(meta, dict):
        summary["page_count"] = meta.get("page_count")
        summary["has_text_layer"] = meta.get("has_text_layer")
    gate = primary.get("harness_gate")
    if isinstance(gate, dict) and gate.get("blocked"):
        summary["harness_gate"] = gate
    return summary


def _fallback_parsed_document_answer(state: AgentState, task: str) -> tuple[str, list[str]]:
    extracted = state.extracted or {}
    summary = extracted.get("content_summary") if isinstance(extracted.get("content_summary"), dict) else {}
    sections = extracted.get("sections") if isinstance(extracted.get("sections"), list) else []
    tables = extracted.get("tables") if isinstance(extracted.get("tables"), list) else []
    key_values = extracted.get("key_values") if isinstance(extracted.get("key_values"), list) else []
    numeric_facts = extracted.get("numeric_facts") if isinstance(extracted.get("numeric_facts"), list) else []
    primary = next(iter(state.parses.values()), {})
    parser = primary.get("parser") or primary.get("backend") or primary.get("source") or "document parser"
    quality_status = (state.quality or {}).get("status") or "not_checked"
    quality_score = (state.quality or {}).get("score")
    evidence: list[str] = []
    for section in sections[:3]:
        title = str(section.get("title") or "section")
        snippet = str(section.get("text") or "")[:180].strip()
        if snippet:
            evidence.append(f"{title}: {snippet}")
    if not evidence:
        markdown = str(primary.get("markdown") or "").strip()
        if markdown:
            evidence.append(markdown[:240])
    answer_lines = [
        "文档解析已完成，但模型在回合上限内没有提交最终业务结论。Harness 已根据已完成的解析结果自动收束为可追溯交付摘要。",
        f"任务: {task or '未记录'}",
        f"解析路径: {parser}",
        f"内容块: {summary.get('item_count', 0)}，页数: {summary.get('page_count', 0)}，章节: {len(sections)}，表格: {len(tables)}，键值: {len(key_values)}，数字事实: {len(numeric_facts)}。",
        f"质量状态: {quality_status}" + (f"，分数: {quality_score}" if quality_score is not None else "。"),
        "完整结果已写入 summary、trace 和 result 文件，可继续追问具体字段或让 Agent 基于已解析内容继续检索。",
    ]
    return "\n".join(answer_lines), evidence


def _dispatch_tool(
    name: str,
    args: dict[str, Any],
    *,
    state: AgentState,
    runners: dict[str, MinerUToolRunner] | MinerUToolRunner | None = None,
    runner: MinerUToolRunner | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    runner_source = runners if runners is not None else runner
    runner_map = runner_source if isinstance(runner_source, dict) else _build_live_mineru_runners(runner_source)
    try:
        if name != "select_skill" and not state.selected_skill:
            result = {
                "ok": False,
                "error": "select_skill_required_before_tool_use",
                "required_tool": "select_skill",
                "available_skill_ids": sorted(LIVE_AGENT_SKILLS),
            }
        elif name == "validate_answer" and not state.parses:
            result = {
                "ok": False,
                "error": "parse_required_before_answer_validation",
                "required_tools": ["parse_html", "parse_office", "parse_pdf"],
            }
        elif name == "finalize" and not state.parses:
            result = {
                "ok": False,
                "error": "parse_required_before_finalize",
                "required_tools": ["parse_html", "parse_office", "parse_pdf"],
            }
        elif name == "parse_html":
            result = _tool_parse_html(state, **args)
        elif name == "select_skill":
            result = _tool_select_skill(state, **args)
        elif name == "parse_office":
            result = _tool_parse_office(state, **args)
        elif name == "parse_url":
            result = _tool_parse_url(state, runner_map, **args)
        elif name == "parse_pdf":
            result = _tool_parse_pdf(state, runner_map, **args)
        elif name == "build_extracted":
            result = _tool_build_extracted(state)
        elif name == "validate_quality":
            result = _tool_validate_quality(state, **args)
        elif name == "clean_text":
            result = _tool_clean_text(state)
        elif name == "export_retrieval":
            result = _tool_export_retrieval(state)
        elif name == "plan_escalation":
            result = _tool_plan_escalation(state)
        elif name == "compare_parsers":
            result = _tool_compare_parsers(state, **args)
        elif name == "query_extracted":
            result = _tool_query_extracted(state, **args)
        elif name == "validate_answer":
            result = _tool_validate_answer(state, **args)
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
        f"- Agent mode: skill-guided tool calling",
        f"- Selected skill: `{(trace.selected_skill or {}).get('skill_id', 'none')}`",
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
    if trace.answer_validation:
        lines.append("")
        lines.append("## Answer validation")
        lines.append(f"- ok: {trace.answer_validation.get('ok')}")
        lines.append(f"- recommendation: {trace.answer_validation.get('recommendation')}")
        blocking = trace.answer_validation.get("blocking_issues") or []
        warnings = trace.answer_validation.get("warnings") or []
        lines.append(f"- blocking issues: {[item.get('code') for item in blocking]}")
        lines.append(f"- warnings: {[item.get('code') for item in warnings]}")
    if state.runtime_harness_events:
        lines.append("")
        lines.append("## Runtime Harness Events")
        for event in state.runtime_harness_events:
            lines.append(
                f"- {event.get('source_file', 'document')}: {event.get('initial_decision', 'initial')} -> "
                f"{event.get('target', 'upgraded parser')}; reason: {event.get('reason', '')}"
            )
    if state.quality:
        lines.append("")
        lines.append("## Quality")
        lines.append(f"- score: {state.quality.get('score')}")
        lines.append(f"- status: {state.quality.get('status')}")
        codes = [i["code"] for i in state.quality.get("issues", [])]
        lines.append(f"- issue codes: {codes}")
    return "\n".join(lines)
