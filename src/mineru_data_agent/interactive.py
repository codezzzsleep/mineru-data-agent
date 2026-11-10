from __future__ import annotations

import json
import os
import re
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import httpx

from .agent import BACKEND_CHOICES, LANG_CHOICES, METHOD_CHOICES, PROFILE_CHOICES, MinerUDataAgent
from .agent_live import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_MAX_TURNS,
    DEFAULT_TIMEOUT,
    PDF_PARSER_CHOICES,
    LiveAgentSession,
    _build_live_mineru_runners,
    _resolve_provider,
    live_trace_to_jsonable,
    run_live_agent,
)
from .batch import run_batch
from .llm_client import DEFAULT_DEEPSEEK_BASE_URL, DEFAULT_DEEPSEEK_MODEL, _chat_completions_url, _parse_json_object
from .llm_client import DeepSeekLLMClient
from .mineru_client import MinerUAgentAPIRunner, MinerUPreciseAPIRunner, MinerURunner, resolve_mineru_executable
from .routing import build_input_metadata, build_workflow_routing
from .source_packager import build_source_document_packages


RUNNER_CHOICES = {"auto", "cli", "agent-api", "precise-api"}
SUPPORTED_WORKSPACE_SUFFIXES = {".pdf", ".html", ".htm", ".docx", ".pptx", ".png", ".jpg", ".jpeg"}


@dataclass
class ChatCommand:
    action: str
    task: str = ""
    input_path: str = ""
    output_root: str = "runs/chat"
    profile: str = "auto"
    runner: str = "auto"
    backend: str = "pipeline"
    method: str = "auto"
    lang: str = "ch"
    llm: str = "deepseek"
    llm_model: str = DEFAULT_DEEPSEEK_MODEL
    strict_page_provenance: bool = False
    rationale: str = ""

    def to_run_kwargs(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "profile": self.profile,
            "backend": self.backend,
            "method": self.method,
            "lang": self.lang,
            "strict_page_provenance": self.strict_page_provenance,
        }

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "task": self.task,
            "input_path": self.input_path,
            "output_root": self.output_root,
            "profile": self.profile,
            "runner": self.runner,
            "backend": self.backend,
            "method": self.method,
            "lang": self.lang,
            "llm": self.llm,
            "llm_model": self.llm_model,
            "strict_page_provenance": self.strict_page_provenance,
            "rationale": self.rationale,
        }


def run_interactive_chat(
    *,
    output_root: Path = Path("runs/chat"),
    provider: str = "deepseek",
    model: str | None = None,
    dry_run: bool = False,
    execution_mode: str = "live",
    max_turns: int = DEFAULT_MAX_TURNS,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    timeout: float = DEFAULT_TIMEOUT,
    mineru_executable: str | None = None,
    input_func: Callable[[str], str] = input,
    print_func: Callable[[str], None] = print,
) -> None:
    default_model = model or DEFAULT_DEEPSEEK_MODEL
    print_func(render_welcome(provider=provider, model=default_model, output_root=output_root, execution_mode=execution_mode))
    if execution_mode == "classic":
        _run_classic_loop(
            output_root=output_root,
            provider=provider,
            default_model=default_model,
            dry_run=dry_run,
            max_turns=max_turns,
            max_tokens=max_tokens,
            timeout=timeout,
            mineru_executable=mineru_executable,
            input_func=input_func,
            print_func=print_func,
        )
        return
    _run_live_loop(
        output_root=output_root,
        provider=provider,
        default_model=default_model,
        dry_run=dry_run,
        max_turns=max_turns,
        max_tokens=max_tokens,
        timeout=timeout,
        mineru_executable=mineru_executable,
        input_func=input_func,
        print_func=print_func,
    )


def _run_live_loop(
    *,
    output_root: Path,
    provider: str,
    default_model: str,
    dry_run: bool,
    max_turns: int,
    max_tokens: int,
    timeout: float,
    mineru_executable: str | None,
    input_func: Callable[[str], str],
    print_func: Callable[[str], None],
) -> None:
    """Coding-agent style loop: the LLM autonomously drives tools, with session
    memory across turns and Ctrl-C interruption that returns to the prompt."""
    session: LiveAgentSession | None = None
    current_doc: str | None = None
    chat_history: list[dict[str, str]] = []
    workspace_root = Path.cwd().resolve()
    while True:
        try:
            raw = input_func("data-agent> ").strip()
        except (EOFError, KeyboardInterrupt):
            print_func("\nbye")
            return
        if not raw:
            continue
        if raw in {"/exit", "/quit", "exit", "quit"}:
            print_func("bye")
            return
        if raw in {"/help", "help", "?"}:
            print_func(render_help())
            continue
        if raw == "/status":
            print_func(
                render_status(
                    provider=provider,
                    model=default_model,
                    output_root=output_root,
                    pending=None,
                    execution_mode="live",
                    max_turns=max_turns,
                    max_tokens=max_tokens,
                )
            )
            print_func(f"current_document: {current_doc or '(none yet)'}")
            print_func(f"session: {'active' if session is not None else 'not started'}")
            continue
        if raw == "/reset":
            session = None
            current_doc = None
            print_func("Session cleared. The next message starts a fresh conversation.")
            continue

        workspace_answer = answer_local_workspace_request(raw, workspace_root=workspace_root, current_doc=current_doc)
        if workspace_answer:
            print_func(workspace_answer)
            continue

        target_path = _extract_existing_path(raw, workspace_root=workspace_root, allow_directories=True)
        path = target_path if target_path and Path(target_path).is_file() else ""
        directory_path = target_path if target_path and Path(target_path).is_dir() else ""
        url = _extract_url(raw)
        context = _build_workspace_context(workspace_root=workspace_root, output_root=output_root, current_doc=current_doc)
        route = route_interactive_intent(
            raw,
            provider=provider,
            model=default_model,
            workspace_context=context,
            timeout=timeout,
            path=path,
            directory_path=directory_path,
            url=url,
            current_doc=current_doc,
        )
        if route.get("action") == "chat":
            answer = _chatbot_reply(
                raw,
                provider=provider,
                model=default_model,
                output_root=output_root,
                current_doc=current_doc,
                timeout=timeout,
                history=chat_history,
                workspace_context=context,
            )
            chat_history.extend([{"role": "user", "content": raw}, {"role": "assistant", "content": answer}])
            chat_history = chat_history[-12:]
            print_func(answer)
            continue
        if route.get("action") == "clarify":
            print_func(str(route.get("message") or "请补充要处理的文件路径、URL 或目录范围。"))
            continue
        if route.get("action") == "current_directory_batch":
            batch_workspace = _resolve_workspace_directory(
                str(route.get("directory_path") or route.get("input_path") or directory_path or ""),
                workspace_root=workspace_root,
            ) or workspace_root
            print_func(f"DeepSeek 已识别为目录批量资料处理任务，目标目录: {batch_workspace}，开始执行目录级 workflow...")
            if dry_run:
                print_func(json.dumps(route, ensure_ascii=False, indent=2))
                continue
            try:
                print_func(
                    render_directory_batch_plan(
                        workspace_root=batch_workspace,
                        task=str(route.get("task") or raw),
                        profile=str(route.get("profile") or "auto"),
                        runner=str(route.get("runner") or "auto"),
                        max_files=_safe_positive_int(route.get("max_files")),
                    )
                )
                batch_result = run_current_directory_batch(
                    workspace_root=batch_workspace,
                    output_root=output_root,
                    task=str(route.get("task") or raw),
                    profile=str(route.get("profile") or "auto"),
                    runner=str(route.get("runner") or "auto"),
                    provider=provider,
                    model=default_model,
                    max_files=_safe_positive_int(route.get("max_files")),
                    progress_callback=lambda item: _print_runtime_harness_gate(item, print_func=print_func),
                )
                print_func(render_directory_batch_result(batch_result))
            except Exception as exc:  # noqa: BLE001 - keep REPL alive
                print_func(f"directory batch workflow error: {str(exc)[-500:]}")
            continue
        if route.get("input_path") and not path:
            candidate = Path(str(route["input_path"]))
            if not candidate.is_absolute():
                candidate = workspace_root / candidate
            if candidate.exists():
                path = str(candidate.resolve())
        if route.get("url") and not url:
            url = str(route["url"])

        if not _is_document_workflow_request(raw, current_doc=current_doc, path=path, url=url):
            answer = _chatbot_reply(
                raw,
                provider=provider,
                model=default_model,
                output_root=output_root,
                current_doc=current_doc,
                timeout=timeout,
                history=chat_history,
                workspace_context=context,
            )
            chat_history.extend([{"role": "user", "content": raw}, {"role": "assistant", "content": answer}])
            chat_history = chat_history[-12:]
            print_func(answer)
            continue

        if not path and not url and not current_doc:
            print_func(
                "我可以处理这个数据/文档任务，但还没有当前文档。请把 PDF/HTML/DOCX/PPTX 路径或网页 URL 一起发给我。"
            )
            continue

        if dry_run:
            print_func(
                f"[dry-run] would run the live workflow. document={path or url or current_doc or '(none)'}; message={raw!r}"
            )
            continue

        try:
            if session is None:
                session = _build_live_session(
                    provider=provider,
                    model=default_model,
                    output_root=output_root,
                    workspace_root=workspace_root,
                    max_turns=max_turns,
                    max_tokens=max_tokens,
                    timeout=timeout,
                    mineru_executable=mineru_executable,
                )
            if path:
                current_doc = path
                default_parser, routing_note = _route_for_document(path, raw)
                session.set_current_document(path, default_pdf_parser=default_parser, routing_note=routing_note)
                print_func(
                    render_single_document_plan(
                        input_path=Path(path),
                        task=raw,
                        profile=str(route.get("profile") or "auto"),
                        runner=str(route.get("runner") or "auto"),
                    )
                )
            print_func("Running live tool-calling workflow... (Ctrl-C to interrupt)")
            result = session.send(raw)
            print_func(render_live_result(result))
        except KeyboardInterrupt:
            print_func("\n(interrupted — back to prompt; session kept. Send a new instruction or /reset.)")
            continue
        except Exception as exc:  # noqa: BLE001 - surface live errors without killing the REPL
            print_func(f"live workflow error: {str(exc)[-300:]}")
            continue


