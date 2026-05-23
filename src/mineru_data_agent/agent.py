from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path
from typing import Any

from .extractors import build_extracted_view, extract_docx, extract_html, extract_pptx, read_content_list, read_markdown
from .retrieval_exporter import build_retrieval_export
from .logging_utils import TraceRecorder
from .mineru_client import MinerUParseError, MinerURunner
from .models import AgentResult, ParseArtifacts, ToolCall
from .planner import build_plan, infer_profile
from .validators import build_quality_report


HTML_SUFFIXES = {".html", ".htm"}
DOCX_SUFFIXES = {".docx"}
PPTX_SUFFIXES = {".pptx"}
NATIVE_SUFFIXES = HTML_SUFFIXES | DOCX_SUFFIXES | PPTX_SUFFIXES
PROFILE_CHOICES = {"financial_report", "standard_or_contract", "workflow_or_diagram", "low_quality_ocr", "general_document"}
RUNNER_CHOICES = {"cli", "agent-api", "native"}
BACKEND_CHOICES = {"pipeline", "vlm-transformers", "vlm-sglang-engine", "vlm-sglang-client"}
METHOD_CHOICES = {"auto", "ocr", "txt"}
LANG_CHOICES = {"ch", "en"}


class AgentRunError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        run_id: str,
        output_dir: Path,
        trace_path: Path,
        result_path: Path,
        summary_path: Path,
    ) -> None:
        super().__init__(message)
        self.run_id = run_id
        self.output_dir = str(output_dir)
        self.trace_path = str(trace_path)
        self.result_path = str(result_path)
        self.summary_path = str(summary_path)


