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
from .planner import analyze_requirement, build_agent_action_plan, build_plan, build_quality_replan, build_task_result, infer_profile
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
    def __init__(
        self,
        mineru_runner: MinerURunner | None = None,
        llm_client: Any | None = None,
        fallback_mineru_runner: MinerURunner | None = None,
    ) -> None:
        self.mineru_runner = mineru_runner or MinerURunner()
        self.llm_client = llm_client
        self.fallback_mineru_runner = fallback_mineru_runner

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
        input_metadata = _input_metadata(input_path)

        try:
            with trace.step("infer_task_profile", task=task, input_file=str(input_path)) as profile_step:
                resolved_profile = infer_profile(task, input_path.name) if profile == "auto" else profile
                adaptive_decision = analyze_requirement(
                    task,
                    resolved_profile,
                    input_metadata=input_metadata,
                )
                plan = build_plan(task, resolved_profile, adaptive_decision)
                profile_step.detail["adaptive_decision"] = adaptive_decision.to_jsonable()
            execution_control = _initial_execution_control(
                requested_profile=profile,
                resolved_profile=resolved_profile,
                backend=backend,
                method=method,
                lang=lang,
                suffix=suffix,
                runner_name=self.mineru_runner.__class__.__name__,
                adaptive_decision=adaptive_decision.to_jsonable(),
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
                        input_metadata=input_metadata,
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
                    adaptive_decision = analyze_requirement(
                        task,
                        resolved_profile,
                        input_metadata=input_metadata,
                        llm_preplan=llm_preplan,
                    )
                    execution_control["adaptive_decision"] = adaptive_decision.to_jsonable()
                    execution_control["planning_rationale"]["adaptive_decision_rationale"] = adaptive_decision.rationale
                    plan = _merge_plan(
                        build_plan(task, resolved_profile, adaptive_decision),
                        llm_preplan.get("execution_plan", []),
                    )
                    pre_step.detail["execution_control"] = execution_control

            with trace.step("agent_task_decomposition") as agent_plan_step:
                agent_action_plan = build_agent_action_plan(
                    task,
                    resolved_profile,
                    adaptive_decision,
                    input_metadata=input_metadata,
                    runner=execution_control.get("resolved", {}).get("runner", _runner_kind(self.mineru_runner)),
                    backend=backend,
                    method=method,
                    lang=lang,
                    llm_enabled=self.llm_client is not None,
                )
                execution_control["agent_action_plan"] = agent_action_plan.to_jsonable()
                agent_plan_step.detail.update(
                    {
                        "subtask_count": len(agent_action_plan.subtasks),
                        "selected_tools": [
                            item["name"]
                            for item in agent_action_plan.tool_registry
                            if isinstance(item, dict) and item.get("selected")
                        ],
                        "replan_trigger_count": len(agent_action_plan.replan_triggers),
                    }
                )

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

            with trace.step("build_structured_view") as structured_step:
                extracted = _attach_task_result(build_extracted_view(markdown, content_list), adaptive_decision)
                structured_step.detail.update(_structured_trace_detail(extracted))
                structured_step.detail["task_result"] = _task_result_trace_detail(extracted)

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
                    recovered_extracted = _attach_task_result(
                        build_extracted_view(recovered_markdown, recovered_content),
                        adaptive_decision,
                    )
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
                        retry_extracted = _attach_task_result(
                            build_extracted_view(retry_markdown, retry_content),
                            adaptive_decision,
                        )
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

            if _should_fallback_to_cli(quality, suffix, self.mineru_runner, self.fallback_mineru_runner):
                with trace.step(
                    "auto_recovery_cli_fallback",
                    from_runner=_runner_kind(self.mineru_runner),
                    fallback_runner=_runner_kind(self.fallback_mineru_runner),
                    from_status=quality.get("status"),
                    issue_codes=_issue_codes(quality),
                ) as fallback_step:
                    try:
                        fallback_artifacts, fallback_call = self.fallback_mineru_runner.parse(
                            input_path,
                            output_dir / "mineru_fallback_cli",
                            backend=backend,
                            method=method,
                            lang=lang,
                        )
                    except Exception as exc:
                        _record_tool_call_from_exception(trace, exc)
                        fallback_step.detail["recovery_error"] = repr(exc)
                        fallback_step.detail["fallback_to_attempt"] = selected_attempt
                        recovery_attempts.append(
                            _failed_attempt_summary(
                                name="cli_fallback",
                                backend=backend,
                                method=method,
                                error=repr(exc),
                            )
                        )
                    else:
                        trace.add_tool_call(fallback_call.__dict__)
                        fallback_markdown = read_markdown(fallback_artifacts.markdown_path)
                        fallback_content = read_content_list(fallback_artifacts.content_list_path)
                        fallback_extracted = _attach_task_result(
                            build_extracted_view(fallback_markdown, fallback_content),
                            adaptive_decision,
                        )
                        fallback_quality = build_quality_report(
                            fallback_markdown,
                            fallback_extracted,
                            resolved_profile,
                            task=task,
                        )
                        recovery_attempts.append(
                            _attempt_summary(
                                name="cli_fallback",
                                quality=fallback_quality,
                                artifacts=fallback_artifacts,
                                backend=backend,
                                method=method,
                                selected=False,
                            )
                        )
                        fallback_step.detail["fallback_quality"] = {
                            "status": fallback_quality.get("status"),
                            "score": fallback_quality.get("score"),
                            "issue_codes": _issue_codes(fallback_quality),
                            "page_count": fallback_extracted.get("content_summary", {}).get("page_count"),
                            "provenance_level": fallback_extracted.get("content_summary", {}).get("provenance_level"),
                        }
                        if _is_better_quality(fallback_quality, quality):
                            markdown = fallback_markdown
                            content_list = fallback_content
                            extracted = fallback_extracted
                            quality = fallback_quality
                            artifacts = fallback_artifacts
                            selected_attempt = "cli_fallback"

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

            with trace.step("agent_replan_after_quality", selected_attempt=selected_attempt) as replan_step:
                replan_after_quality = build_quality_replan(
                    quality=quality,
                    attempts=recovery_attempts,
                    selected_attempt=selected_attempt,
                    decision=adaptive_decision,
                    action_plan=execution_control.get("agent_action_plan", {}),
                )
                execution_control["replan_after_quality"] = replan_after_quality
                replan_step.detail.update(replan_after_quality)

            with trace.step("build_retrieval_export") as retrieval_step:
                retrieval_export = build_retrieval_export(
                    markdown=markdown,
                    content_list=content_list,
                    output_dir=output_dir / "retrieval",
                    doc_id=input_path.stem,
                    source_file=input_path,
                )
                retrieval_step.detail.update(_retrieval_trace_detail(retrieval_export))

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
                    llm_analysis["usage_summary"] = _summarize_llm_usage(llm_preplan, post_llm_analysis)
                    trace.add_tool_call(llm_call.__dict__)
                with trace.step("llm_quality_decision") as llm_decision_step:
                    llm_quality_decision = _apply_llm_quality_decision(recovery_decision, post_llm_analysis)
                    llm_analysis["quality_decision"] = llm_quality_decision
                    llm_decision_step.detail.update(llm_quality_decision)

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


def _structured_trace_detail(extracted: dict[str, Any]) -> dict[str, Any]:
    summary = extracted.get("content_summary", {}) if isinstance(extracted, dict) else {}
    semantic = extracted.get("semantic_signals", {}) if isinstance(extracted, dict) else {}
    return {
        "item_count": int(summary.get("item_count") or 0),
        "page_count": int(summary.get("page_count") or 0),
        "provenance_level": summary.get("provenance_level", "unknown"),
        "source_counts": summary.get("source_counts", {}),
        "section_count": len(extracted.get("sections", [])),
        "table_count": len(extracted.get("tables", [])),
        "key_value_count": len(extracted.get("key_values", [])),
        "numeric_fact_count": len(extracted.get("numeric_facts", [])),
        "semantic_signal_counts": {
            "dates": len(semantic.get("dates", [])) if isinstance(semantic, dict) else 0,
            "recommendations": len(semantic.get("recommendations", [])) if isinstance(semantic, dict) else 0,
            "anomaly_lines": len(semantic.get("anomaly_lines", [])) if isinstance(semantic, dict) else 0,
        },
    }


def _attach_task_result(extracted: dict[str, Any], adaptive_decision: Any) -> dict[str, Any]:
    extracted["task_result"] = build_task_result(extracted, adaptive_decision)
    return extracted


def _task_result_trace_detail(extracted: dict[str, Any]) -> dict[str, Any]:
    task_result = extracted.get("task_result", {}) if isinstance(extracted, dict) else {}
    answers = task_result.get("answers", {}) if isinstance(task_result, dict) else {}
    return {
        "task_intents": task_result.get("task_intents", []),
        "target_schema_keys": list((task_result.get("target_schema") or {}).keys())[:30]
        if isinstance(task_result.get("target_schema"), dict)
        else [],
        "answer_keys": list(answers.keys()) if isinstance(answers, dict) else [],
    }


def _retrieval_trace_detail(retrieval_export: dict[str, Any]) -> dict[str, Any]:
    stats = retrieval_export.get("stats", {}) if isinstance(retrieval_export, dict) else {}
    return {
        "chunks_count": int(stats.get("total_chunks") or 0),
        "by_type": stats.get("by_type", {}),
        "pages": stats.get("pages", []),
        "chunks_path": retrieval_export.get("chunks_path"),
        "manifest_path": retrieval_export.get("manifest_path"),
        "quality_report_path": retrieval_export.get("quality_report_path"),
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
    adaptive_decision: dict[str, Any] | None = None,
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
        "planning_rationale": _planning_rationale(
            profile=resolved_profile,
            runner=runner_kind,
            backend=backend,
            method=method,
            lang=lang,
            suffix=suffix,
            source="rules",
        ),
        "adaptive_decision": adaptive_decision or {},
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
    control["planning_rationale"] = _planning_rationale(
        profile=resolved_profile,
        runner=control["resolved"]["runner"],
        backend=resolved_backend,
        method=resolved_method,
        lang=resolved_lang,
        suffix=suffix,
        source="llm_preplan+rules",
    )
    return resolved_profile, resolved_backend, resolved_method, resolved_lang, control


def _planning_rationale(
    *,
    profile: str,
    runner: str,
    backend: str,
    method: str,
    lang: str,
    suffix: str,
    source: str,
) -> dict[str, Any]:
    file_family = "native_office_or_html" if suffix in NATIVE_SUFFIXES else "pdf_or_image"
    profile_reasons = {
        "financial_report": "financial keywords or explicit profile require table and numeric consistency checks",
        "standard_or_contract": "standard/contract keywords or explicit profile require section and clause preservation",
        "workflow_or_diagram": "workflow/diagram keywords or explicit profile require procedural and figure evidence",
        "low_quality_ocr": "scan/OCR/low-quality keywords or explicit profile require OCR/noise checks and recovery readiness",
        "general_document": "no specialized profile signal was strong enough; use general structured extraction",
    }
    runner_reasons = {
        "native": "HTML/DOCX/PPTX inputs are handled by native extractors to preserve document structure without MinerU",
        "agent-api": "online MinerU Agent API is selected for CPU-friendly PDF parsing and quick reproducibility",
        "cli": "local MinerU CLI is selected when full artifacts and page-level provenance are required",
    }
    recovery_policy = [
        "text_cleanup if mojibake or encoding noise is detected",
        "ocr_retry for PDF/image results with blocking extraction or OCR-related quality issues",
        "cli_fallback when online API lacks page-level provenance and a local MinerU CLI is available",
        "manual_numeric_review when subtotal/total consistency checks fail",
    ]
    return {
        "source": source,
        "file_family": file_family,
        "profile_reason": profile_reasons.get(profile, profile_reasons["general_document"]),
        "runner_reason": runner_reasons.get(runner, "runner was supplied by caller or deployment configuration"),
        "backend_reason": f"backend={backend} is used for MinerU parsing when the selected runner calls MinerU",
        "method_reason": f"method={method} balances automatic parsing with OCR fallback when quality gates require it",
        "lang_reason": f"lang={lang} is passed to MinerU or recorded for native extraction audit",
        "recovery_policy": recovery_policy,
    }


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
    field_evidence = result.extracted.get("field_evidence", [])
    semantic = result.extracted.get("semantic_signals", {})
    task_result = result.extracted.get("task_result", {}) if isinstance(result.extracted.get("task_result"), dict) else {}
    top_pairs = key_values[:8] if isinstance(key_values, list) else []
    top_evidence = field_evidence[:5] if isinstance(field_evidence, list) else []
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
        f"- Field evidence records: {len(field_evidence) if isinstance(field_evidence, list) else 0}",
        f"- Numeric facts: {len(result.extracted.get('numeric_facts', []))}",
        f"- Dates detected: {len(semantic.get('dates', []))}",
        f"- Recommendation signals: {len(semantic.get('recommendations', []))}",
        f"- Anomaly signals: {len(semantic.get('anomaly_lines', []))}",
        f"- Retrieval chunks: {result.retrieval_export.get('stats', {}).get('total_chunks', 0)}",
        f"- Recovery decision: {result.recovery_decision.get('decision', 'unknown')}",
        f"- Recovery selected attempt: {result.recovery_decision.get('selected_attempt', 'initial')}",
        f"- Recovery attempts: {len(result.recovery_decision.get('attempts', []))}",
        f"- Task intents: {', '.join(task_result.get('task_intents', [])) if task_result.get('task_intents') else 'none'}",
        f"- LLM analysis: {_llm_status_label(result.llm_analysis)}",
        "",
        "## Plan",
    ]
    lines.extend([f"{index}. {step}" for index, step in enumerate(result.plan, start=1)])
    rationale = result.execution_control.get("planning_rationale", {})
    if isinstance(rationale, dict) and rationale:
        lines.extend(["", "## Planning Rationale"])
        for key in ["profile_reason", "runner_reason", "backend_reason", "method_reason", "lang_reason"]:
            if rationale.get(key):
                lines.append(f"- {rationale[key]}")
        policy = rationale.get("recovery_policy", [])
        if isinstance(policy, list) and policy:
            lines.append("- Recovery policy:")
            lines.extend([f"  - {item}" for item in policy[:6]])
    adaptive = result.execution_control.get("adaptive_decision", {})
    if isinstance(adaptive, dict) and adaptive:
        lines.extend(["", "## Adaptive Task Decision"])
        lines.append(f"- Intents: {', '.join(adaptive.get('task_intents', []))}")
        schema = adaptive.get("target_schema", {})
        if isinstance(schema, dict) and schema:
            lines.append(f"- Target schema keys: {', '.join(list(schema.keys())[:12])}")
        thresholds = adaptive.get("quality_thresholds", {})
        if isinstance(thresholds, dict) and thresholds:
            lines.append(f"- Quality thresholds: {json.dumps(thresholds, ensure_ascii=False)}")
        recovery = adaptive.get("recovery_strategy", [])
        if isinstance(recovery, list) and recovery:
            lines.append("- Recovery strategy:")
            for item in recovery[:6]:
                if isinstance(item, dict):
                    lines.append(f"  - {item.get('action')} on {item.get('trigger')} ({item.get('priority')})")
    agent_plan = result.execution_control.get("agent_action_plan", {})
    if isinstance(agent_plan, dict) and agent_plan:
        selected_tools = [
            item.get("name")
            for item in agent_plan.get("tool_registry", [])
            if isinstance(item, dict) and item.get("selected")
        ]
        subtasks = agent_plan.get("subtasks", []) if isinstance(agent_plan.get("subtasks"), list) else []
        lines.extend(["", "## Agent Action Plan"])
        lines.append(f"- Subtasks: {len(subtasks)}")
        lines.append(f"- Selected tools: {', '.join(str(item) for item in selected_tools[:12])}")
        for subtask in subtasks[:6]:
            if isinstance(subtask, dict):
                lines.append(f"- {subtask.get('id')}: {subtask.get('goal')}")
    quality_replan = result.execution_control.get("replan_after_quality", {})
    if isinstance(quality_replan, dict) and quality_replan:
        lines.extend(["", "## Agent Replan After Quality"])
        lines.append(f"- Issue codes: {', '.join(quality_replan.get('issue_codes', [])) or 'none'}")
        lines.append(f"- Attempted actions: {', '.join(quality_replan.get('attempted_actions', []))}")
        lines.append(f"- Selected reason: {quality_replan.get('selected_reason')}")
    answers = task_result.get("answers", {}) if isinstance(task_result.get("answers"), dict) else {}
    if answers:
        lines.extend(["", "## Task-Specific Answers"])
        top_growth = answers.get("top_growth_candidate")
        if isinstance(top_growth, dict):
            lines.append(
                "- Top growth candidate: "
                f"{top_growth.get('label')} delta={top_growth.get('delta')} "
                f"percent_change={top_growth.get('percent_change')}"
            )
        comparisons = answers.get("comparisons")
        if isinstance(comparisons, list) and comparisons:
            lines.append(f"- Comparison candidates: {len(comparisons)}")
        anomalies = answers.get("anomaly_candidates")
        if isinstance(anomalies, list) and anomalies:
            lines.append(f"- Anomaly candidates: {len(anomalies)}")
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
        usage_summary = result.llm_analysis.get("usage_summary")
        if isinstance(usage_summary, dict) and usage_summary.get("tool_call_count"):
            lines.append(
                "LLM usage: "
                f"{usage_summary.get('total_tokens', 0)} tokens across "
                f"{usage_summary.get('tool_call_count', 0)} call(s); "
                f"estimated cost={usage_summary.get('estimated_cost_usd')}"
            )
            lines.append("")
        if isinstance(llm_plan, list) and llm_plan:
            lines.append("Suggested execution plan:")
            lines.extend([f"{index}. {step}" for index, step in enumerate(llm_plan[:12], start=1)])
    if top_pairs:
        lines.extend(["", "## Extracted Fields"])
        lines.extend([f"- {item.get('key')}: {item.get('value')}" for item in top_pairs])
    if top_evidence:
        lines.extend(["", "## Field Evidence"])
        for item in top_evidence:
            provenance = item.get("provenance", {}) if isinstance(item.get("provenance"), dict) else {}
            location = provenance.get("page_no") or provenance.get("line") or provenance.get("level", "unknown")
            lines.append(
                f"- {item.get('key')}: confidence={item.get('confidence')}, "
                f"location={location}, evidence={item.get('evidence_text')}"
            )
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


def _summarize_llm_usage(*items: dict[str, Any]) -> dict[str, Any]:
    usage_items = [
        item.get("llm_usage")
        for item in items
        if isinstance(item, dict) and isinstance(item.get("llm_usage"), dict)
    ]
    total_prompt = 0
    total_completion = 0
    total_tokens = 0
    total_cost = 0.0
    configured_costs = 0
    providers = []
    for item in usage_items:
        usage = item.get("usage", {}) if isinstance(item.get("usage"), dict) else {}
        total_prompt += int(usage.get("prompt_tokens") or 0)
        total_completion += int(usage.get("completion_tokens") or 0)
        total_tokens += int(usage.get("total_tokens") or 0)
        provider = item.get("provider")
        model = item.get("model")
        if provider or model:
            providers.append({"provider": provider, "model": model})
        cost = item.get("cost_estimate", {}) if isinstance(item.get("cost_estimate"), dict) else {}
        if cost.get("configured") and cost.get("estimated_cost") is not None:
            configured_costs += 1
            total_cost += float(cost.get("estimated_cost") or 0)
    return {
        "tool_call_count": len(usage_items),
        "prompt_tokens": total_prompt,
        "completion_tokens": total_completion,
        "total_tokens": total_tokens,
        "cost_configured_calls": configured_costs,
        "estimated_cost_usd": round(total_cost, 8) if configured_costs else None,
        "providers": providers,
        "boundary": (
            "Cost is computed only when token usage is returned by the provider and token price env vars are configured."
        ),
    }


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


def _apply_llm_quality_decision(recovery_decision: dict[str, Any], post_llm_analysis: dict[str, Any]) -> dict[str, Any]:
    findings = post_llm_analysis.get("risk_findings")
    suggestions = post_llm_analysis.get("recovery_suggestions")
    if not isinstance(findings, list):
        findings = []
    if not isinstance(suggestions, list):
        suggestions = []

    risk_counts = {"error": 0, "warning": 0, "info": 0}
    normalized_findings: list[dict[str, Any]] = []
    for item in findings:
        if not isinstance(item, dict):
            continue
        level = str(item.get("level", "info")).lower()
        if level not in risk_counts:
            level = "info"
        risk_counts[level] += 1
        normalized_findings.append(
            {
                "level": level,
                "message": str(item.get("message", "")).strip(),
                "evidence": str(item.get("evidence", "")).strip(),
            }
        )

    normalized_suggestions = [str(item).strip() for item in suggestions if str(item).strip()]
    previous_decision = str(recovery_decision.get("decision", "accept"))
    actions = recovery_decision.setdefault("actions", [])
    if not isinstance(actions, list):
        actions = []
        recovery_decision["actions"] = actions

    applied_effects: list[str] = []
    if risk_counts["error"]:
        recovery_decision["decision"] = "llm_review_required"
        actions.append("LLM post-parse review reported error-level risk; route to review before downstream use.")
        applied_effects.append("decision=llm_review_required")
    elif risk_counts["warning"] and previous_decision == "accept":
        recovery_decision["decision"] = "accept_with_llm_review_notes"
        actions.append("LLM post-parse review reported warning-level risk; keep review note with the result.")
        applied_effects.append("decision=accept_with_llm_review_notes")

    for suggestion in normalized_suggestions[:5]:
        action = f"LLM suggested: {suggestion}"
        if action not in actions:
            actions.append(action)
            applied_effects.append("append_recovery_suggestion")

    quality_decision = {
        "status": post_llm_analysis.get("status", "completed"),
        "previous_decision": previous_decision,
        "final_decision": recovery_decision.get("decision"),
        "risk_counts": risk_counts,
        "risk_findings": normalized_findings[:20],
        "suggested_actions": normalized_suggestions[:10],
        "applied_effects": applied_effects,
    }
    recovery_decision["llm_quality_decision"] = quality_decision
    return quality_decision


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


def _should_fallback_to_cli(
    quality: dict[str, Any],
    suffix: str,
    runner: Any,
    fallback_runner: Any | None,
) -> bool:
    if fallback_runner is None:
        return False
    if suffix in HTML_SUFFIXES | DOCX_SUFFIXES | PPTX_SUFFIXES:
        return False
    if _runner_kind(runner) == "cli":
        return False
    return "no_page_provenance" in _issue_codes(quality)