def _build_live_session(
    *,
    provider: str,
    model: str,
    output_root: Path,
    workspace_root: Path,
    max_turns: int,
    max_tokens: int,
    timeout: float,
    mineru_executable: str | None,
) -> LiveAgentSession:
    resolved_provider, resolved_model, api_key, base_url = _resolve_provider(provider, model=model)
    run_id = uuid.uuid4().hex[:12]
    runner = MinerURunner(executable=mineru_executable) if mineru_executable else None
    runners = _build_live_mineru_runners(runner)
    output_dir = Path(output_root).expanduser().resolve() / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    return LiveAgentSession(
        output_dir=output_dir,
        provider=resolved_provider,
        model=resolved_model,
        api_key=api_key,
        base_url=base_url,
        max_turns=max_turns,
        max_tokens=max_tokens,
        timeout=timeout,
        runners=runners,
        workspace_root=workspace_root,
        run_id=run_id,
    )


def _has_mineru_token() -> bool:
    return bool(os.getenv("MINERU_PRECISE_API_TOKEN") or os.getenv("MINERU_API_TOKEN"))


def _route_for_document(path: str, text: str) -> tuple[str, str]:
    """Rule-based default PDF parser for the document; the LLM may still override it."""
    try:
        metadata = build_input_metadata(Path(path))
        routing = build_workflow_routing(
            input_metadata=metadata,
            task=text,
            precise_api_token_available=_has_mineru_token(),
            local_cli_available=True,
        )
    except Exception as exc:  # noqa: BLE001
        return "auto", f"router unavailable ({str(exc)[-120:]}); default parser=auto"
    selected = routing.selected_runner
    if str(metadata.get("suffix") or "").lower() == ".pdf" and metadata.get("has_text_layer") is True:
        note = (
            f"router initial PDF parser=local because a text layer is available; "
            f"planned runner={selected}; Harness may upgrade during parse_pdf if layout/table risks are confirmed."
        )
        return "local", note
    default_parser = selected if selected in PDF_PARSER_CHOICES else "auto"
    reason = routing.reasons[0] if routing.reasons else ""
    return default_parser, f"router selected runner={selected} ({reason})"


def render_live_result(result: dict[str, Any]) -> str:
    selected_skill = result.get("selected_skill") if isinstance(result.get("selected_skill"), dict) else {}
    answer_validation = result.get("answer_validation") if isinstance(result.get("answer_validation"), dict) else {}
    lines = [
        "Completed live Agent workflow. 已完成 Data Agent 工作流。",
        f"  run_id: {result.get('run_id')}",
        f"  状态: {result.get('status')}",
    ]
    if result.get("provider") or result.get("model"):
        lines.append(f"  模型: {result.get('provider', '')}/{result.get('model', '')}".rstrip("/"))
    if selected_skill:
        skill_name = selected_skill.get("name") or selected_skill.get("skill_id") or "unknown"
        reason = selected_skill.get("reason") or ""
        lines.append(f"  任务策略: {skill_name}" + (f" ({reason})" if reason else ""))

    tool_steps = _render_human_tool_steps(result.get("tool_sequence") or [])
    if tool_steps:
        lines.extend(["", "工具使用:"])
        lines.extend(tool_steps)

    parse_runtime = _render_parse_runtime(result.get("parse_runtime"))
    if parse_runtime:
        lines.extend(["", "解析路径:"])
        lines.extend(parse_runtime)

    runtime_events = _render_live_runtime_harness_events(result.get("runtime_harness_events"))
    if runtime_events:
        lines.extend(["", "执行中 Harness 拦截:"])
        lines.extend(runtime_events)

    if answer_validation:
        status = "通过" if answer_validation.get("ok") else "需复核"
        recommendation = answer_validation.get("recommendation") or ""
        lines.extend(["", f"答案校验: {status}" + (f" ({recommendation})" if recommendation else "")])

    answer = str(result.get("final_answer") or "").strip()
    if answer:
        lines.extend(["", "结果:", _indent_multiline(_truncate_text(answer, 1200))])

    lines.extend(
        [
            "",
            "交付物:",
            f"  summary: {result.get('summary_path')}",
            f"  trace: {result.get('trace_path')}",
        ]
    )
    if result.get("result_path"):
        lines.append(f"  result: {result.get('result_path')}")
    return "\n".join(lines)


def _run_classic_loop(
    *,
    output_root: Path,
    provider: str,
    default_model: str,
    dry_run: bool,
    max_turns: int,
    max_tokens: int,
    timeout: float,
    mineru_executable: str | None,
    input_func: Callable[[str], str],
    print_func: Callable[[str], None],
) -> None:
    """Deterministic single-shot mode: natural language -> parameters -> confirm -> agent.run."""
    pending: ChatCommand | None = None
    while True:
        try:
            raw = input_func("data-agent> ").strip()
        except (EOFError, KeyboardInterrupt):
            print_func("\nbye")
            return
        if not raw:
            continue
        if raw in {"/exit", "/quit", "exit", "quit"}:
            print_func("bye")
            return
        if raw in {"/help", "help", "?"}:
            print_func(render_help())
            continue
        if raw == "/status":
            print_func(
                render_status(
                    provider=provider,
                    model=default_model,
                    output_root=output_root,
                    pending=pending,
                    execution_mode="classic",
                    max_turns=max_turns,
                    max_tokens=max_tokens,
                )
            )
            continue
        if raw == "/run":
            if pending is None:
                print_func("No pending plan. Describe a document task first.")
                continue
            _execute_or_preview(
                pending,
                dry_run=dry_run,
                print_func=print_func,
                execution_mode="classic",
                provider=provider,
                max_turns=max_turns,
                max_tokens=max_tokens,
                timeout=timeout,
                mineru_executable=mineru_executable,
            )
            pending = None
            continue

        workspace_answer = answer_local_workspace_request(raw, workspace_root=Path.cwd().resolve(), current_doc=None)
        if workspace_answer:
            print_func(workspace_answer)
            continue

        command = plan_chat_command(raw, output_root=output_root, provider=provider, model=default_model)
        if command.action != "run":
            print_func(command.rationale or "I can help with document parsing tasks. Try: parse <file> and extract fields.")
            continue
        pending = command
        print_func(render_plan(command))
        answer = input_func("Run this plan? [Y/n] ").strip().lower()
        if answer in {"", "y", "yes"}:
            _execute_or_preview(
                command,
                dry_run=dry_run,
                print_func=print_func,
                execution_mode="classic",
                provider=provider,
                max_turns=max_turns,
                max_tokens=max_tokens,
                timeout=timeout,
                mineru_executable=mineru_executable,
            )
            pending = None
        else:
            print_func("Plan saved. Use /run to execute it, or describe a new task.")


def plan_chat_command(
    text: str,
    *,
    output_root: Path = Path("runs/chat"),
    provider: str = "deepseek",
    model: str | None = None,
) -> ChatCommand:
    heuristic = _heuristic_command(text, output_root=output_root, model=model or DEFAULT_DEEPSEEK_MODEL)
    if provider != "deepseek":
        return heuristic
    if not os.getenv("DEEPSEEK_API_KEY"):
        heuristic.rationale = "DeepSeek key is not configured; using local heuristic planner."
        return heuristic
    try:
        llm_command = _deepseek_plan(text, fallback=heuristic, model=model or DEFAULT_DEEPSEEK_MODEL)
    except Exception as exc:
        heuristic.rationale = f"DeepSeek planning failed; using local heuristic planner. error={str(exc)[-300:]}"
        return heuristic
    return llm_command