class MinerUDataAgent:
    def __init__(self, mineru_runner: MinerURunner | None = None, llm_client: Any | None = None) -> None:
        self.mineru_runner = mineru_runner or MinerURunner()
        self.llm_client = llm_client

    def run(
        self,
        input_file: str | Path,
        output_root: str | Path,
        *,
        task: str,
        profile: str = "auto",
        backend: str = "pipeline",
        method: str = "auto",
        lang: str = "ch",
    ) -> AgentResult:
        input_path = Path(input_file).expanduser().resolve()
        if not input_path.exists():
            raise FileNotFoundError(f"Input file does not exist: {input_path}")

        run_id = uuid.uuid4().hex[:12]
        output_dir = Path(output_root).expanduser().resolve() / run_id
        output_dir.mkdir(parents=True, exist_ok=True)
        trace = TraceRecorder()
        result_path = output_dir / "result.json"
        summary_path = output_dir / "summary.md"
        trace_path = output_dir / "trace.json"
        suffix = input_path.suffix.lower()
        llm_preplan: dict[str, Any] = {"enabled": False}
        execution_control: dict[str, Any] = {}

        try:
            with trace.step("infer_task_profile", task=task, input_file=str(input_path)):
                resolved_profile = infer_profile(task, input_path.name) if profile == "auto" else profile
                plan = build_plan(task, resolved_profile)
            execution_control = _initial_execution_control(
                requested_profile=profile,
                resolved_profile=resolved_profile,
                backend=backend,
                method=method,
                lang=lang,
                suffix=suffix,
                runner_name=self.mineru_runner.__class__.__name__,
            )

            if self.llm_client:
                with trace.step(
                    "llm_pre_execution_planning",
                    requested_profile=profile,
                    inferred_profile=resolved_profile,
                    backend=backend,
                    method=method,
                    lang=lang,
                ) as pre_step:
                    llm_preplan, llm_pre_call = self.llm_client.plan_execution(
                        task=task,
                        input_metadata=_input_metadata(input_path),
                        inferred_profile=resolved_profile,
                        requested_profile=profile,
                        requested_backend=backend,
                        requested_method=method,
                        requested_lang=lang,
                        current_runner=_runner_kind(self.mineru_runner),
                    )
                    llm_preplan["enabled"] = True
                    trace.add_tool_call(llm_pre_call.__dict__)
                    resolved_profile, backend, method, lang, execution_control = _apply_llm_preplan(
                        preplan=llm_preplan,
                        requested_profile=profile,
                        initial_profile=resolved_profile,
                        backend=backend,
                        method=method,
                        lang=lang,
                        suffix=suffix,
                        runner_kind=_runner_kind(self.mineru_runner),
                        runner_name=self.mineru_runner.__class__.__name__,
                    )
                    plan = _merge_plan(build_plan(task, resolved_profile), llm_preplan.get("execution_plan", []))
                    pre_step.detail["execution_control"] = execution_control

            artifacts = ParseArtifacts()
            markdown = ""
            content_list: list[dict[str, Any]] = []

            if suffix in HTML_SUFFIXES:
                with trace.step("extract_html", input_file=str(input_path)):
                    markdown, content_list = extract_html(input_path)
                    artifacts = _write_native_parse_artifacts(output_dir, input_path, "html", markdown, content_list)
            elif suffix in DOCX_SUFFIXES:
                with trace.step("extract_docx", input_file=str(input_path)):
                    markdown, content_list = extract_docx(input_path)
                    artifacts = _write_native_parse_artifacts(output_dir, input_path, "office", markdown, content_list)
            elif suffix in PPTX_SUFFIXES:
                with trace.step("extract_pptx", input_file=str(input_path)):
                    markdown, content_list = extract_pptx(input_path)
                    artifacts = _write_native_parse_artifacts(output_dir, input_path, "office", markdown, content_list)
            else:
                with trace.step("mineru_parse", backend=backend, method=method, lang=lang):
                    try:
                        artifacts, call = self.mineru_runner.parse(
                            input_path,
                            output_dir / "mineru",
                            backend=backend,
                            method=method,
                            lang=lang,
                        )
                    except MinerUParseError as exc:
                        trace.add_tool_call(exc.tool_call.__dict__)
                        raise
                    trace.add_tool_call(call.__dict__)
                    markdown = read_markdown(artifacts.markdown_path)
                    content_list = read_content_list(artifacts.content_list_path)

            with trace.step("build_structured_view"):
                extracted = build_extracted_view(markdown, content_list)

            with trace.step("quality_validation", profile=resolved_profile):
                quality = build_quality_report(markdown, extracted, resolved_profile, task=task)

            recovery_attempts = [
                _attempt_summary(
                    name="initial",
                    quality=quality,
                    artifacts=artifacts,
                    backend=backend,
                    method=method,
                    selected=True,
                )
            ]
            selected_attempt = "initial"

            if _should_run_text_cleanup(quality):
                with trace.step("auto_recovery_text_cleanup", from_status=quality.get("status")):
                    recovered_markdown, recovered_content = _clean_text_artifacts(markdown, content_list)
                    recovered_extracted = build_extracted_view(recovered_markdown, recovered_content)
                    recovered_quality = build_quality_report(
                        recovered_markdown,
                        recovered_extracted,
                        resolved_profile,
                        task=task,
                    )
                    recovered_artifacts = _write_recovery_parse_artifacts(
                        output_dir,
                        input_path,
                        "text_cleanup",
                        recovered_markdown,
                        recovered_content,
                    )
                    recovery_attempts.append(
                        _attempt_summary(
                            name="text_cleanup",
                            quality=recovered_quality,
                            artifacts=recovered_artifacts,
                            backend=backend,
                            method=method,
                            selected=False,
                        )
                    )
                    if _is_better_quality(recovered_quality, quality):
                        markdown = recovered_markdown
                        content_list = recovered_content
                        extracted = recovered_extracted
                        quality = recovered_quality
                        artifacts = recovered_artifacts
                        selected_attempt = "text_cleanup"

            if _should_retry_with_ocr(quality, suffix, method):
                with trace.step("auto_recovery_ocr_retry", backend=backend, from_method=method, retry_method="ocr") as retry_step:
                    try:
                        retry_artifacts, retry_call = self.mineru_runner.parse(
                            input_path,
                            output_dir / "mineru_retry_ocr",
                            backend=backend,
                            method="ocr",
                            lang=lang,
                        )
                    except Exception as exc:
                        _record_tool_call_from_exception(trace, exc)
                        retry_step.detail["recovery_error"] = repr(exc)
                        retry_step.detail["fallback_to_attempt"] = selected_attempt
                        recovery_attempts.append(
                            _failed_attempt_summary(
                                name="ocr_retry",
                                backend=backend,
                                method="ocr",
                                error=repr(exc),
                            )
                        )
                    else:
                        trace.add_tool_call(retry_call.__dict__)
                        retry_markdown = read_markdown(retry_artifacts.markdown_path)
                        retry_content = read_content_list(retry_artifacts.content_list_path)
                        retry_extracted = build_extracted_view(retry_markdown, retry_content)
                        retry_quality = build_quality_report(retry_markdown, retry_extracted, resolved_profile, task=task)
                        recovery_attempts.append(
                            _attempt_summary(
                                name="ocr_retry",
                                quality=retry_quality,
                                artifacts=retry_artifacts,
                                backend=backend,
                                method="ocr",
                                selected=False,
                            )
                        )
                        if _is_better_quality(retry_quality, quality):
                            markdown = retry_markdown
                            content_list = retry_content
                            extracted = retry_extracted
                            quality = retry_quality
                            artifacts = retry_artifacts
                            selected_attempt = "ocr_retry"

            _mark_selected_attempt(recovery_attempts, selected_attempt)

            with trace.step("recovery_decision", quality_status=quality.get("status"), selected_attempt=selected_attempt):
                recovery_decision = _build_recovery_decision(
                    quality,
                    extracted,
                    resolved_profile,
                    suffix,
                    attempts=recovery_attempts,
                    selected_attempt=selected_attempt,
                )

            with trace.step("build_retrieval_export"):
                retrieval_export = build_retrieval_export(
                    markdown=markdown,
                    content_list=content_list,
                    output_dir=output_dir / "retrieval",
                    doc_id=input_path.stem,
                    source_file=input_path,
                )

            llm_analysis: dict[str, Any] = {"enabled": False}
            if self.llm_client:
                llm_analysis = {
                    "enabled": True,
                    "pre_execution_plan": llm_preplan,
                    "execution_control": execution_control,
                }
                with trace.step("llm_agent_analysis"):
                    post_llm_analysis, llm_call = self.llm_client.analyze(
                        task=task,
                        profile=resolved_profile,
                        plan=plan,
                        extracted=extracted,
                        quality=quality,
                    )
                    llm_analysis["post_parse_analysis"] = post_llm_analysis
                    llm_analysis.update(post_llm_analysis)
                    llm_analysis["enabled"] = True
                    trace.add_tool_call(llm_call.__dict__)

            result = AgentResult(
                run_id=run_id,
                task=task,
                profile=resolved_profile,
                input_file=str(input_path),
                output_dir=str(output_dir),
                plan=plan,
                execution_control=execution_control,
                extracted=extracted,
                quality=quality,
                recovery_decision=recovery_decision,
                retrieval_export=retrieval_export,
                llm_analysis=llm_analysis,
                artifacts=artifacts.to_jsonable(),
                trace_path=str(trace_path),
                summary_path=str(summary_path),
            )
            result_path.write_text(json.dumps(result.to_jsonable(), ensure_ascii=False, indent=2), encoding="utf-8")
            summary_path.write_text(_build_summary(result), encoding="utf-8")
            trace.write(
                trace_path,
                {
                    "run_id": run_id,
                    "task": task,
                    "profile": resolved_profile,
                    "status": "completed",
                    "result_path": str(result_path),
                    "summary_path": str(summary_path),
                },
            )
            return result
        except Exception as exc:
            trace.write(
                trace_path,
                {
                    "run_id": run_id,
                    "task": task,
                    "profile": profile,
                    "status": "failed",
                    "input_file": str(input_path),
                    "result_path": str(result_path),
                    "summary_path": str(summary_path),
                    "error": repr(exc),
                },
            )
            raise AgentRunError(
                f"Agent run failed: {exc}",
                run_id=run_id,
                output_dir=output_dir,
                trace_path=trace_path,
                result_path=result_path,
                summary_path=summary_path,
            ) from exc


