from __future__ import annotations

import re
import unicodedata
from typing import Any

from .models import ParseArtifacts


HTML_SUFFIXES = {".html", ".htm"}
DOCX_SUFFIXES = {".docx"}
PPTX_SUFFIXES = {".pptx"}
NATIVE_SUFFIXES = HTML_SUFFIXES | DOCX_SUFFIXES | PPTX_SUFFIXES


def runner_kind(runner: Any) -> str:
    name = runner.__class__.__name__.lower()
    if "agentapi" in name or "agent_api" in name or "agent" in name and "api" in name:
        return "agent-api"
    return "cli"


def requires_page_provenance(suffix: str) -> bool:
    return suffix.lower() not in NATIVE_SUFFIXES


def apply_strict_page_provenance(
    *,
    quality: dict[str, Any],
    suffix: str,
    attempts: list[dict[str, Any]],
    selected_attempt: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    required = requires_page_provenance(suffix)
    issue_codes = quality_issue_codes(quality)
    gate: dict[str, Any] = {
        "enabled": True,
        "required": required,
        "satisfied": None,
        "selected_attempt": selected_attempt,
        "mode": "not_applicable" if not required else "audit_gate",
    }
    if not required:
        gate["satisfied"] = True
        return quality, gate
    if "no_page_provenance" not in issue_codes:
        gate["satisfied"] = True
        gate["mode"] = "audit_grade_result"
        return quality, gate

    updated = dict(quality)
    issues = [dict(issue) for issue in quality.get("issues", []) if isinstance(issue, dict)]
    if "strict_page_provenance_failed" not in issue_codes:
        issues.append(
            {
                "code": "strict_page_provenance_failed",
                "level": "error",
                "message": "Strict page provenance was requested, but the selected result still lacks page-level provenance.",
                "evidence": {
                    "selected_attempt": selected_attempt,
                    "available_attempts": [str(attempt.get("name")) for attempt in attempts if isinstance(attempt, dict)],
                },
            }
        )
    error_count = sum(1 for issue in issues if issue.get("level") == "error")
    warning_count = sum(1 for issue in issues if issue.get("level") == "warning")
    info_count = sum(1 for issue in issues if issue.get("level") == "info")
    updated["issues"] = issues
    updated["issue_count"] = len(issues)
    updated["issue_counts"] = {"error": error_count, "warning": warning_count, "info": info_count}
    updated["status"] = "needs_review"
    updated["score"] = min(int(updated.get("score") or 0), max(0, 100 - error_count * 30 - warning_count * 8))
    gate.update(
        {
            "satisfied": False,
            "mode": "partial_result_returned",
            "failure_code": "strict_page_provenance_failed",
            "action": "rerun_with_local_cli_or_provider_page_provenance",
        }
    )
    return updated, gate


def build_recovery_decision(
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
    if "strict_page_provenance_failed" in issue_codes:
        decision = "strict_page_provenance_failed"
        actions.append(
            "Strict page provenance was requested; treat this as a partial result until a CLI/provider path emits page evidence."
        )
    if suffix in NATIVE_SUFFIXES:
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


def apply_llm_quality_decision(recovery_decision: dict[str, Any], post_llm_analysis: dict[str, Any]) -> dict[str, Any]:
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


def attempt_summary(
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
        "issue_codes": quality_issue_codes(quality),
        "selected": selected,
        "artifacts": artifacts.to_jsonable(),
    }


def failed_attempt_summary(*, name: str, backend: str, method: str, error: str) -> dict[str, Any]:
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


def mark_selected_attempt(attempts: list[dict[str, Any]], selected_attempt: str) -> None:
    for attempt in attempts:
        attempt["selected"] = attempt.get("name") == selected_attempt


def quality_issue_codes(quality: dict[str, Any]) -> list[str]:
    issues = quality.get("issues", [])
    if not isinstance(issues, list):
        return []
    return [str(issue.get("code")) for issue in issues if isinstance(issue, dict)]


def build_runtime_recovery_plan(
    *,
    action_plan: dict[str, Any],
    quality: dict[str, Any],
    suffix: str,
    method: str,
    runner: Any,
    fallback_runner: Any | None,
    llm_recovery_suggestions: Any = None,
    memory_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    issue_codes = quality_issue_codes(quality)
    triggers = action_plan.get("replan_triggers", []) if isinstance(action_plan, dict) else []
    state_machine = action_plan.get("state_machine", {}) if isinstance(action_plan, dict) else {}
    conditional_edges = state_machine.get("conditional_edges", []) if isinstance(state_machine, dict) else []
    edge_by_issue = {
        str(edge.get("condition", "")).removeprefix("quality_issue:"): edge
        for edge in conditional_edges
        if isinstance(edge, dict) and str(edge.get("condition", "")).startswith("quality_issue:")
    }

    actions: list[dict[str, Any]] = []
    for trigger in triggers if isinstance(triggers, list) else []:
        if not isinstance(trigger, dict):
            continue
        issue_code = str(trigger.get("issue_code") or "")
        if issue_code not in issue_codes:
            continue
        actions.append(
            _runtime_recovery_action(
                action=str(trigger.get("action") or ""),
                issue_code=issue_code,
                source="agent_action_plan.replan_triggers",
                reason=str(trigger.get("reason") or ""),
                state_edge=edge_by_issue.get(issue_code),
            )
        )

    if should_run_text_cleanup(quality):
        actions.append(
            _runtime_recovery_action(
                action="text_cleanup",
                issue_code="possible_mojibake",
                source="validator_policy",
                reason="text cleanup remains available for mojibake even if no trigger matched",
                state_edge=edge_by_issue.get("possible_mojibake"),
            )
        )
    if should_retry_with_ocr(quality, suffix, method):
        actions.append(
            _runtime_recovery_action(
                action="ocr_retry",
                issue_code=_first_matching_issue(
                    issue_codes,
                    {
                        "empty_markdown",
                        "no_content_blocks",
                        "short_text",
                        "weak_page_provenance",
                        "financial_signal_missing",
                        "expected_date_missing",
                        "expected_recommendation_missing",
                        "expected_anomaly_signal_missing",
                    },
                )
                or "ocr_retry_candidate",
                source="validator_policy",
                reason="quality report indicates sparse or OCR-sensitive result",
                state_edge=edge_by_issue.get("short_text"),
            )
        )
    if should_fallback_to_cli(quality, suffix, runner, fallback_runner):
        actions.append(
            _runtime_recovery_action(
                action="cli_fallback",
                issue_code="no_page_provenance",
                source="validator_policy",
                reason="page provenance is missing and a fallback runner is configured",
                state_edge=edge_by_issue.get("no_page_provenance"),
            )
        )
    for suggestion in _iter_llm_recovery_suggestions(llm_recovery_suggestions):
        actions.append(
            _runtime_recovery_action(
                action=_map_llm_recovery_suggestion(suggestion),
                issue_code="llm_suggested",
                source="llm_post_review.recovery_suggestions",
                reason=suggestion,
                state_edge=None,
            )
        )
    for action in _iter_memory_recovery_actions(memory_summary):
        actions.append(
            _runtime_recovery_action(
                action=action,
                issue_code="memory_recommended",
                source="local_sqlite_memory.recommended_actions",
                reason="Prior local runs with the same profile and overlapping issue codes selected this recovery action successfully.",
                state_edge=None,
            )
        )

    deduped = _dedupe_runtime_actions(actions)
    for item in deduped:
        item["skip_reason"] = runtime_recovery_skip_reason(
            str(item.get("action")),
            quality=quality,
            suffix=suffix,
            method=method,
            runner=runner,
            fallback_runner=fallback_runner,
            source=str(item.get("source") or ""),
            issue_code=str(item.get("issue_code") or ""),
        )
        item["runtime_status"] = "planned" if not item["skip_reason"] else "skipped"
    return {
        "source": "agent_action_plan.state_machine",
        "initial_issue_codes": issue_codes,
        "actions": deduped,
        "memory_recommended_actions": list((memory_summary or {}).get("recommended_actions", []))
        if isinstance(memory_summary, dict)
        else [],
        "loop_policy": state_machine.get("loop_policy", {}) if isinstance(state_machine, dict) else {},
        "boundary": "Runtime recovery consumes agent_action_plan replan triggers, validator fallback policies, and bounded LLM recovery suggestions; it is deterministic, not a general multi-turn planner.",
    }


def runtime_recovery_skip_reason(
    action: str,
    *,
    quality: dict[str, Any],
    suffix: str,
    method: str,
    runner: Any,
    fallback_runner: Any | None,
    source: str = "",
    issue_code: str = "",
) -> str:
    llm_suggested = source.startswith("llm_post_review") and issue_code == "llm_suggested"
    if action == "text_cleanup":
        if should_run_text_cleanup(quality) or llm_suggested:
            return ""
        return "possible_mojibake no longer present"
    if action == "ocr_retry":
        if should_retry_with_ocr(quality, suffix, method):
            return ""
        if llm_suggested and suffix not in NATIVE_SUFFIXES and method.lower() != "ocr":
            return ""
        return "OCR retry is not eligible for current file/method/quality"
    if action == "cli_fallback":
        if should_fallback_to_cli(quality, suffix, runner, fallback_runner):
            return ""
        if (
            llm_suggested
            and fallback_runner is not None
            and suffix not in NATIVE_SUFFIXES
            and runner_kind(runner) != "cli"
        ):
            return ""
        return "CLI fallback is not eligible or no fallback runner is configured"
    if action in {"manual_numeric_review", "visual_review", "chunk_stitch_review", "llm_suggested_review"}:
        return "manual_or_advisory_action_only"
    return "unsupported_recovery_action"


def is_better_quality(candidate: dict[str, Any], current: dict[str, Any]) -> bool:
    return _quality_key(candidate) > _quality_key(current)


def clean_text_artifacts(markdown: str, content_list: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    return _clean_text(markdown), [_clean_json_value(item) for item in content_list]


def should_run_text_cleanup(quality: dict[str, Any]) -> bool:
    return "possible_mojibake" in quality_issue_codes(quality)


def should_retry_with_ocr(quality: dict[str, Any], suffix: str, method: str) -> bool:
    if suffix in NATIVE_SUFFIXES:
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
    return quality.get("status") == "needs_review" or bool(set(quality_issue_codes(quality)) & retry_codes)


def should_fallback_to_cli(
    quality: dict[str, Any],
    suffix: str,
    runner: Any,
    fallback_runner: Any | None,
) -> bool:
    if fallback_runner is None:
        return False
    if suffix in NATIVE_SUFFIXES:
        return False
    if runner_kind(runner) == "cli":
        return False
    return "no_page_provenance" in quality_issue_codes(quality)


def _runtime_recovery_action(
    *,
    action: str,
    issue_code: str,
    source: str,
    reason: str,
    state_edge: Any,
) -> dict[str, Any]:
    edge = state_edge if isinstance(state_edge, dict) else {}
    return {
        "action": action,
        "issue_code": issue_code,
        "source": source,
        "reason": reason,
        "runner_change": edge.get("runner_change"),
        "method_change": edge.get("method_change"),
    }


def _dedupe_runtime_actions(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    priority = {"text_cleanup": 0, "ocr_retry": 1, "cli_fallback": 2, "manual_numeric_review": 3}
    deduped: dict[str, dict[str, Any]] = {}
    for action in actions:
        name = str(action.get("action") or "")
        if not name or name in deduped:
            if name and name in deduped:
                deduped[name].setdefault("additional_sources", []).append(
                    {
                        "source": action.get("source"),
                        "issue_code": action.get("issue_code"),
                        "reason": action.get("reason"),
                    }
                )
            continue
        deduped[name] = action
    return sorted(deduped.values(), key=lambda item: priority.get(str(item.get("action")), 99))


def _iter_llm_recovery_suggestions(suggestions: Any) -> list[str]:
    if not isinstance(suggestions, list):
        return []
    return [str(item).strip() for item in suggestions if str(item).strip()][:10]


def _map_llm_recovery_suggestion(suggestion: str) -> str:
    lowered = suggestion.lower()
    if any(token in lowered for token in ("mojibake", "乱码", "clean", "cleanup", "text cleanup", "normalize text")):
        return "text_cleanup"
    if any(token in lowered for token in ("ocr", "识别", "retry", "rerun", "重试", "重跑")):
        return "ocr_retry"
    if any(token in lowered for token in ("cli", "fallback", "local", "本地", "页级", "page provenance", "page-level")):
        return "cli_fallback"
    return "llm_suggested_review"


def _iter_memory_recovery_actions(memory_summary: dict[str, Any] | None) -> list[str]:
    if not isinstance(memory_summary, dict):
        return []
    raw_actions = memory_summary.get("recommended_actions")
    if not isinstance(raw_actions, list):
        return []
    supported = {"text_cleanup", "ocr_retry", "cli_fallback"}
    actions: list[str] = []
    for item in raw_actions:
        action = str(item).strip()
        if action in supported and action not in actions:
            actions.append(action)
    return actions[:3]


def _first_matching_issue(issue_codes: list[str], candidates: set[str]) -> str | None:
    for code in issue_codes:
        if code in candidates:
            return code
    return None


def _quality_key(quality: dict[str, Any]) -> tuple[int, int, int, int]:
    rank = {"needs_review": 0, "pass_with_warnings": 1, "pass": 2}
    issue_counts = quality.get("issue_counts", {})
    warning_count = int(issue_counts.get("warning", 0)) if isinstance(issue_counts, dict) else 0
    issue_penalty = sum(_issue_penalty(code) for code in quality_issue_codes(quality))
    return (rank.get(str(quality.get("status")), -1), -issue_penalty, int(quality.get("score") or 0), -warning_count)


def _issue_penalty(code: str) -> int:
    penalties = {
        "strict_page_provenance_failed": 100,
        "empty_markdown": 90,
        "no_content_blocks": 80,
        "numeric_total_mismatch": 70,
        "no_page_provenance": 45,
        "short_text": 35,
        "possible_mojibake": 25,
        "weak_clause_structure": 20,
        "expected_anomaly_signal_missing": 15,
        "expected_recommendation_missing": 15,
        "expected_date_missing": 15,
        "document_level_provenance": 5,
        "numeric_total_needs_review": 5,
        "numeric_total_verified": 0,
    }
    return penalties.get(code, 10)


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
        "杳": "查",
        "曰": "日",
        "己完成": "已完成",
    }
    cleaned = unicodedata.normalize("NFC", text)
    for bad, good in replacements.items():
        cleaned = cleaned.replace(bad, good)
    cleaned = re.sub(r"([^\W\d_])\1{3,}", r"\1\1", cleaned, flags=re.UNICODE)
    return "\n".join(" ".join(line.split()) for line in cleaned.splitlines()).strip()