def render_welcome(*, provider: str, model: str, output_root: Path, execution_mode: str = "live") -> str:
    width = min(max(shutil.get_terminal_size((96, 24)).columns, 72), 112)
    title = " MinerU Data Agent Harness "
    line = "=" * width
    left = [
        "Welcome back.",
        "",
        "Natural-language document workflow",
        f"model: {model}",
        f"mode: {execution_mode}",
        f"output: {output_root}",
    ]
    right = [
        "Try:",
        "  parse examples/cases/case_1_financial_report.html and check totals",
        "  use precise api for examples/real_pdfs/complex_financial_report.pdf",
        "",
        "Commands: /help /status /run /exit",
    ]
    body = _two_columns(left, right, width=width)
    return "\n".join([line, title.center(width), body, line, ""])


def render_help() -> str:
    return "\n".join(
        [
            "Commands:",
            "  /help      Show this help.",
            "  /status    Show model, output root, and pending plan.",
            "  /run       Execute the last proposed plan.",
            "  /exit      Leave the interactive harness.",
            "  ls/dir     List files in the current working directory.",
            "  pwd        Show the current working directory.",
            "",
            "Chat behavior:",
            "  Natural-language messages go through the configured LLM.",
            "  Document/data requests with a file path or URL start the live tool workflow.",
            "  Local commands remain deterministic: /help /status /exit ls/dir pwd.",
            "",
            "Natural language examples:",
            "  parse examples/cases/case_1_financial_report.html and extract financial fields",
            "  use precise api for examples/real_pdfs/complex_financial_report.pdf, verify table totals",
            "  read examples/cases/case_3_standard_contract.html and summarize clauses with evidence",
        ]
    )