def _input_metadata(input_path: Path) -> dict[str, Any]:
    stat = input_path.stat()
    return {
        "filename": input_path.name,
        "suffix": input_path.suffix.lower(),
        "size_bytes": stat.st_size,
        "is_native_extractor_input": input_path.suffix.lower() in NATIVE_SUFFIXES,
    }


def _runner_kind(runner: Any) -> str:
    name = runner.__class__.__name__.lower()
    if "agentapi" in name or "agent_api" in name or "agent" in name and "api" in name:
        return "agent-api"
    return "cli"


def _initial_execution_control(
    *,
    requested_profile: str,
    resolved_profile: str,
    backend: str,
    method: str,
    lang: str,
    suffix: str,
    runner_name: str,
) -> dict[str, Any]:
    runner_kind = "native" if suffix in NATIVE_SUFFIXES else ("agent-api" if "AgentAPI" in runner_name else "cli")
    return {
        "llm_preplan_enabled": False,
        "requested": {
            "profile": requested_profile,
            "backend": backend,
            "method": method,
            "lang": lang,
        },
        "initial": {
            "profile": resolved_profile,
            "backend": backend,
            "method": method,
            "lang": lang,
            "runner": runner_kind,
        },
        "resolved": {
            "profile": resolved_profile,
            "backend": backend,
            "method": method,
            "lang": lang,
            "runner": runner_kind,
        },
        "runner_class": runner_name,
        "applied": [],
        "ignored": [],
    }


