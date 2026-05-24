from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = PROJECT_ROOT / "submission_artifacts"
OUT_DIR = ARTIFACT_ROOT / "recovery_effectiveness"


def main() -> None:
    report = build_report()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "recovery_effectiveness_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (OUT_DIR / "recovery_effectiveness_report.md").write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"out_dir": display_path(OUT_DIR), "cases": report["aggregate"]["results_with_recovery"]}, ensure_ascii=False))


def build_report() -> dict[str, Any]:
    rows = []
    attempt_counts: Counter[str] = Counter()
    selected_counts: Counter[str] = Counter()
    initial_issue_counts: Counter[str] = Counter()
    failed_attempt_counts: Counter[str] = Counter()
    executed = 0
    selected_non_initial = 0
    total_extra_seconds = 0.0

    for path in sorted(ARTIFACT_ROOT.rglob("result.json")):
        if "request_artifacts" in path.parts:
            continue
        result = load_json(path)
        if not isinstance(result, dict):
            continue
        recovery = result.get("recovery_decision")
        if not isinstance(recovery, dict):
            continue
        trace = load_json(resolve_trace_path(result, path))
        tool_seconds = trace_tool_seconds(trace)
        attempts = recovery.get("attempts", []) if isinstance(recovery.get("attempts"), list) else []
        if not attempts:
            continue
        row = summarize_recovery(path, result, recovery, tool_seconds)
        rows.append(row)
        if row["executed"]:
            executed += 1
            total_extra_seconds += row["non_initial_tool_seconds"]
        if row["selected_attempt"] != "initial":
            selected_non_initial += 1
        attempt_counts.update(row["attempt_names"])
        selected_counts[row["selected_attempt"]] += 1
        initial_issue_counts.update(row["initial_issue_codes"])
        failed_attempt_counts.update(row["failed_attempts"])

    return {
        "schema_version": "2026-05-24",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "scope": "Recovery effectiveness summary over saved submission artifacts.",
        "aggregate": {
            "results_with_recovery": len(rows),
            "recovery_executed": executed,
            "selected_non_initial": selected_non_initial,
            "executed_rate": executed / len(rows) if rows else 0.0,
            "selected_non_initial_rate": selected_non_initial / len(rows) if rows else 0.0,
            "average_non_initial_tool_seconds_when_executed": round(total_extra_seconds / executed, 3) if executed else 0.0,
            "attempt_counts": dict(sorted(attempt_counts.items())),
            "selected_attempt_counts": dict(sorted(selected_counts.items())),
            "initial_issue_counts": dict(sorted(initial_issue_counts.items())),
            "failed_attempt_counts": dict(sorted(failed_attempt_counts.items())),
        },
        "cases": rows,
        "interpretation": [
            "Executed recovery means the Agent attempted a second path such as text cleanup, OCR retry, or CLI fallback.",
            "Selected non-initial means the recovered result replaced the first attempt.",
            "Cached CLI fallback is counted separately in tool names and should not be presented as live CLI/GPU evidence.",
        ],
    }


def summarize_recovery(path: Path, result: dict[str, Any], recovery: dict[str, Any], tool_seconds: dict[str, float]) -> dict[str, Any]:
    attempts = recovery.get("attempts", []) if isinstance(recovery.get("attempts"), list) else []
    attempt_names = [str(item.get("name")) for item in attempts if isinstance(item, dict)]
    failed_attempts = [
        str(item.get("name"))
        for item in attempts
        if isinstance(item, dict) and item.get("quality_status") == "failed"
    ]
    selected_attempt = str(recovery.get("selected_attempt") or "unknown")
    non_initial_seconds = sum(value for name, value in tool_seconds.items() if name != "initial")
    quality = result.get("quality", {}) if isinstance(result.get("quality"), dict) else {}
    return {
        "result_path": display_path(path),
        "run_id": result.get("run_id"),
        "profile": result.get("profile"),
        "quality_status": quality.get("status"),
        "quality_score": quality.get("score"),
        "decision": recovery.get("decision"),
        "executed": bool(recovery.get("executed")),
        "selected_attempt": selected_attempt,
        "attempt_names": attempt_names,
        "initial_issue_codes": [str(item) for item in recovery.get("initial_issue_codes", [])],
        "final_issue_codes": [str(item) for item in recovery.get("issue_codes", [])],
        "failed_attempts": failed_attempts,
        "non_initial_tool_seconds": round(non_initial_seconds, 3),
        "llm_quality_decision_present": isinstance(recovery.get("llm_quality_decision"), dict),
    }


def resolve_trace_path(result: dict[str, Any], result_path: Path) -> Path:
    raw = result.get("trace_path")
    if raw:
        path = Path(str(raw).replace("<PROJECT_ROOT>", str(PROJECT_ROOT)))
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        if path.exists():
            return path
    return result_path.with_name("trace.json")


def trace_tool_seconds(trace: Any) -> dict[str, float]:
    if not isinstance(trace, dict) or not isinstance(trace.get("tool_calls"), list):
        return {}
    seconds: dict[str, float] = {}
    for call in trace["tool_calls"]:
        if not isinstance(call, dict):
            continue
        tool = str(call.get("tool") or "unknown")
        seconds[tool] = seconds.get(tool, 0.0) + float(call.get("elapsed_seconds") or 0)
    return seconds


def render_markdown(report: dict[str, Any]) -> str:
    aggregate = report["aggregate"]
    lines = [
        "# Recovery Effectiveness Report",
        "",
        report["scope"],
        "",
        "## Aggregate",
        "",
        f"- Results with recovery records: {aggregate['results_with_recovery']}",
        f"- Recovery executed: {aggregate['recovery_executed']}",
        f"- Selected non-initial result: {aggregate['selected_non_initial']}",
        f"- Executed rate: {aggregate['executed_rate']:.2%}",
        f"- Selected non-initial rate: {aggregate['selected_non_initial_rate']:.2%}",
        f"- Avg non-initial tool seconds when executed: {aggregate['average_non_initial_tool_seconds_when_executed']}",
        f"- Attempt counts: `{json.dumps(aggregate['attempt_counts'], ensure_ascii=False)}`",
        f"- Selected attempt counts: `{json.dumps(aggregate['selected_attempt_counts'], ensure_ascii=False)}`",
        f"- Initial issue counts: `{json.dumps(aggregate['initial_issue_counts'], ensure_ascii=False)}`",
        f"- Failed attempt counts: `{json.dumps(aggregate['failed_attempt_counts'], ensure_ascii=False)}`",
        "",
        "## Cases",
        "",
        "| Result | Decision | Executed | Selected | Initial Issues | Final Quality | LLM Decision |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in report["cases"]:
        lines.append(
            "| {path} | {decision} | {executed} | {selected} | {issues} | {quality} ({score}) | {llm} |".format(
                path=row["result_path"],
                decision=row["decision"],
                executed=str(row["executed"]).lower(),
                selected=row["selected_attempt"],
                issues=", ".join(row["initial_issue_codes"]) or "-",
                quality=row["quality_status"],
                score=row["quality_score"],
                llm=str(row["llm_quality_decision_present"]).lower(),
            )
        )
    lines.extend(["", "## Interpretation", ""])
    lines.extend(f"- {item}" for item in report["interpretation"])
    lines.append("")
    return "\n".join(lines)


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