def render_status(
    *,
    provider: str,
    model: str,
    output_root: Path,
    pending: ChatCommand | None,
    execution_mode: str = "live",
    max_turns: int = DEFAULT_MAX_TURNS,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> str:
    lines = [
        f"provider: {provider}",
        f"model: {model}",
        f"execution_mode: {execution_mode}",
        f"live_limits: max_turns={max_turns}, max_tokens={max_tokens}",
        f"output_root: {output_root}",
        f"deepseek_key: {'configured' if os.getenv('DEEPSEEK_API_KEY') else 'missing'}",
        f"mineru_precise_token: {'configured' if (os.getenv('MINERU_PRECISE_API_TOKEN') or os.getenv('MINERU_API_TOKEN')) else 'missing'}",
    ]
    if pending:
        lines.extend(["", "pending:", json.dumps(pending.to_jsonable(), ensure_ascii=False, indent=2)])
    return "\n".join(lines)


def answer_builtin_question(text: str, *, provider: str, model: str, output_root: Path) -> str | None:
    lowered = text.lower().strip()
    compact = re.sub(r"\s+", "", text.lower())
    if _contains_any(
        compact,
        [
            "你是什么模型",
            "你用什么模型",
            "模型是什么",
            "当前模型",
            "什么模型",
            "浣犳槸浠€涔堟ā鍨",
            "浣犵敤浠€涔堟ā鍨",
            "妯″瀷鏄粈涔",
            "褰撳墠妯″瀷",
        ],
    ) or _contains_any(
        lowered,
        ["what model", "which model", "current model"],
    ):
        return "\n".join(
            [
                f"我是 MinerU Data Agent Harness 的交互式终端入口。",
                f"当前自然语言规划模型: {provider}/{model}",
                "角色分工: DeepSeek 负责理解任务和规划，MinerU 负责文档解析，Harness 负责路由、质量检查、恢复和交付物输出。",
            ]
        )
    if _contains_any(compact, ["你是谁", "你能做什么", "介绍一下", "浣犳槸璋", "浣犺兘鍋氫粈涔", "浠嬬粛涓€涓"]) or _contains_any(
        lowered,
        ["who are you", "what can you do"],
    ):
        return "\n".join(
            [
                "我是面向复杂文档处理的 Data Agent Harness。",
                "你可以直接用自然语言让我解析 PDF/HTML/Office 文档、抽取结构化字段、检查质量、生成 trace 和 document_skill 包。",
                "示例: parse examples/cases/case_1_financial_report.html and extract financial fields",
            ]
        )
    if _contains_any(compact, ["配置了吗", "key配置", "api配置", "状态", "閰嶇疆浜嗗悧", "鐘舵€"]) or _contains_any(lowered, ["configured", "api key"]):
        return render_status(provider=provider, model=model, output_root=output_root, pending=None)
    return None


def answer_local_workspace_request(text: str, *, workspace_root: Path, current_doc: str | None) -> str | None:
    lowered = text.lower().strip()
    compact = re.sub(r"\s+", "", lowered)
    if compact in {"pwd", "cwd"}:
        return f"当前工作目录: `{workspace_root}`"

    if compact in {"ls", "dir"}:
        return _render_directory_listing(workspace_root)

    if compact in {"currentdocument", "currentfile"}:
        return f"当前文档: `{current_doc}`" if current_doc else "当前还没有加载文档。你可以直接输入文件名或路径让我解析。"
    return None


def route_interactive_intent(
    text: str,
    *,
    provider: str,
    model: str,
    workspace_context: dict[str, Any],
    timeout: float,
    path: str,
    directory_path: str = "",
    url: str,
    current_doc: str | None,
) -> dict[str, Any]:
    if provider == "deepseek" and os.getenv("DEEPSEEK_API_KEY"):
        try:
            return _deepseek_route_interactive_intent(
                text,
                model=model,
                workspace_context=workspace_context,
                timeout=timeout,
                path=path,
                directory_path=directory_path,
                url=url,
                current_doc=current_doc,
            )
        except Exception:
            pass
    return _fallback_route_interactive_intent(
        text,
        workspace_context=workspace_context,
        path=path,
        directory_path=directory_path,
        url=url,
        current_doc=current_doc,
    )


def _deepseek_route_interactive_intent(
    text: str,
    *,
    model: str,
    workspace_context: dict[str, Any],
    timeout: float,
    path: str,
    directory_path: str,
    url: str,
    current_doc: str | None,
) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are the intent router for MinerU Data Agent Harness. "
                    "Return strict JSON only. Decide whether the user wants normal chat, clarification, "
                    "single-document processing, or current-directory batch processing. "
                    "Use current_directory_batch when the user refers to current path/current directory/these files/this batch "
                    "or names an existing subdirectory/folder that contains supported documents "
                    "and asks to parse, extract, analyze, organize, OCR, or build AI-friendly document packages. "
                    "If the user names a folder from workspace_context.directories, set directory_path to that folder path. "
                    "If the user asks for precise/精准/精确 parsing, set runner=precise-api. "
                    "Do not choose a workflow for casual chat."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "user_text": text,
                        "detected_path": path,
                        "detected_directory_path": directory_path,
                        "detected_url": url,
                        "current_document": current_doc,
                        "workspace_context": workspace_context,
                        "allowed_json_schema": {
                            "action": "chat|clarify|single_document|current_directory_batch",
                            "task": "natural-language task to execute",
                            "input_path": "optional file path for single_document",
                            "directory_path": "optional directory path for current_directory_batch",
                            "url": "optional URL for single_document",
                            "profile": "auto|general_document|financial_report|standard_or_contract|workflow_or_diagram|low_quality_ocr",
                            "runner": "auto|agent-api|precise-api|cli",
                            "max_files": "optional integer",
                            "message": "short user-facing clarification message",
                            "reason": "short reason",
                        },
                        "policy": [
                            "For current-directory batch, one original source document should become one document_skill package.",
                            "Prefer local parsing for HTML/Office and text-layer PDFs.",
                            "Use OCR pipeline for scanned PDFs; do not use whole-document VLM by default.",
                            "VLM is only for focused charts/tables/layout/cross-page/quality-degraded page chunks.",
                            "Ask clarify if the user asks to process documents but no source is available.",
                        ],
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        "temperature": 0.0,
        "max_tokens": 512,
    }
    headers = {"Authorization": f"Bearer {os.environ['DEEPSEEK_API_KEY']}", "Content-Type": "application/json"}
    with httpx.Client(timeout=timeout) as client:
        response = client.post(_chat_completions_url(DEFAULT_DEEPSEEK_BASE_URL), headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
    content = str(data["choices"][0]["message"].get("content") or "{}")
    return _normalize_interactive_route(_parse_json_object(content), fallback_text=text)


def _fallback_route_interactive_intent(
    text: str,
    *,
    workspace_context: dict[str, Any],
    path: str,
    directory_path: str = "",
    url: str,
    current_doc: str | None,
) -> dict[str, Any]:
    compact = re.sub(r"\s+", "", text.lower())
    if path or url:
        return {"action": "single_document", "task": text, "input_path": path, "url": url, "profile": "auto"}
    referenced_dir = directory_path or _find_referenced_workspace_dir(text, workspace_context)
    has_batch_reference = _contains_any(compact, ["当前目录", "当前路径", "这些文件", "这批文件", "这批资料", "目录下", "文件夹下", "文件夹"])
    has_task = _contains_any(compact, ["解析", "提取", "抽取", "分析", "整理", "处理", "ocr", "parse", "extract", "analyze"])
    files = workspace_context.get("files") if isinstance(workspace_context.get("files"), list) else []
    if has_task and (referenced_dir or (has_batch_reference and files)):
        return {
            "action": "current_directory_batch",
            "task": text,
            "profile": "auto",
            "runner": _runner_from_text(text),
            "directory_path": referenced_dir,
            "reason": "fallback directory batch intent",
        }
    if _is_document_workflow_request(text, current_doc=current_doc, path=path, url=url):
        return {"action": "clarify", "message": "请补充要处理的文件路径、URL，或说明要处理当前目录下哪些文件。"}
    return {"action": "chat"}


def _normalize_interactive_route(data: dict[str, Any], *, fallback_text: str) -> dict[str, Any]:
    action = str(data.get("action") or "chat").strip().lower()
    if action not in {"chat", "clarify", "single_document", "current_directory_batch"}:
        action = "chat"
    profile = str(data.get("profile") or "auto").strip()
    if profile not in PROFILE_CHOICES | {"auto"}:
        profile = "auto"
    runner = str(data.get("runner") or "auto").strip().lower()
    if runner not in RUNNER_CHOICES:
        runner = "auto"
    if runner == "auto":
        runner = _runner_from_text(fallback_text)
    return {
        "action": action,
        "task": str(data.get("task") or fallback_text),
        "input_path": str(data.get("input_path") or ""),
        "directory_path": str(data.get("directory_path") or ""),
        "url": str(data.get("url") or ""),
        "profile": profile,
        "runner": runner,
        "max_files": _safe_positive_int(data.get("max_files")),
        "message": str(data.get("message") or ""),
        "reason": str(data.get("reason") or "DeepSeek interactive intent router"),
    }


def _build_workspace_context(*, workspace_root: Path, output_root: Path, current_doc: str | None) -> dict[str, Any]:
    files = _workspace_document_files(workspace_root)
    directories = _workspace_directories(workspace_root)
    return {
        "cwd": str(workspace_root),
        "output_root": str(output_root),
        "current_document": current_doc or "",
        "supported_file_count": len(files),
        "files": files[:80],
        "directories": directories[:40],
        "available_tools": [
            "list_directory",
            "parse_single_document",
            "parse_current_directory",
            "build_source_packages",
            "build_corpus_catalog",
            "load_document_skill",
            "search_corpus",
        ],
    }


def _workspace_document_files(workspace_root: Path) -> list[dict[str, Any]]:
    files = []
    for item in sorted(workspace_root.iterdir(), key=lambda path: path.name.lower()):
        if not item.is_file() or item.suffix.lower() not in SUPPORTED_WORKSPACE_SUFFIXES:
            continue
        meta: dict[str, Any] = {
            "name": item.name,
            "path": str(item),
            "suffix": item.suffix.lower(),
            "size_bytes": item.stat().st_size,
        }
        try:
            meta.update(build_input_metadata(item))
        except Exception:
            pass
        files.append(meta)
    return files


def _workspace_directories(workspace_root: Path) -> list[dict[str, Any]]:
    directories: list[dict[str, Any]] = []
    for item in sorted(workspace_root.iterdir(), key=lambda path: path.name.lower()):
        if not item.is_dir():
            continue
        supported_files = [
            child
            for child in item.rglob("*")
            if child.is_file() and child.suffix.lower() in SUPPORTED_WORKSPACE_SUFFIXES
        ]
        directories.append(
            {
                "name": item.name,
                "path": str(item),
                "supported_file_count": len(supported_files),
                "sample_files": [child.name for child in supported_files[:12]],
            }
        )
    return directories


def run_current_directory_batch(
    *,
    workspace_root: Path,
    output_root: Path,
    task: str,
    profile: str = "auto",
    runner: str = "auto",
    provider: str = "deepseek",
    model: str | None = None,
    max_files: int | None = None,
    progress_callback: Any | None = None,
) -> dict[str, Any]:
    files = [Path(item["path"]) for item in _workspace_document_files(workspace_root)]
    if max_files:
        files = files[:max_files]
    if not files:
        return {"ok": False, "error": "no_supported_files", "workspace_root": str(workspace_root)}

    run_root = Path(output_root).expanduser().resolve() / datetime.now().strftime("%Y%m%d%H%M")
    batch_root = run_root / "raw_runs"
    manifest_path = run_root / "batch_manifest.json"
    tasks = _build_directory_batch_tasks(files, task=task, profile=profile)
    manifest = {
        "defaults": {"profile": profile, "backend": "pipeline", "method": "auto", "lang": "ch"},
        "tasks": tasks,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    llm_client = None
    if provider == "deepseek" and os.getenv("DEEPSEEK_API_KEY"):
        llm_client = DeepSeekLLMClient(model=model)
    primary_runner = _batch_primary_runner(runner)
    agent = MinerUDataAgent(
        primary_runner,
        llm_client=llm_client,
        fallback_mineru_runner=MinerURunner(executable=resolve_mineru_executable()),
        requested_runner=runner if runner in RUNNER_CHOICES else "auto",
        auto_runner=runner not in {"agent-api", "precise-api", "cli"},
    )
    batch_report = run_batch(
        manifest_path=manifest_path,
        output_root=batch_root,
        agent=agent,
        progress_callback=progress_callback,
    )
    package_report = build_source_document_packages(run_root=batch_root, source_root=workspace_root, output_root=run_root / "source_packages")
    return {
        "ok": True,
        "run_root": str(run_root),
        "manifest_path": str(manifest_path),
        "plan": _build_directory_batch_plan(files, task=task, profile=profile, runner=runner),
        "batch_report": batch_report,
        "package_report": package_report,
        "document_root": package_report.get("document_root"),
        "corpus_catalog": package_report.get("corpus_catalog"),
    }


def render_directory_batch_plan(
    *,
    workspace_root: Path,
    task: str,
    profile: str = "auto",
    runner: str = "auto",
    max_files: int | None = None,
) -> str:
    files = [Path(item["path"]) for item in _workspace_document_files(workspace_root)]
    if max_files:
        files = files[:max_files]
    if not files:
        return "执行计划: 当前目录没有可处理文档。"
    plan = _build_directory_batch_plan(files, task=task, profile=profile, runner=runner)
    lines = [
        "执行计划:",
        f"  文档数: {len(plan)}",
        f"  路由偏好: {runner if runner in RUNNER_CHOICES else 'auto'}",
    ]
    for index, item in enumerate(plan, start=1):
        pages = item.get("page_count")
        page_text = f"{pages} 页" if pages else "页数未知"
        text_layer = item.get("text_layer_label") or "文字层未知"
        layout_label = item.get("layout_label") or ""
        layout_text = f"，{layout_label}" if layout_label else ""
        chunks = item.get("chunk_count")
        chunk_text = f"，切分为 {chunks} 个页段" if chunks and chunks > 1 else ""
        lines.append(
            f"  {index}. {item.get('name')} -> {item.get('final_strategy')} "
            f"({page_text}，{text_layer}{layout_text}{chunk_text})"
        )
        lines.append(f"     初判: {item.get('initial_decision')}")
        if item.get("preflight_risk"):
            lines.append(f"     预检关注: {item.get('preflight_risk')}")
        lines.append(f"     计划策略: {item.get('reason')}")
        validation = item.get("validation_policy")
        if validation:
            lines.append(f"     重点校验: {validation}")
    return "\n".join(lines)


def render_single_document_plan(
    *,
    input_path: Path,
    task: str,
    profile: str = "auto",
    runner: str = "auto",
) -> str:
    plan = _build_directory_batch_plan([Path(input_path)], task=task, profile=profile, runner=runner)
    if not plan:
        return "执行计划: 未能识别可处理文档。"
    item = plan[0]
    pages = item.get("page_count")
    page_text = f"{pages} 页" if pages else "页数未知"
    text_layer = item.get("text_layer_label") or "文字层未知"
    layout_label = item.get("layout_label") or ""
    layout_text = f"，{layout_label}" if layout_label else ""
    chunks = item.get("chunk_count")
    chunk_text = f"，切分为 {chunks} 个页段" if chunks and chunks > 1 else ""
    lines = [
        "执行计划:",
        f"  文档: {item.get('name')}",
        f"  路由偏好: {runner if runner in RUNNER_CHOICES else 'auto'}",
        f"  计划路径: {item.get('final_strategy')} ({page_text}，{text_layer}{layout_text}{chunk_text})",
        f"  初判: {item.get('initial_decision')}",
    ]
    if item.get("preflight_risk"):
        lines.append(f"  预检关注: {item.get('preflight_risk')}")
    lines.append(f"  计划策略: {item.get('reason')}")
    if item.get("validation_policy"):
        lines.append(f"  重点校验: {item.get('validation_policy')}")
    return "\n".join(lines)


def _build_directory_batch_plan(
    files: list[Path],
    *,
    task: str,
    profile: str,
    runner: str = "auto",
) -> list[dict[str, Any]]:
    plan = []
    normalized_runner = runner if runner in RUNNER_CHOICES else "auto"
    for path in files:
        metadata: dict[str, Any] = {}
        try:
            metadata = build_input_metadata(path)
        except Exception as exc:  # noqa: BLE001
            metadata = {
                "filename": path.name,
                "suffix": path.suffix.lower(),
                "size_bytes": path.stat().st_size if path.exists() else 0,
                "probe_error": str(exc)[-200:],
            }
        routing = build_workflow_routing(
            input_metadata=metadata,
            task=task,
            profile=profile,
            requested_runner=normalized_runner,
            current_runner="auto",
            precise_api_token_available=_has_mineru_token(),
            local_cli_available=resolve_mineru_executable() is not None,
        )
        page_count = _safe_positive_int(metadata.get("page_count"))
        has_text_layer = metadata.get("has_text_layer")
        chunk_count = 1
        if path.suffix.lower() == ".pdf" and has_text_layer is False and page_count and page_count > 200:
            chunk_count = (page_count + 199) // 200
        method_label = _batch_plan_method_label(metadata, routing.selected_runner, chunk_count=chunk_count)
        initial_decision = _batch_initial_decision(metadata, normalized_runner)
        gate = _batch_harness_gate(metadata)
        reason = _batch_plan_reason(
            metadata,
            selected_runner=routing.selected_runner,
            chunk_count=chunk_count,
            requested_runner=normalized_runner,
        )
        plan.append(
            {
                "name": path.name,
                "path": str(path),
                "suffix": path.suffix.lower(),
                "page_count": page_count,
                "has_text_layer": has_text_layer,
                "text_layer_label": _text_layer_label(has_text_layer),
                "layout_label": _layout_label(metadata),
                "selected_runner": routing.selected_runner,
                "method_label": method_label,
                "final_strategy": method_label,
                "initial_decision": initial_decision,
                "harness_gate": gate.get("message", ""),
                "preflight_risk": gate.get("preflight_message", ""),
                "validation_policy": gate.get("validation_policy", ""),
                "chunk_count": chunk_count,
                "reason": reason,
            }
        )
    return plan


def _batch_plan_method_label(metadata: dict[str, Any], selected_runner: str, *, chunk_count: int) -> str:
    suffix = str(metadata.get("suffix") or "").lower()
    if suffix in {".html", ".htm", ".docx", ".pptx"}:
        return "本地结构解析"
    if suffix == ".pdf" and metadata.get("has_text_layer") is True and _has_pdf_harness_gate_risk(metadata):
        return "本地 PDF 文字层试读 + 质量门"
    if suffix == ".pdf" and metadata.get("has_text_layer") is True and selected_runner in {"native", "agent-api", "cli", "precise-api"}:
        return "本地 PDF 文字层优先"
    if suffix == ".pdf" and metadata.get("has_text_layer") is False and chunk_count > 1:
        return "扫描 PDF OCR 分段处理"
    if selected_runner == "precise-api":
        return "MinerU 精准 API"
    if selected_runner == "agent-api":
        return "MinerU Agent 轻量 API"
    if selected_runner == "cli":
        return "本地 MinerU CLI"
    return selected_runner or "自动路由"


def _batch_plan_reason(
    metadata: dict[str, Any],
    *,
    selected_runner: str,
    chunk_count: int,
    requested_runner: str,
) -> str:
    suffix = str(metadata.get("suffix") or "").lower()
    page_count = _safe_positive_int(metadata.get("page_count"))
    size = _format_size(int(metadata.get("size_bytes") or 0))
    if suffix in {".html", ".htm"}:
        if selected_runner == "native":
            return "本地 HTML 已经是结构化文本，优先用本地解析，避免不必要的远程调用。"
        return "用户或模型选择线上 HTML 解析，交给 MinerU-HTML 做远程规范化。"
    if suffix in {".docx", ".pptx"}:
        return "Office 文档可直接提取文本和结构，优先用本地解析保留低成本路径。"
    if suffix == ".pdf" and metadata.get("has_text_layer") is True:
        if _has_pdf_harness_gate_risk(metadata):
            if _has_table_risk(metadata):
                return "先以本地文字层作为低成本初始路径；执行中做文字层/版式/表格探测，由 Harness 质量门确认风险，风险成立时升级到 MinerU/VLM 保持结构，并用 OCR 或文字层做数字二次校验。"
            return "先以本地文字层作为低成本初始路径；执行中做文字层/版式探测，由 Harness 质量门确认双栏/阅读顺序风险，风险成立时升级到 MinerU 版面解析，本地文字层保留为校验证据。"
        return "检测到可提取文字层，优先用本地 PDF 文本解析；只有图表、跨页或质量异常再升级到 MinerU。"
    if suffix == ".pdf" and metadata.get("has_text_layer") is False:
        if chunk_count > 1:
            return f"未检测到可用文字层，且约 {page_count or '未知'} 页；按页段切分后走 OCR/精准解析，避免一次性处理过大。"
        if selected_runner == "precise-api" or requested_runner == "precise-api":
            return "未检测到可用文字层，按精确解析请求走 MinerU pipeline/OCR，并保留质量校验结果。"
        if selected_runner == "agent-api":
            return "未检测到可用文字层，但文件在轻量 API 限制内，先走 MinerU Agent 轻量解析。"
        return "未检测到可用文字层，需要 OCR 类解析；Harness 会在质量不足时触发恢复或升级。"
    if selected_runner == "precise-api":
        return f"文件大小约 {size}，按任务要求走 MinerU 精准 API，保留更完整的 Markdown/JSON 结果。"
    if selected_runner == "agent-api":
        return f"文件大小约 {size}，符合轻量 API 条件，优先选择低成本解析。"
    return "根据文件类型、页数、大小、文字层探测和用户任务目标自动选择处理路径。"


def _has_layout_reading_order_risk(metadata: dict[str, Any]) -> bool:
    return bool(
        metadata.get("is_complex_layout")
        or metadata.get("layout_risk") == "reading_order_risk"
        or metadata.get("layout_type") == "multi_column"
    )


def _has_table_risk(metadata: dict[str, Any]) -> bool:
    return bool(metadata.get("has_tables") or metadata.get("table_risk") == "table_structure_or_numeric_risk")


def _has_pdf_harness_gate_risk(metadata: dict[str, Any]) -> bool:
    return _has_layout_reading_order_risk(metadata) or _has_table_risk(metadata)


def _batch_initial_decision(metadata: dict[str, Any], requested_runner: str) -> str:
    suffix = str(metadata.get("suffix") or "").lower()
    if suffix in {".html", ".htm", ".docx", ".pptx"}:
        return "本地结构化读取"
    if suffix == ".pdf" and metadata.get("has_text_layer") is True:
        return "直接读取 PDF 文字层"
    if suffix == ".pdf" and metadata.get("has_text_layer") is False:
        return "无文字层，进入 OCR 路径"
    if requested_runner == "precise-api":
        return "用户请求高精度解析"
    if requested_runner == "agent-api":
        return "用户请求轻量 Agent API"
    return "按文件类型自动选择"


def _batch_harness_gate(metadata: dict[str, Any]) -> dict[str, str]:
    if str(metadata.get("suffix") or "").lower() != ".pdf" or metadata.get("has_text_layer") is not True:
        return {}
    reasons = []
    if _has_layout_reading_order_risk(metadata):
        reasons.append("双栏/复杂版式会破坏裸文本阅读顺序")
    if _has_table_risk(metadata):
        pages = _table_pages_label(metadata)
        reasons.append(f"检测到表格{pages}，需要保持行列结构")
    if not reasons:
        return {}
    validation = ""
    if _has_table_risk(metadata):
        validation = "VLM 保表格结构；OCR/文字层校验数字，冲突时标记复核。"
    else:
        validation = "本地文字层作为阅读顺序和内容一致性校验证据。"
    return {
        "message": "；".join(reasons) + "，拦截直接读取并升级。",
        "preflight_message": "；".join(reasons) + "，执行时通过文字层/版式探测由质量门确认是否升级。",
        "validation_policy": validation,
    }


def _table_pages_label(metadata: dict[str, Any]) -> str:
    pages = metadata.get("table_pages")
    if isinstance(pages, list) and pages:
        shown = ", ".join(str(item) for item in pages[:8])
        suffix = "..." if len(pages) > 8 else ""
        return f"页 {shown}{suffix}"
    return ""


def _text_layer_label(value: Any) -> str:
    if value is True:
        return "有文字层"
    if value is False:
        return "无可用文字层"
    return "文字层未知"


def _layout_label(metadata: dict[str, Any]) -> str:
    if _has_layout_reading_order_risk(metadata):
        pages = _safe_positive_int(metadata.get("multi_column_pages"))
        sampled = _safe_positive_int(metadata.get("layout_sampled_pages"))
        if pages and sampled:
            return f"复杂版式/双栏风险 {pages}/{sampled} 页"
        return "复杂版式/双栏风险"
    if metadata.get("layout_risk") == "low":
        return "版式风险低"
    return ""


def _build_directory_batch_tasks(files: list[Path], *, task: str, profile: str) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for path in files:
        metadata = {}
        try:
            metadata = build_input_metadata(path)
        except Exception:
            metadata = {}
        page_count = _safe_positive_int(metadata.get("page_count"))
        has_text_layer = metadata.get("has_text_layer")
        suffix = path.suffix.lower()
        if suffix == ".pdf" and has_text_layer is False and page_count and page_count > 200:
            for start_page in range(1, page_count + 1, 200):
                end_page = min(start_page + 199, page_count)
                tasks.append(
                    _directory_batch_task(
                        path,
                        task=task,
                        profile="low_quality_ocr" if profile == "auto" else profile,
                        index=len(tasks) + 1,
                        start_page=start_page,
                        end_page=end_page,
                        page_count=page_count,
                    )
                )
            continue
        tasks.append(_directory_batch_task(path, task=task, profile=profile, index=len(tasks) + 1))
    return tasks


def _directory_batch_task(
    path: Path,
    *,
    task: str,
    profile: str,
    index: int,
    start_page: int | None = None,
    end_page: int | None = None,
    page_count: int | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "id": f"doc_{index:03d}",
        "input": str(path),
        "source_file": path.name,
        "task": task,
        "profile": profile,
        "backend": "pipeline",
        "method": "auto",
        "lang": "ch",
    }
    if start_page is not None or end_page is not None:
        item["page_range"] = _format_page_range(start_page, end_page)
        item["start_page"] = start_page
        item["end_page"] = end_page
        item["task"] = f"{task} 原始文件《{path.name}》页段 {item['page_range']}。"
        item["method"] = "ocr"
        item["page_count"] = page_count
    return item


def render_directory_batch_result(result: dict[str, Any]) -> str:
    if not result.get("ok"):
        return f"目录批处理未执行: {result.get('error')}"
    batch = result.get("batch_report") or {}
    package = result.get("package_report") or {}
    lines = [
        "Completed current-directory Data Agent workflow.",
        "",
        "工具使用:",
        f"  1. 目录扫描: 发现并筛选可处理文档，生成批处理 manifest。",
        f"  2. 批量解析: 已完成 {batch.get('completed', 0)}/{batch.get('total', 0)} 个任务，失败 {batch.get('failed', 0)} 个。",
    ]
    gate_lines = _render_runtime_harness_gates(batch)
    if gate_lines:
        lines.extend(["", "执行中 Harness 拦截:"])
        lines.extend(gate_lines)
    lines.extend(
        [
            f"  3. 资料包构建: 按原始资料聚合为 {package.get('total_source_documents', 0)} 个 source package。",
            f"  4. AI 友好交付: 输出 document_skill、retrieval chunks、trace 和 corpus catalog。",
            "",
            "交付物:",
            f"  output: {result.get('document_root')}",
            f"  catalog: {(result.get('corpus_catalog') or {}).get('catalog_json', '')}",
        ]
    )
    return "\n".join(lines)


def _print_runtime_harness_gate(item: dict[str, Any], *, print_func: Callable[[str], None]) -> None:
    text = _render_runtime_harness_gate_item(item)
    if text:
        print_func(text)


def _render_runtime_harness_gate_item(item: dict[str, Any]) -> str:
    gate = item.get("harness_gate")
    if not isinstance(gate, dict) or not gate.get("blocked"):
        return ""
    source = item.get("source_file") or item.get("input") or item.get("id") or "unknown"
    target = gate.get("target") or "layout-aware parser"
    reason = gate.get("reason") or "运行时质量/结构风险"
    lines = [
        f"执行中发现风险，Harness 拦截: {source}",
        f"  初始路径: {gate.get('initial_decision', 'direct-read')} -> 升级到: {target}",
        f"  原因: {reason}",
    ]
    actions = gate.get("actions")
    if isinstance(actions, list):
        for action in actions[:3]:
            if not isinstance(action, dict):
                continue
            label = action.get("action") or "check"
            action_reason = action.get("reason") or ""
            pages = action.get("pages")
            page_text = f" pages={pages}" if pages else ""
            lines.append(f"  - {label}{page_text}: {action_reason}")
    return "\n".join(lines)


def _render_runtime_harness_gates(batch: dict[str, Any]) -> list[str]:
    items = batch.get("items")
    if not isinstance(items, list):
        return []
    lines = []
    for item in items:
        if not isinstance(item, dict):
            continue
        gate = item.get("harness_gate")
        if not isinstance(gate, dict) or not gate.get("blocked"):
            continue
        source = item.get("source_file") or item.get("input") or item.get("id") or "unknown"
        reason = gate.get("reason") or "运行时风险门拦截了初始解析路径"
        target = gate.get("target") or "layout-aware parser"
        lines.append(f"  - {source}: 初始 {gate.get('initial_decision', 'direct-read')} 被拦截，升级到 {target}。原因: {reason}")
        actions = gate.get("actions")
        if isinstance(actions, list):
            for action in actions[:3]:
                if isinstance(action, dict):
                    label = action.get("action") or "check"
                    action_reason = action.get("reason") or ""
                    pages = action.get("pages")
                    page_text = f" pages={pages}" if pages else ""
                    lines.append(f"    · {label}{page_text}: {action_reason}")
    return lines


def _render_live_runtime_harness_events(events: Any) -> list[str]:
    if not isinstance(events, list):
        return []
    lines: list[str] = []
    for event in events:
        if not isinstance(event, dict) or not event.get("blocked"):
            continue
        source = event.get("source_file") or "document"
        initial = event.get("initial_decision") or "direct-read"
        target = event.get("target") or "layout-aware parser"
        backend = event.get("backend") or ""
        target_text = f"{target}/{backend}" if backend else str(target)
        reason = event.get("reason") or "运行时风险门拦截了初始解析路径"
        lines.append(f"  - {source}: 初始 {initial} 被拦截，升级到 {target_text}。原因: {reason}")
        actions = event.get("actions")
        if isinstance(actions, list):
            for action in actions[:3]:
                if isinstance(action, dict):
                    label = action.get("action") or "check"
                    action_reason = action.get("reason") or ""
                    pages = action.get("pages")
                    page_text = f" pages={pages}" if pages else ""
                    lines.append(f"    · {label}{page_text}: {action_reason}")
    return lines


def _render_parse_runtime(value: Any) -> list[str]:
    if not isinstance(value, dict) or not value:
        return []
    kind = value.get("kind") or "document"
    parser = value.get("parser") or ""
    backend = value.get("backend") or ""
    route = str(parser)
    if backend:
        route = f"{route}/{backend}" if route else str(backend)
    if not route:
        route = str(kind)
    details = []
    if value.get("page_count") is not None:
        details.append(f"页数={value.get('page_count')}")
    if value.get("has_text_layer") is not None:
        details.append(f"文字层={'有' if value.get('has_text_layer') else '无'}")
    if value.get("blocks") is not None:
        details.append(f"内容块={value.get('blocks')}")
    if value.get("markdown_chars") is not None:
        details.append(f"Markdown字符={value.get('markdown_chars')}")
    suffix = f" ({'，'.join(details)})" if details else ""
    return [f"  - {kind}: {route}{suffix}"]


def _safe_positive_int(value: Any) -> int | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _render_human_tool_steps(tool_sequence: list[Any]) -> list[str]:
    steps: list[str] = []
    previous = ""
    for raw_name in tool_sequence:
        name = str(raw_name)
        if not name:
            continue
        label, purpose = _human_tool_description(name)
        if not label:
            continue
        if name == previous and steps:
            steps[-1] += "；重复调用用于补充或重试。"
            continue
        steps.append(f"  {len(steps) + 1}. {label}: {purpose}")
        previous = name
    return steps


def _human_tool_description(name: str) -> tuple[str, str]:
    descriptions = {
        "select_skill": ("选择任务策略", "根据用户目标选择抽取、审计、恢复或综述等处理策略。"),
        "parse_html": ("本地 HTML 解析", "直接读取网页结构，低成本生成 Markdown 与内容块。"),
        "parse_office": ("Office 文档解析", "读取 DOCX/PPTX 文本、段落与基础结构。"),
        "parse_url": ("在线 URL 解析", "下载网页或远程文档，并按类型调用 MinerU API。"),
        "parse_pdf": ("PDF 智能解析", "按成本和质量选择本地文字层、轻量 API、精准 API 或局部 VLM。"),
        "build_extracted": ("结构化抽取", "把解析内容整理成章节、表格、键值、数字事实和证据视图。"),
        "validate_quality": ("质量检查", "检查空结果、乱码、页级证据、表格/字段质量等风险。"),
        "clean_text": ("文本恢复", "清理 OCR/编码噪声后重新进入结构化抽取。"),
        "plan_escalation": ("细粒度升级计划", "识别需要局部 OCR/VLM 重试的页段或证据块。"),
        "compare_parsers": ("多解析器一致性校验", "对比 VLM、OCR、文字层结果，标记疑似幻觉或冲突。"),
        "query_extracted": ("证据检索", "从已抽取结构中检索相关字段、段落、表格和数字事实。"),
        "export_retrieval": ("检索包导出", "生成 retrieval chunks，便于后续 RAG 或人工复核。"),
        "validate_answer": ("答案校验", "检查最终回答的证据支撑、数字引用和简单算术一致性。"),
        "finalize": ("结果交付", "在通过校验后提交最终回答和证据列表。"),
    }
    return descriptions.get(name, (name, "执行 Harness 内部工具步骤，完整细节见 trace。"))


def _truncate_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + f"... [已截断，完整内容见 summary/trace，共 {len(text)} 字符]"


def _indent_multiline(text: str, prefix: str = "  ") -> str:
    return "\n".join(prefix + line if line else prefix.rstrip() for line in text.splitlines())


def _resolve_workspace_directory(raw: str, *, workspace_root: Path) -> Path | None:
    text = raw.strip().strip('"').strip("'").strip("`")
    if not text:
        return None
    candidate = Path(text).expanduser()
    if not candidate.is_absolute():
        candidate = workspace_root / candidate
    try:
        resolved = candidate.resolve()
    except OSError:
        return None
    return resolved if resolved.is_dir() else None


def _find_referenced_workspace_dir(text: str, workspace_context: dict[str, Any]) -> str:
    compact_text = re.sub(r"\s+", "", text.lower())
    directories = workspace_context.get("directories")
    if not isinstance(directories, list):
        return ""
    for item in directories:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "")
        path = str(item.get("path") or "")
        supported_count = _safe_positive_int(item.get("supported_file_count")) or 0
        if supported_count <= 0:
            continue
        if name and re.sub(r"\s+", "", name.lower()) in compact_text:
            return path
        if path and re.sub(r"\s+", "", path.lower()) in compact_text:
            return path
    return ""


def _runner_from_text(text: str) -> str:
    lowered = text.lower()
    if "precise" in lowered or "精准" in text or "精确" in text or "高精度" in text:
        return "precise-api"
    if "agent api" in lowered or "轻量" in text:
        return "agent-api"
    if "cli" in lowered or "本地 mineru" in lowered or "本地mineru" in lowered:
        return "cli"
    return "auto"


def _batch_primary_runner(runner: str) -> Any:
    normalized = runner if runner in RUNNER_CHOICES else "auto"
    if normalized == "agent-api":
        return MinerUAgentAPIRunner()
    if normalized == "precise-api":
        return MinerUPreciseAPIRunner()
    return MinerURunner()


def _format_page_range(start_page: int | None, end_page: int | None) -> str:
    if start_page is not None and end_page is not None:
        return f"{start_page}-{end_page}"
    if start_page is not None:
        return str(start_page)
    if end_page is not None:
        return str(end_page)
    return ""


def _render_directory_listing(path: Path, *, limit: int = 60) -> str:
    try:
        entries = sorted(path.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower()))
    except OSError as exc:
        return f"无法读取当前目录 `{path}`: {exc}"
    lines = [f"当前目录: `{path}`", "", "| 类型 | 名称 | 大小 |", "|---|---|---:|"]
    for item in entries[:limit]:
        kind = "dir" if item.is_dir() else "file"
        size = "-" if item.is_dir() else _format_size(item.stat().st_size)
        suffix = "/" if item.is_dir() else ""
        lines.append(f"| {kind} | `{item.name}{suffix}` | {size} |")
    if len(entries) > limit:
        lines.append(f"| ... | 还有 {len(entries) - limit} 项未显示 | |")
    return "\n".join(lines)