def _apply_llm_preplan(
    *,
    preplan: dict[str, Any],
    requested_profile: str,
    initial_profile: str,
    backend: str,
    method: str,
    lang: str,
    suffix: str,
    runner_kind: str,
    runner_name: str,
) -> tuple[str, str, str, str, dict[str, Any]]:
    resolved_profile = initial_profile
    resolved_backend = backend
    resolved_method = method
    resolved_lang = lang
    control = _initial_execution_control(
        requested_profile=requested_profile,
        resolved_profile=initial_profile,
        backend=backend,
        method=method,
        lang=lang,
        suffix=suffix,
        runner_name=runner_name,
    )
    control["llm_preplan_enabled"] = True
    control["llm_preplan_status"] = preplan.get("status")
    control["llm_recommendation"] = {
        "profile": preplan.get("recommended_profile"),
        "runner": preplan.get("recommended_runner"),
        "backend": preplan.get("recommended_backend"),
        "method": preplan.get("recommended_method"),
        "lang": preplan.get("recommended_lang"),
        "confidence": preplan.get("confidence"),
    }
    if preplan.get("status") != "completed":
        control["ignored"].append({"field": "*", "reason": "llm_preplan_failed_or_unavailable"})
        return resolved_profile, resolved_backend, resolved_method, resolved_lang, control

    requested_runner = _safe_choice(preplan.get("recommended_runner"), RUNNER_CHOICES)
    if requested_runner and requested_runner != runner_kind and suffix not in NATIVE_SUFFIXES:
        control["ignored"].append(
            {
                "field": "runner",
                "recommended": requested_runner,
                "current": runner_kind,
                "reason": "runner is fixed by the constructed runner; choose --runner before execution",
            }
        )

    recommended_profile = _safe_choice(preplan.get("recommended_profile"), PROFILE_CHOICES)
    if recommended_profile and requested_profile == "auto" and recommended_profile != resolved_profile:
        control["applied"].append(
            {"field": "profile", "from": resolved_profile, "to": recommended_profile, "reason": "llm_preplan"}
        )
        resolved_profile = recommended_profile
    elif recommended_profile and requested_profile != "auto" and recommended_profile != resolved_profile:
        control["ignored"].append(
            {
                "field": "profile",
                "recommended": recommended_profile,
                "current": resolved_profile,
                "reason": "explicit profile was supplied",
            }
        )

    if suffix in NATIVE_SUFFIXES:
        for field in ["backend", "method"]:
            value = preplan.get(f"recommended_{field}")
            if value:
                control["ignored"].append(
                    {
                        "field": field,
                        "recommended": value,
                        "current": backend if field == "backend" else method,
                        "reason": "native HTML/DOCX/PPTX extractor branch does not call MinerU parser",
                    }
                )
    else:
        recommended_backend = _safe_choice(preplan.get("recommended_backend"), BACKEND_CHOICES)
        if recommended_backend and backend == "pipeline" and recommended_backend != resolved_backend:
            control["applied"].append(
                {"field": "backend", "from": resolved_backend, "to": recommended_backend, "reason": "llm_preplan"}
            )
            resolved_backend = recommended_backend
        elif recommended_backend and backend != "pipeline" and recommended_backend != resolved_backend:
            control["ignored"].append(
                {
                    "field": "backend",
                    "recommended": recommended_backend,
                    "current": resolved_backend,
                    "reason": "explicit backend was supplied",
                }
            )

        recommended_method = _safe_choice(preplan.get("recommended_method"), METHOD_CHOICES)
        if recommended_method and method == "auto" and recommended_method != resolved_method:
            control["applied"].append(
                {"field": "method", "from": resolved_method, "to": recommended_method, "reason": "llm_preplan"}
            )
            resolved_method = recommended_method
        elif recommended_method and method != "auto" and recommended_method != resolved_method:
            control["ignored"].append(
                {
                    "field": "method",
                    "recommended": recommended_method,
                    "current": resolved_method,
                    "reason": "explicit method was supplied",
                }
            )

    recommended_lang = _safe_choice(preplan.get("recommended_lang"), LANG_CHOICES)
    if recommended_lang and lang == "ch" and recommended_lang != resolved_lang:
        control["applied"].append(
            {"field": "lang", "from": resolved_lang, "to": recommended_lang, "reason": "llm_preplan"}
        )
        resolved_lang = recommended_lang
    elif recommended_lang and lang != "ch" and recommended_lang != resolved_lang:
        control["ignored"].append(
            {
                "field": "lang",
                "recommended": recommended_lang,
                "current": resolved_lang,
                "reason": "explicit language was supplied",
            }
        )

    control["resolved"] = {
        "profile": resolved_profile,
        "backend": resolved_backend,
        "method": resolved_method,
        "lang": resolved_lang,
        "runner": "native" if suffix in NATIVE_SUFFIXES else runner_kind,
    }
    return resolved_profile, resolved_backend, resolved_method, resolved_lang, control


