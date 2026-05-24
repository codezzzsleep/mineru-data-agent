from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = PROJECT_ROOT / "submission_artifacts"
OUT_DIR = ARTIFACT_ROOT / "agent_value"

CURATED_DIRS = [
    "cases",
    "mineru_cases",
    "agent_api_cases",
    "recovery_cases",
    "failure_recovery_cases",
    "office_cases",
    "challenge_cases",
    "adaptive_cases",
    "agent_decision_cases",
    "public_real_cases",
    "llm_cases",
    "long_document_chunks",
]


def main() -> None:
    report = build_report()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "agent_value_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "agent_value_report.md").write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"out_dir": display_path(OUT_DIR), "cases": report["aggregate"]["cases"]}, ensure_ascii=False))


def build_report() -> dict[str, Any]:
    rows = [summarize_result(path) for path in find_result_files()]
    decision_modes = Counter(row["decision_mode"] for row in rows)
    parser_runners = Counter(row["runner"] for row in rows)
    return {
        "schema_version": "2026-05-24",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "scope": "Saved-artifact report of what the Agent layer adds on top of parser Markdown/content_list artifacts.",
        "aggregate": {
            "cases": len(rows),
            "decision_modes": dict(sorted(decision_modes.items())),
            "parser_runners": dict(sorted(parser_runners.items())),
            "with_state_machine": sum(1 for row in rows if row["has_state_machine"]),
            "with_task_result": sum(1 for row in rows if row["task_result_keys"] > 0),
            "with_field_evidence": sum(1 for row in rows if row["field_evidence_count"] > 0),
            "with_quality_issues": sum(1 for row in rows if row["quality_issue_count"] > 0),
            "with_recovery_attempts": sum(1 for row in rows if row["recovery_attempt_count"] > 1),
            "selected_non_initial": sum(1 for row in rows if row["selected_non_initial"]),
            "with_retrieval_chunks": sum(1 for row in rows if row["retrieval_chunks"] > 0),
            "with_live_llm_trace": sum(1 for row in rows if row["live_llm_trace_calls"] > 0),
        },
        "agent_layer_fields": [
            "execution_control.planning_rationale",
            "execution_control.adaptive_decision",
            "execution_control.agent_action_plan",
            "execution_control.agent_action_plan.state_machine",
            "execution_control.replan_after_quality",
            "quality.issues",
            "recovery_decision",
            "extracted.field_evidence",
            "extracted.task_result",
            "retrieval_export",
            "trace.json",
            "summary.md",
        ],
        "rows": rows,
        "boundaries": [
            "This is not a third-party parser benchmark and does not claim higher OCR/parser accuracy than raw MinerU.",
            "It compares saved parser artifacts against saved Agent-layer audit, validation, recovery, and export fields.",
            "Offline agent_decision_cases are counted separately from live LLM traces.",
            "Controlled failure_recovery_cases are fault-injection evidence, not live OCR/network/GPU evidence.",
        ],
    }


def find_result_files() -> list[Path]:
    paths: list[Path] = []
    for dirname in CURATED_DIRS:
        root = ARTIFACT_ROOT / dirname
        if root.exists():
            paths.extend(root.rglob("result.json"))
    return sorted(paths)