def _format_size(size: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024


def render_plan(command: ChatCommand) -> str:
    return "\n".join(
        [
            "",
            "Planned document workflow:",
            f"  input:  {command.input_path}",
            f"  task:   {command.task}",
            f"  runner: {command.runner}",
            f"  profile/backend/method/lang: {command.profile}/{command.backend}/{command.method}/{command.lang}",
            f"  llm:    {command.llm} ({command.llm_model})",
            f"  out:    {command.output_root}",
            f"  why:    {command.rationale or 'natural-language plan'}",
            "",
        ]
    )


def _execute_or_preview(
    command: ChatCommand,
    *,
    dry_run: bool,
    print_func: Callable[[str], None],
    execution_mode: str = "live",
    provider: str = "deepseek",
    max_turns: int = DEFAULT_MAX_TURNS,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    timeout: float = DEFAULT_TIMEOUT,
    mineru_executable: str | None = None,
) -> None:
    if dry_run:
        print_func("Dry run. No document was parsed.")
        print_func(json.dumps(command.to_jsonable(), ensure_ascii=False, indent=2))
        return
    input_path = Path(command.input_path).expanduser()
    if not input_path.exists():
        print_func(f"Input file does not exist: {input_path}")
        return
    if execution_mode == "live":
        from .mineru_client import MinerURunner

        print_func("Running live tool-calling workflow...")
        trace = run_live_agent(
            input_file=input_path,
            output_root=Path(command.output_root),
            task=command.task,
            provider=provider,
            model=command.llm_model,
            max_turns=max_turns,
            max_tokens=max_tokens,
            timeout=timeout,
            mineru_runner=MinerURunner(executable=mineru_executable) if mineru_executable else None,
            default_pdf_parser=command.runner,
        )
        result = live_trace_to_jsonable(trace, display_paths=True)
        print_func(
            "\n".join(
                [
                    "Completed live Agent workflow.",
                    f"  run_id: {result.get('run_id')}",
                    f"  status: {result.get('status')}",
                    f"  tools: {', '.join(result.get('tool_sequence') or [])}",
                    f"  answer: {result.get('final_answer') or ''}",
                    f"  summary: {result.get('summary_path')}",
                    f"  trace: {result.get('trace_path')}",
                ]
            )
        )
        return

    from .cli import _build_fallback_runner, _build_llm_client, _build_runner

    args = _namespace_from_command(command)
    agent = MinerUDataAgent(
        _build_runner(args),
        llm_client=_build_llm_client(args),
        fallback_mineru_runner=_build_fallback_runner(args),
        requested_runner=command.runner,
        auto_runner=command.runner == "auto",
    )
    print_func("Running workflow...")
    result = agent.run(input_path, Path(command.output_root), **command.to_run_kwargs())
    print_func(
        "\n".join(
            [
                "Completed.",
                f"  run_id: {result.run_id}",
                f"  quality: {result.quality.get('status')} ({result.quality.get('score')}/100)",
                f"  summary: {result.summary_path}",
                f"  trace: {result.trace_path}",
                f"  skill: {result.skill_package.get('files', {}).get('skill', '')}",
            ]
        )
    )


def _namespace_from_command(command: ChatCommand) -> Any:
    class Args:
        pass

    args = Args()
    args.runner = command.runner
    args.mineru_executable = None
    args.fallback_mineru_executable = None
    args.cli_fallback_on_no_page_provenance = True
    args.api_timeout = 300
    args.api_poll_interval = 3.0
    args.api_max_retries = 2
    args.llm = command.llm
    args.llm_model = command.llm_model
    args.llm_base_url = None
    args.llm_timeout = 60.0
    args.llm_max_preview_chars = 4000
    return args


def _heuristic_command(text: str, *, output_root: Path, model: str) -> ChatCommand:
    path = _extract_existing_path(text)
    lowered = text.lower()
    runner = "auto"
    if "precise" in lowered or "精准" in text or "vlm" in lowered:
        runner = "precise-api"
    elif "agent api" in lowered or "轻量" in text:
        runner = "agent-api"
    elif "cli" in lowered or "本地 mineru" in text:
        runner = "cli"
    profile = "auto"
    if any(item in lowered for item in ["financial", "finance", "table", "total"]) or any(item in text for item in ["财报", "财务", "合计", "表格"]):
        profile = "financial_report"
    elif any(item in lowered for item in ["contract", "standard"]) or any(item in text for item in ["合同", "标准", "条款"]):
        profile = "standard_or_contract"
    elif any(item in lowered for item in ["workflow", "diagram", "flow"]) or any(item in text for item in ["流程", "图"]):
        profile = "workflow_or_diagram"
    backend = "vlm-transformers" if runner == "precise-api" and profile in {"financial_report", "workflow_or_diagram"} else "pipeline"
    return ChatCommand(
        action="run" if path else "clarify",
        input_path=path,
        task=_task_without_path(text, path) or text,
        output_root=str(output_root),
        profile=profile,
        runner=runner,
        backend=backend,
        method="auto",
        lang="ch",
        llm="deepseek",
        llm_model=model,
        rationale="local heuristic from file path and task keywords",
    )


def _deepseek_plan(text: str, *, fallback: ChatCommand, model: str) -> ChatCommand:
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You convert a user's natural-language document request into a MinerU Data Agent command. "
                    "Return strict JSON only."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "user_text": text,
                        "fallback": fallback.to_jsonable(),
                        "allowed": {
                            "action": ["run", "clarify"],
                            "runner": sorted(RUNNER_CHOICES),
                            "profile": sorted(PROFILE_CHOICES | {"auto"}),
                            "backend": sorted(BACKEND_CHOICES),
                            "method": sorted(METHOD_CHOICES),
                            "lang": sorted(LANG_CHOICES),
                        },
                        "instruction": (
                            "Choose action=run only when an input_path is present. Keep paths exactly as written. "
                            "Prefer runner=auto unless the user explicitly requests precise-api, agent-api, or cli. "
                            "Use deepseek-v4-flash unless the user asks otherwise."
                        ),
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        "temperature": 0.0,
    }
    headers = {"Authorization": f"Bearer {os.environ['DEEPSEEK_API_KEY']}", "Content-Type": "application/json"}
    with httpx.Client(timeout=30.0) as client:
        response = client.post(_chat_completions_url(DEFAULT_DEEPSEEK_BASE_URL), headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
    content = data["choices"][0]["message"].get("content") or "{}"
    parsed = _parse_json_object(content)
    merged = {**fallback.to_jsonable(), **{key: value for key, value in parsed.items() if value not in (None, "")}}
    return _normalize_chat_command(merged, fallback=fallback, model=model)


def _normalize_chat_command(data: dict[str, Any], *, fallback: ChatCommand, model: str) -> ChatCommand:
    action = str(data.get("action") or fallback.action).strip().lower()
    if action not in {"run", "clarify"}:
        action = fallback.action
    runner = _choice(data.get("runner"), RUNNER_CHOICES, fallback.runner)
    profile = _choice(data.get("profile"), PROFILE_CHOICES | {"auto"}, fallback.profile)
    backend = _choice(data.get("backend"), BACKEND_CHOICES, fallback.backend)
    method = _choice(data.get("method"), METHOD_CHOICES, fallback.method)
    lang = _choice(data.get("lang"), LANG_CHOICES, fallback.lang)
    return ChatCommand(
        action=action,
        task=str(data.get("task") or fallback.task),
        input_path=str(data.get("input_path") or fallback.input_path),
        output_root=str(data.get("output_root") or fallback.output_root),
        profile=profile,
        runner=runner,
        backend=backend,
        method=method,
        lang=lang,
        llm="deepseek",
        llm_model=str(data.get("llm_model") or model),
        strict_page_provenance=bool(data.get("strict_page_provenance", fallback.strict_page_provenance)),
        rationale=str(data.get("rationale") or "DeepSeek natural-language planner"),
    )


def _choice(value: Any, allowed: set[str], default: str) -> str:
    text = str(value or "").strip().lower()
    return text if text in allowed else default


def _contains_any(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)


def _extract_url(text: str) -> str:
    match = re.search(r"https?://[^\s)）]+", text, flags=re.I)
    if not match:
        return ""
    return match.group(0).rstrip(".,;，。；、)")


def _is_document_workflow_request(
    text: str,
    *,
    current_doc: str | None,
    path: str,
    url: str,
) -> bool:
    lowered = text.lower().strip()
    compact = re.sub(r"\s+", "", lowered)
    if not compact:
        return False

    casual = {
        "hi",
        "hello",
        "hey",
        "你好",
        "您好",
        "在吗",
        "谢谢",
        "thanks",
        "thankyou",
        "早上好",
        "下午好",
        "晚上好",
    }
    if compact in casual:
        return False

    strong_verbs = [
        "parse",
        "extract",
        "ocr",
        "mineru",
        "解析",
        "提取",
        "抽取",
        "识别",
        "结构化",
    ]
    workflow_verbs = strong_verbs + [
        "analyze",
        "analyse",
        "summarize",
        "summary",
        "convert",
        "process",
        "validate",
        "check",
        "audit",
        "retrieve",
        "load",
        "split",
        "chunk",
        "vlm",
        "分析",
        "总结",
        "摘要",
        "整理",
        "处理",
        "转换",
        "清洗",
        "校验",
        "检查",
        "审计",
        "恢复",
        "导出",
        "检索",
        "查询",
        "加载",
        "拆分",
        "切块",
        "运行",
    ]
    document_nouns = [
        "pdf",
        "html",
        "htm",
        "docx",
        "pptx",
        "png",
        "jpg",
        "jpeg",
        "url",
        "webpage",
        "document",
        "file",
        "table",
        "corpus",
        "skill",
        "trace",
        "文档",
        "文件",
        "网页",
        "资料",
        "史料",
        "财报",
        "合同",
        "表格",
        "图片",
        "扫描",
        "影印",
        "数据",
        "证据",
        "字段",
        "页面",
    ]

    has_source = bool(path or url)
    has_current = bool(current_doc)
    has_strong_verb = _contains_any(lowered, strong_verbs) or _contains_any(compact, strong_verbs)
    has_workflow_verb = _contains_any(lowered, workflow_verbs) or _contains_any(compact, workflow_verbs)
    has_document_noun = _contains_any(lowered, document_nouns) or _contains_any(compact, document_nouns)

    if has_source:
        return True
    if has_strong_verb:
        return True
    if has_current and has_workflow_verb:
        return True
    return has_workflow_verb and has_document_noun


def _chatbot_reply(
    text: str,
    *,
    provider: str,
    model: str,
    output_root: Path,
    current_doc: str | None,
    timeout: float,
    history: list[dict[str, str]],
    workspace_context: dict[str, Any] | None = None,
) -> str:
    api_key = os.getenv("DEEPSEEK_API_KEY") if provider == "deepseek" else None
    fallback = (
        "我在。现在是普通聊天模式；只有当你让我解析、提取、分析文档或数据时，我才会启动工具工作流。"
        f" 当前模型配置是 {provider}/{model}。"
    )
    if not api_key:
        return fallback

    messages = [
        {
            "role": "system",
            "content": (
                "You are the conversational front desk of MinerU Data Agent Harness. "
                "Answer in concise Chinese by default. Use the provided Harness context for identity, model, "
                "workspace, current document, and capability questions. Do not call tools and do not claim a document was parsed. "
                "When answering identity or capability questions, describe MinerU Data Agent as a general-purpose "
                "data/document processing Agent Harness. Do not specialize the identity based on current workspace filenames. "
                "Mention workspace contents only if the user explicitly asks about current files, directories, or available documents. "
                "If the user asks for document parsing, extraction, OCR, data cleaning, validation, or document analysis, "
                "tell them to provide a file path or URL so the Harness can run the workflow."
            ),
        },
        {
            "role": "system",
            "content": json.dumps(
                {
                    "provider": provider,
                    "model": model,
                    "output_root": str(output_root),
                    "current_document": current_doc or "",
                    "workspace_context": workspace_context or {},
                    "local_commands": ["ls", "dir", "pwd", "/help", "/status", "/exit"],
                    "roles": {
                        "DeepSeek": "natural-language understanding, planning, and conversational answers",
                        "MinerU": "external document parsing tool",
                        "Harness": "tool routing, quality checks, recovery, trace, and delivery artifacts",
                    },
                },
                ensure_ascii=False,
            ),
        },
    ]
    messages.extend(history[-8:])
    messages.append({"role": "user", "content": text})
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 512,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(_chat_completions_url(DEFAULT_DEEPSEEK_BASE_URL), headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        content = str(data["choices"][0]["message"].get("content") or "").strip()
        return content or fallback
    except Exception as exc:  # noqa: BLE001 - keep chat usable when provider is unavailable
        error = str(exc).replace(api_key, "***")[-180:]
        return f"{fallback}\n普通聊天调用 DeepSeek 暂时失败: {error}"


def _extract_existing_path(text: str, *, workspace_root: Path | None = None, allow_directories: bool = False) -> str:
    candidates = re.findall(
        r'"([^"]+)"|`([^`]+)`|([^\s]+(?:\.pdf|\.html|\.htm|\.docx|\.pptx|\.png|\.jpg|\.jpeg))',
        text,
        flags=re.I,
    )
    for groups in candidates:
        raw = next((item for item in groups if item), "")
        path = _resolve_candidate_path(raw, workspace_root=workspace_root)
        if path.exists():
            if path.is_file() or (allow_directories and path.is_dir()):
                return str(path)
    if allow_directories and workspace_root is not None:
        compact = re.sub(r"\s+", "", text.lower())
        try:
            for item in sorted(workspace_root.iterdir(), key=lambda path: len(path.name), reverse=True):
                if not item.is_dir():
                    continue
                name = re.sub(r"\s+", "", item.name.lower())
                if name and name in compact:
                    return str(item.resolve())
        except OSError:
            return ""
    return ""


def _resolve_candidate_path(raw: str, *, workspace_root: Path | None = None) -> Path:
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute() and workspace_root is not None:
        candidate = workspace_root / candidate
    return candidate


def _task_without_path(text: str, path: str) -> str:
    if not path:
        return text.strip()
    return text.replace(path, "").strip(" ,，:：")


def _two_columns(left: list[str], right: list[str], *, width: int) -> str:
    gap = " | "
    left_width = max(28, width // 2 - 2)
    right_width = max(28, width - left_width - len(gap))
    rows = []
    for index in range(max(len(left), len(right))):
        left_item = left[index] if index < len(left) else ""
        right_item = right[index] if index < len(right) else ""
        rows.append(left_item[:left_width].ljust(left_width) + gap + right_item[:right_width])
    return "\n".join(rows)