def _safe_choice(value: Any, allowed: set[str]) -> str:
    text = str(value or "").strip().lower()
    return text if text in allowed else ""


def _merge_plan(base_plan: list[str], llm_plan: Any) -> list[str]:
    merged = list(base_plan)
    if isinstance(llm_plan, list):
        for raw_step in llm_plan:
            step = str(raw_step).strip()
            if step and step not in merged:
                merged.append(f"LLM preplan: {step}")
    return merged


def _build_summary(result: AgentResult) -> str:
    summary = result.extracted.get("content_summary", {})
    issues = result.quality.get("issues", [])
    key_values = result.extracted.get("key_values", [])
    semantic = result.extracted.get("semantic_signals", {})
    top_pairs = key_values[:8] if isinstance(key_values, list) else []
    lines = [
        f"# MinerU Data Agent Run {result.run_id}",
        "",
        f"- Task: {result.task}",
        f"- Profile: {result.profile}",
        f"- Execution method: {result.execution_control.get('resolved', {}).get('method', 'unknown')}",
        f"- Execution backend: {result.execution_control.get('resolved', {}).get('backend', 'unknown')}",
        f"- LLM preplan applied changes: {len(result.execution_control.get('applied', []))}",
        f"- Input: `{result.input_file}`",
        f"- Quality: {result.quality.get('status')} ({result.quality.get('score')}/100)",
        f"- Content blocks: {summary.get('item_count', 0)}",
        f"- Pages with provenance: {summary.get('page_count', 0)}",
        f"- Provenance level: {summary.get('provenance_level', 'unknown')}",
        f"- Sections: {len(result.extracted.get('sections', []))}",
        f"- Tables: {len(result.extracted.get('tables', []))}",
        f"- Key-values: {len(key_values)}",
        f"- Numeric facts: {len(result.extracted.get('numeric_facts', []))}",
        f"- Dates detected: {len(semantic.get('dates', []))}",
        f"- Recommendation signals: {len(semantic.get('recommendations', []))}",
        f"- Anomaly signals: {len(semantic.get('anomaly_lines', []))}",
        f"- Retrieval chunks: {result.retrieval_export.get('stats', {}).get('total_chunks', 0)}",
        f"- Recovery decision: {result.recovery_decision.get('decision', 'unknown')}",
        f"- Recovery selected attempt: {result.recovery_decision.get('selected_attempt', 'initial')}",
        f"- Recovery attempts: {len(result.recovery_decision.get('attempts', []))}",
        f"- LLM analysis: {_llm_status_label(result.llm_analysis)}",
        "",
        "## Plan",
    ]
    lines.extend([f"{index}. {step}" for index, step in enumerate(result.plan, start=1)])
    if result.llm_analysis.get("enabled"):
        llm_plan = result.llm_analysis.get("execution_plan", [])
        lines.extend(["", "## LLM Agent Analysis", ""])
        preplan = result.llm_analysis.get("pre_execution_plan", {})
        if isinstance(preplan, dict):
            lines.append(
                "Pre-execution control: "
                f"profile={preplan.get('recommended_profile', '')}, "
                f"runner={preplan.get('recommended_runner', '')}, "
                f"method={preplan.get('recommended_method', '')}, "
                f"backend={preplan.get('recommended_backend', '')}"
            )
            applied = result.execution_control.get("applied", [])
            if applied:
                lines.append("Applied LLM control changes:")
                for item in applied[:8]:
                    if isinstance(item, dict):
                        lines.append(f"- {item.get('field')}: {item.get('from')} -> {item.get('to')}")
            lines.append("")
        understanding = result.llm_analysis.get("task_understanding")
        if understanding:
            lines.append(str(understanding))
            lines.append("")
        if isinstance(llm_plan, list) and llm_plan:
            lines.append("Suggested execution plan:")
            lines.extend([f"{index}. {step}" for index, step in enumerate(llm_plan[:12], start=1)])
    if top_pairs:
        lines.extend(["", "## Extracted Fields"])
        lines.extend([f"- {item.get('key')}: {item.get('value')}" for item in top_pairs])
    if semantic.get("recommendations"):
        lines.extend(["", "## Recommendation Evidence"])
        for item in semantic.get("recommendations", [])[:5]:
            lines.append(f"- {item.get('text')}")
    recovery_actions = result.recovery_decision.get("actions", [])
    if recovery_actions:
        lines.extend(["", "## Recovery Decision"])
        lines.append(f"- Decision: {result.recovery_decision.get('decision')}")
        lines.extend([f"- {action}" for action in recovery_actions])
        attempts = result.recovery_decision.get("attempts", [])
        if isinstance(attempts, list) and attempts:
            lines.append("")
            lines.append("Attempts:")
            for attempt in attempts:
                if isinstance(attempt, dict):
                    selected = "selected" if attempt.get("selected") else "not selected"
                    lines.append(
                        f"- {attempt.get('name')}: {attempt.get('quality_status')} "
                        f"({attempt.get('score')}/100), {selected}"
                    )
    lines.extend(["", "## Issues"])
    if issues:
        lines.extend([f"- [{item['level']}] {item['code']}: {item['message']}" for item in issues])
    else:
        lines.append("- No blocking issues detected.")
    lines.extend(["", "## Markdown Preview", "", result.extracted.get("markdown_preview", "")])
    return "\n".join(lines).strip() + "\n"