def summarize_result(path: Path) -> dict[str, Any]:
    result = load_json(path)
    trace = load_json(path.with_name("trace.json"))
    execution = result.get("execution_control", {}) if isinstance(result, dict) else {}
    extracted = result.get("extracted", {}) if isinstance(result, dict) else {}
    quality = result.get("quality", {}) if isinstance(result, dict) else {}
    recovery = result.get("recovery_decision", {}) if isinstance(result, dict) else {}
    retrieval = result.get("retrieval_export", {}) if isinstance(result, dict) else {}
    agent_plan = execution.get("agent_action_plan", {}) if isinstance(execution, dict) else {}
    adaptive = execution.get("adaptive_decision", {}) if isinstance(execution, dict) else {}
    planning = execution.get("planning_rationale", {}) if isinstance(execution, dict) else {}
    rel = display_path(path)
    rows_parts = path.relative_to(ARTIFACT_ROOT).parts
    category = rows_parts[0] if rows_parts else ""
    live_llm_trace_calls = count_live_llm_trace_calls(trace)
    return {
        "result_path": rel,
        "category": category,
        "case_id": path.parent.name,
        "task": result.get("task") if isinstance(result, dict) else None,
        "decision_mode": decision_mode(path, execution, live_llm_trace_calls),
        "planning_source": planning.get("source") if isinstance(planning, dict) else None,
        "runner": nested_get(execution, "resolved", "runner") or nested_get(execution, "initial", "runner") or "-",
        "profile": result.get("profile") if isinstance(result, dict) else None,
        "parser_artifact_summary": parser_artifact_summary(extracted),
        "task_intents": len(adaptive.get("task_intents", [])) if isinstance(adaptive.get("task_intents"), list) else 0,
        "target_schema_fields": len(adaptive.get("target_schema", {})) if isinstance(adaptive.get("target_schema"), dict) else 0,
        "post_processors": len(adaptive.get("post_processors", [])) if isinstance(adaptive.get("post_processors"), list) else 0,
        "has_action_plan": bool(agent_plan),
        "has_state_machine": bool(agent_plan.get("state_machine")) if isinstance(agent_plan, dict) else False,
        "replan_triggers": len(agent_plan.get("replan_triggers", [])) if isinstance(agent_plan.get("replan_triggers"), list) else 0,
        "quality_status": quality.get("status") if isinstance(quality, dict) else None,
        "quality_score": quality.get("score") if isinstance(quality, dict) else None,
        "quality_issue_count": len(quality.get("issues", [])) if isinstance(quality.get("issues"), list) else 0,
        "quality_issue_codes": issue_codes(quality),
        "recovery_decision": recovery.get("decision") if isinstance(recovery, dict) else None,
        "recovery_attempt_count": len(recovery.get("attempts", [])) if isinstance(recovery.get("attempts"), list) else 0,
        "selected_attempt": recovery.get("selected_attempt") if isinstance(recovery, dict) else None,
        "selected_non_initial": recovery.get("selected_attempt") not in {None, "", "initial"} if isinstance(recovery, dict) else False,
        "field_evidence_count": count_field_evidence(extracted),
        "task_result_keys": len(extracted.get("task_result", {})) if isinstance(extracted.get("task_result"), dict) else 0,
        "retrieval_chunks": count_retrieval_chunks(retrieval),
        "trace_steps": len(trace.get("steps", [])) if isinstance(trace, dict) and isinstance(trace.get("steps"), list) else 0,
        "trace_tool_calls": len(trace.get("tool_calls", [])) if isinstance(trace, dict) and isinstance(trace.get("tool_calls"), list) else 0,
        "live_llm_trace_calls": live_llm_trace_calls,
    }


def decision_mode(path: Path, execution: dict[str, Any], live_llm_trace_calls: int) -> str:
    rel = display_path(path)
    if "failure_recovery_cases/" in rel:
        return "controlled_fault_injection"
    if "agent_decision_cases/" in rel:
        return "offline_scripted_decision_regression"
    if live_llm_trace_calls:
        return "saved_live_llm_trace"
    if execution.get("llm_preplan_enabled"):
        return "llm_enabled_saved_result_without_live_trace"
    return "deterministic_rules"


def parser_artifact_summary(extracted: dict[str, Any]) -> dict[str, Any]:
    summary = extracted.get("content_summary", {}) if isinstance(extracted, dict) else {}
    return {
        "content_items": summary.get("item_count") if isinstance(summary, dict) else None,
        "provenance_level": summary.get("provenance_level") if isinstance(summary, dict) else None,
        "tables": len(extracted.get("tables", [])) if isinstance(extracted.get("tables"), list) else 0,
        "key_values": len(extracted.get("key_values", [])) if isinstance(extracted.get("key_values"), list) else 0,
        "numeric_facts": len(extracted.get("numeric_facts", [])) if isinstance(extracted.get("numeric_facts"), list) else 0,
    }


