from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LABELS_PATH = PROJECT_ROOT / "examples" / "evaluation" / "labels.json"
OUT_DIR = PROJECT_ROOT / "submission_artifacts" / "stability"


def main() -> None:
    labels = json.loads(LABELS_PATH.read_text(encoding="utf-8"))
    cases = []
    quality_counts: Counter[str] = Counter()
    provenance_counts: Counter[str] = Counter()
    issue_counts: Counter[str] = Counter()
    tool_counts: Counter[str] = Counter()
    total_tool_elapsed = 0.0
    max_tool_elapsed = 0.0
    recovery_executed = 0
    total_steps = 0
    total_tool_calls = 0

    for raw_case in labels["cases"]:
        result_path = PROJECT_ROOT / raw_case["result_path"]
        result = json.loads(result_path.read_text(encoding="utf-8"))
        trace_path = _resolve_trace_path(result)
        trace = json.loads(trace_path.read_text(encoding="utf-8")) if trace_path.exists() else {}
        quality = result.get("quality", {})
        extracted = result.get("extracted", {})
        recovery = result.get("recovery_decision", {})
        tool_calls = trace.get("tool_calls", []) if isinstance(trace.get("tool_calls"), list) else []
        steps = trace.get("steps", []) if isinstance(trace.get("steps"), list) else []
        elapsed = sum(float(call.get("elapsed_seconds") or 0) for call in tool_calls if isinstance(call, dict))

        quality_status = str(quality.get("status") or "unknown")
        provenance = (
            extracted.get("content_summary", {}).get("provenance_level")
            if isinstance(extracted.get("content_summary"), dict)
            else "unknown"
        )
        issues = [
            str(item.get("code"))
            for item in quality.get("issues", [])
            if isinstance(item, dict) and item.get("code")
        ]
        tools = [
            str(call.get("tool"))
            for call in tool_calls
            if isinstance(call, dict) and call.get("tool")
        ]

        quality_counts[quality_status] += 1
        provenance_counts[str(provenance or "unknown")] += 1
        issue_counts.update(issues)
        tool_counts.update(tools)
        total_tool_elapsed += elapsed
        max_tool_elapsed = max(max_tool_elapsed, *(float(call.get("elapsed_seconds") or 0) for call in tool_calls), 0.0)
        total_steps += len(steps)
        total_tool_calls += len(tool_calls)
        if recovery.get("executed"):
            recovery_executed += 1

        trace_status = _infer_trace_status(trace)
        cases.append(
            {
                "id": raw_case["id"],
                "result_path": _display_path(result_path),
                "trace_path": _display_path(trace_path),
                "status": trace_status,
                "quality_status": quality_status,
                "quality_score": quality.get("score"),
                "provenance_level": provenance,
                "step_count": len(steps),
                "tool_call_count": len(tool_calls),
                "tool_elapsed_seconds": round(elapsed, 3),
                "recovery_executed": bool(recovery.get("executed")),
                "selected_attempt": recovery.get("selected_attempt"),
                "issue_codes": issues,
                "tools": tools,
            }
        )

    report = {
        "schema_version": "2026-05-23",
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "scope": (
            "Submission artifact stability report over saved evaluation cases. "
            "This is not a high-concurrency load test."
        ),
        "case_count": len(cases),
        "completed_cases": sum(1 for item in cases if item["status"] in {"completed", "completed_inferred"}),
        "result_files_checked": len(cases),
        "trace_files_checked": sum(1 for item in cases if (PROJECT_ROOT / item["trace_path"]).exists()),
        "total_steps": total_steps,
        "total_tool_calls": total_tool_calls,
        "total_tool_elapsed_seconds": round(total_tool_elapsed, 3),
        "max_tool_elapsed_seconds": round(max_tool_elapsed, 3),
        "recovery_executed_cases": recovery_executed,
        "quality_status_counts": dict(sorted(quality_counts.items())),
        "provenance_level_counts": dict(sorted(provenance_counts.items())),
        "issue_code_counts": dict(sorted(issue_counts.items())),
        "tool_counts": dict(sorted(tool_counts.items())),
        "cases": cases,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "stability_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "stability_report.md").write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"out_dir": str(OUT_DIR), "case_count": len(cases)}, ensure_ascii=False, indent=2))


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Stability Report",
        "",
        "This report checks saved submission artifacts referenced by `examples/evaluation/labels.json`.",
        "It verifies result/trace presence and summarizes execution evidence. It is not a high-concurrency load test.",
        "",
        "## Aggregate",
        "",
        f"- Cases checked: {report['case_count']}",
        f"- Completed or inferred-completed traces: {report['completed_cases']}/{report['case_count']}",
        f"- Result files checked: {report['result_files_checked']}",
        f"- Trace files checked: {report['trace_files_checked']}",
        f"- Total trace steps: {report['total_steps']}",
        f"- Total tool calls: {report['total_tool_calls']}",
        f"- Total tool elapsed seconds: {report['total_tool_elapsed_seconds']}",
        f"- Max single-tool elapsed seconds: {report['max_tool_elapsed_seconds']}",
        f"- Recovery executed cases: {report['recovery_executed_cases']}",
        f"- Quality status counts: `{json.dumps(report['quality_status_counts'], ensure_ascii=False)}`",
        f"- Provenance level counts: `{json.dumps(report['provenance_level_counts'], ensure_ascii=False)}`",
        f"- Tool counts: `{json.dumps(report['tool_counts'], ensure_ascii=False)}`",
        "",
        "## Cases",
        "",
        "| Case | Trace | Quality | Provenance | Steps | Tools | Recovery | Tool Seconds |",
        "| --- | --- | --- | --- | ---: | ---: | --- | ---: |",
    ]
    for item in report["cases"]:
        lines.append(
            "| {id} | {status} | {quality} ({score}) | {provenance} | {steps} | {tools} | {recovery} / {attempt} | {seconds} |".format(
                id=item["id"],
                status=item["status"],
                quality=item["quality_status"],
                score=item["quality_score"],
                provenance=item["provenance_level"],
                steps=item["step_count"],
                tools=item["tool_call_count"],
                recovery=str(item["recovery_executed"]).lower(),
                attempt=item["selected_attempt"],
                seconds=item["tool_elapsed_seconds"],
            )
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- This report summarizes saved artifact stability and trace completeness.",
            "- It does not prove high-concurrency behavior; a separate live load test is still recommended before a production claim.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def _resolve_trace_path(result: dict[str, Any]) -> Path:
    value = result.get("trace_path")
    if value:
        path = Path(str(value).replace("<PROJECT_ROOT>", str(PROJECT_ROOT)))
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        if path.exists():
            return path
    result_path = result.get("result_path")
    if result_path:
        path = Path(str(result_path).replace("<PROJECT_ROOT>", str(PROJECT_ROOT)))
        if path.is_absolute():
            sibling = path.with_name("trace.json")
            if sibling.exists():
                return sibling
    return PROJECT_ROOT / "missing-trace.json"


def _infer_trace_status(trace: dict[str, Any]) -> str:
    status = trace.get("status")
    if status:
        return str(status)
    steps = trace.get("steps", []) if isinstance(trace.get("steps"), list) else []
    if steps and all(isinstance(step, dict) and step.get("status") == "completed" for step in steps):
        return "completed_inferred"
    if any(isinstance(step, dict) and step.get("status") == "failed" for step in steps):
        return "failed_inferred"
    return "unknown"


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


if __name__ == "__main__":
    main()