def _llm_status_label(llm_analysis: dict[str, Any]) -> str:
    if not llm_analysis.get("enabled"):
        return "disabled"
    return f"enabled/{llm_analysis.get('status', 'completed')}"


def _write_native_parse_artifacts(
    output_dir: Path,
    input_path: Path,
    dirname: str,
    markdown: str,
    content_list: list[dict[str, Any]],
) -> ParseArtifacts:
    native_dir = output_dir / dirname
    native_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(input_path, native_dir / input_path.name)
    md_path = native_dir / f"{input_path.stem}.md"
    content_path = native_dir / f"{input_path.stem}_content_list.json"
    md_path.write_text(markdown, encoding="utf-8")
    content_path.write_text(json.dumps(content_list, ensure_ascii=False, indent=2), encoding="utf-8")
    return ParseArtifacts(markdown_path=md_path, content_list_path=content_path)


def _write_recovery_parse_artifacts(
    output_dir: Path,
    input_path: Path,
    recovery_name: str,
    markdown: str,
    content_list: list[dict[str, Any]],
) -> ParseArtifacts:
    recovery_dir = output_dir / "recovery" / recovery_name
    recovery_dir.mkdir(parents=True, exist_ok=True)
    md_path = recovery_dir / f"{input_path.stem}.md"
    content_path = recovery_dir / f"{input_path.stem}_content_list.json"
    md_path.write_text(markdown, encoding="utf-8")
    content_path.write_text(json.dumps(content_list, ensure_ascii=False, indent=2), encoding="utf-8")
    return ParseArtifacts(markdown_path=md_path, content_list_path=content_path)