def issue_codes(quality: dict[str, Any]) -> list[str]:
    issues = quality.get("issues", []) if isinstance(quality, dict) else []
    codes = []
    for issue in issues if isinstance(issues, list) else []:
        if isinstance(issue, dict) and issue.get("code"):
            codes.append(str(issue["code"]))
    return codes


def count_field_evidence(extracted: dict[str, Any]) -> int:
    if not isinstance(extracted, dict):
        return 0
    evidence = extracted.get("field_evidence")
    if isinstance(evidence, list):
        return len(evidence)
    evidence_map = extracted.get("field_evidence_map")
    if isinstance(evidence_map, dict):
        return len(evidence_map)
    return 0


def count_retrieval_chunks(retrieval: dict[str, Any]) -> int:
    if not isinstance(retrieval, dict):
        return 0
    if isinstance(retrieval.get("chunk_count"), int):
        return int(retrieval["chunk_count"])
    chunks_path = retrieval.get("chunks_path")
    if not chunks_path:
        return 0
    path = resolve_path(chunks_path)
    try:
        return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    except Exception:
        return 0


def count_live_llm_trace_calls(trace: Any) -> int:
    if not isinstance(trace, dict):
        return 0
    count = 0
    for call in trace.get("tool_calls", []) if isinstance(trace.get("tool_calls"), list) else []:
        if not isinstance(call, dict):
            continue
        name = str(call.get("name") or call.get("tool") or "").lower()
        command = " ".join(str(item).lower() for item in call.get("command", []) if isinstance(call.get("command"), list))
        if "modelscope-llm" in name or "openai-compatible-llm" in name:
            count += 1
    return count


def nested_get(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def render_markdown(report: dict[str, Any]) -> str:
    aggregate = report["aggregate"]
    lines = [
        "# Agent Value Report",
        "",
        report["scope"],
        "",
        "## Aggregate",
        "",
        f"- Cases: {aggregate['cases']}",
        f"- Decision modes: `{json.dumps(aggregate['decision_modes'], ensure_ascii=False)}`",
        f"- Parser runners: `{json.dumps(aggregate['parser_runners'], ensure_ascii=False)}`",
        f"- With state machine: {aggregate['with_state_machine']}",
        f"- With task_result: {aggregate['with_task_result']}",
        f"- With field evidence: {aggregate['with_field_evidence']}",
        f"- With quality issues: {aggregate['with_quality_issues']}",
        f"- With recovery attempts beyond initial: {aggregate['with_recovery_attempts']}",
        f"- Selected non-initial recovery: {aggregate['selected_non_initial']}",
        f"- With retrieval chunks: {aggregate['with_retrieval_chunks']}",
        f"- With live LLM trace calls: {aggregate['with_live_llm_trace']}",
        "",
        "## Agent-Layer Fields Checked",
        "",
    ]
    lines.extend(f"- `{field}`" for field in report["agent_layer_fields"])
    lines.extend(
        [
            "",
            "## Case Rows",
            "",
            "| Case | Mode | Runner | Schema | State | Quality | Recovery | Evidence | Retrieval |",
            "| --- | --- | --- | ---: | --- | --- | --- | ---: | ---: |",
        ]
    )
    for row in report["rows"]:
        quality = f"{row['quality_status']} ({row['quality_score']})"
        recovery = f"{row['recovery_decision']} / {row['selected_attempt']}"
        state = "yes" if row["has_state_machine"] else "-"
        lines.append(
            "| `{case}` | `{mode}` | `{runner}` | {schema} | {state} | {quality} | {recovery} | {evidence} | {chunks} |".format(
                case=row["result_path"],
                mode=row["decision_mode"],
                runner=row["runner"],
                schema=row["target_schema_fields"],
                state=state,
                quality=quality,
                recovery=recovery,
                evidence=row["field_evidence_count"],
                chunks=row["retrieval_chunks"],
            )
        )
    lines.extend(["", "## Boundaries", ""])
    lines.extend(f"- {item}" for item in report["boundaries"])
    lines.append("")
    return "\n".join(lines)


def resolve_path(value: Any) -> Path:
    raw = str(value).replace("<PROJECT_ROOT>", str(PROJECT_ROOT))
    path = Path(raw)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


if __name__ == "__main__":
    main()