def _build_recovery_decision(
    quality: dict[str, Any],
    extracted: dict[str, Any],
    profile: str,
    suffix: str,
    *,
    attempts: list[dict[str, Any]] | None = None,
    selected_attempt: str = "initial",
) -> dict[str, Any]:
    issues = quality.get("issues", [])
    issue_codes = [str(issue.get("code")) for issue in issues if isinstance(issue, dict)]
    attempts = attempts or []
    initial_attempt = attempts[0] if attempts else {}
    initial_issue_codes = initial_attempt.get("issue_codes", [])
    executed = len(attempts) > 1
    actions: list[str] = []
    decision = "accept"
    if quality.get("status") == "needs_review":
        decision = "retry_or_manual_review"
    elif quality.get("status") == "pass_with_warnings":
        decision = "accept_with_review_notes"
    if selected_attempt != "initial" and decision == "accept":
        decision = "recovered_accept"
    elif selected_attempt != "initial" and decision == "accept_with_review_notes":
        decision = "recovered_with_review_notes"

    if executed:
        actions.append(
            f"Executed {len(attempts) - 1} automatic recovery attempt(s); selected `{selected_attempt}`."
        )
    failed_attempts = [
        str(attempt.get("name"))
        for attempt in attempts
        if isinstance(attempt, dict) and attempt.get("quality_status") == "failed"
    ]
    if failed_attempts:
        actions.append(f"Recovery attempt(s) failed but were kept in the audit trail: {', '.join(failed_attempts)}.")

    if any(code in issue_codes for code in ["empty_markdown", "no_content_blocks", "short_text"]):
        decision = "retry_or_manual_review"
        actions.append("Retry with OCR/VLM-capable parsing or inspect the source file quality.")
    if "no_page_provenance" in issue_codes:
        actions.append("Use local MinerU CLI when page-level provenance is required.")
    if "numeric_total_mismatch" in issue_codes:
        decision = "manual_numeric_review"
        actions.append("Route total/subtotal mismatches to numeric review before downstream use.")
    if suffix in {".docx", ".pptx", ".html", ".htm"}:
        actions.append("Native extractor result has document/slide-level provenance; use PDF/MinerU path for page-layout audit.")
    if profile == "financial_report" and not extracted.get("tables"):
        actions.append("If this is a financial document, rerun with a parser path that preserves HTML/Markdown tables.")
    if initial_issue_codes and selected_attempt != "initial":
        actions.append(f"Initial quality issues were preserved for audit: {', '.join(map(str, initial_issue_codes))}.")
    if not actions:
        actions.append("No automatic retry required; keep artifacts and trace for audit.")
    return {
        "decision": decision,
        "actions": actions,
        "issue_codes": issue_codes,
        "initial_issue_codes": initial_issue_codes,
        "selected_attempt": selected_attempt,
        "executed": executed,
        "attempts": attempts,
    }


def _attempt_summary(
    *,
    name: str,
    quality: dict[str, Any],
    artifacts: ParseArtifacts,
    backend: str,
    method: str,
    selected: bool,
) -> dict[str, Any]:
    return {
        "name": name,
        "backend": backend,
        "method": method,
        "quality_status": quality.get("status"),
        "score": quality.get("score"),
        "issue_codes": _issue_codes(quality),
        "selected": selected,
        "artifacts": artifacts.to_jsonable(),
    }


def _failed_attempt_summary(*, name: str, backend: str, method: str, error: str) -> dict[str, Any]:
    return {
        "name": name,
        "backend": backend,
        "method": method,
        "quality_status": "failed",
        "score": 0,
        "issue_codes": ["recovery_attempt_failed"],
        "selected": False,
        "error": error[-1000:],
        "artifacts": {},
    }


def _mark_selected_attempt(attempts: list[dict[str, Any]], selected_attempt: str) -> None:
    for attempt in attempts:
        attempt["selected"] = attempt.get("name") == selected_attempt


def _record_tool_call_from_exception(trace: TraceRecorder, exc: Exception) -> None:
    tool_call = getattr(exc, "tool_call", None)
    if isinstance(tool_call, ToolCall):
        trace.add_tool_call(tool_call.__dict__)


def _issue_codes(quality: dict[str, Any]) -> list[str]:
    issues = quality.get("issues", [])
    if not isinstance(issues, list):
        return []
    return [str(issue.get("code")) for issue in issues if isinstance(issue, dict)]


def _is_better_quality(candidate: dict[str, Any], current: dict[str, Any]) -> bool:
    return _quality_key(candidate) > _quality_key(current)


def _quality_key(quality: dict[str, Any]) -> tuple[int, int, int]:
    rank = {"needs_review": 0, "pass_with_warnings": 1, "pass": 2}
    issue_counts = quality.get("issue_counts", {})
    warning_count = int(issue_counts.get("warning", 0)) if isinstance(issue_counts, dict) else 0
    return (rank.get(str(quality.get("status")), -1), int(quality.get("score") or 0), -warning_count)


def _should_run_text_cleanup(quality: dict[str, Any]) -> bool:
    return "possible_mojibake" in _issue_codes(quality)


def _clean_text_artifacts(markdown: str, content_list: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    return _clean_text(markdown), [_clean_json_value(item) for item in content_list]


def _clean_json_value(value: Any) -> Any:
    if isinstance(value, str):
        return _clean_text(value)
    if isinstance(value, list):
        return [_clean_json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _clean_json_value(item) for key, item in value.items()}
    return value


def _clean_text(text: str) -> str:
    replacements = {
        "锟斤拷": "",
        "����": "",
        "�": "",
        "Ã": "",
        "Â": "",
    }
    cleaned = text
    for bad, good in replacements.items():
        cleaned = cleaned.replace(bad, good)
    return "\n".join(" ".join(line.split()) for line in cleaned.splitlines()).strip()


def _should_retry_with_ocr(quality: dict[str, Any], suffix: str, method: str) -> bool:
    if suffix in HTML_SUFFIXES | DOCX_SUFFIXES | PPTX_SUFFIXES:
        return False
    if method.lower() == "ocr":
        return False
    retry_codes = {
        "empty_markdown",
        "no_content_blocks",
        "short_text",
        "weak_page_provenance",
        "financial_signal_missing",
        "expected_date_missing",
        "expected_recommendation_missing",
        "expected_anomaly_signal_missing",
    }
    return quality.get("status") == "needs_review" or bool(set(_issue_codes(quality)) & retry_codes)
