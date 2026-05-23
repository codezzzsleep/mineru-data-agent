from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVALUATION_PATH = PROJECT_ROOT / "submission_artifacts" / "evaluation" / "evaluation_metrics.json"
STABILITY_PATH = PROJECT_ROOT / "submission_artifacts" / "stability" / "stability_report.json"
OUT_DIR = PROJECT_ROOT / "submission_artifacts" / "baseline_comparison"


GROUPS = [
    {
        "id": "html_native_fixtures",
        "name": "Native HTML/Web fixtures",
        "matcher": lambda case_id: case_id.startswith("html_"),
        "interpretation": "Low-cost deterministic parser path for task planning, schema, trace, and retrieval checks.",
    },
    {
        "id": "mineru_cli_pdf",
        "name": "MinerU CLI PDF with page provenance",
        "matcher": lambda case_id: case_id.startswith("mineru_cli_"),
        "interpretation": "Full local MinerU artifact path with page-level provenance and saved middle/layout/model files.",
    },
    {
        "id": "office_native",
        "name": "Native Office files",
        "matcher": lambda case_id: case_id.startswith("office_"),
        "interpretation": "DOCX/PPTX structure path for non-PDF enterprise material.",
    },
    {
        "id": "llm_recovery_fallback",
        "name": "LLM plan plus recovery fallback",
        "matcher": lambda case_id: case_id.startswith("pdf_llm_"),
        "interpretation": "Agent scheduling/recovery evidence: online API warning triggers CLI fallback and accepted recovery.",
    },
    {
        "id": "challenge_fixtures",
        "name": "Challenge fixtures",
        "matcher": lambda case_id: case_id.startswith("challenge_"),
        "interpretation": "Stress fixtures for cross-page tables, OCR noise, industry matrices, and workflow incidents.",
    },
    {
        "id": "public_real_pdf",
        "name": "Public real PDFs via online API",
        "matcher": lambda case_id: case_id.startswith("public_"),
        "interpretation": "Official public PDF evidence for real-world formatting and text/table evidence gates.",
    },
]


def main() -> None:
    evaluation = json.loads(EVALUATION_PATH.read_text(encoding="utf-8"))
    stability = json.loads(STABILITY_PATH.read_text(encoding="utf-8"))
    report = build_report(evaluation, stability)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "baseline_comparison.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "baseline_comparison.md").write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"out_dir": display_path(OUT_DIR), "groups": len(report["groups"])}, ensure_ascii=False))


def build_report(evaluation: dict[str, Any], stability: dict[str, Any]) -> dict[str, Any]:
    stability_by_id = {item["id"]: item for item in stability.get("cases", []) if isinstance(item, dict) and item.get("id")}
    groups = []
    covered: set[str] = set()
    for group in GROUPS:
        cases = [
            item
            for item in evaluation.get("cases", [])
            if isinstance(item, dict) and group["matcher"](str(item.get("id", "")))
        ]
        covered.update(str(item.get("id")) for item in cases)
        groups.append(summarize_group(group, cases, stability_by_id))
    remaining = [
        item
        for item in evaluation.get("cases", [])
        if isinstance(item, dict) and str(item.get("id")) not in covered
    ]
    if remaining:
        groups.append(
            summarize_group(
                {
                    "id": "other",
                    "name": "Other saved artifacts",
                    "interpretation": "Cases not covered by the predefined comparison groups.",
                },
                remaining,
                stability_by_id,
            )
        )
    return {
        "schema_version": "2026-05-24",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "scope": (
            "Saved-artifact cost/speed/quality comparison across runner families and scenario groups. "
            "This is not a third-party OCR benchmark."
        ),
        "source_reports": {
            "evaluation": display_path(EVALUATION_PATH),
            "stability": display_path(STABILITY_PATH),
        },
        "overall": {
            "cases": evaluation.get("case_count"),
            "field_accuracy": evaluation.get("aggregate", {}).get("field_accuracy"),
            "text_evidence_accuracy": evaluation.get("aggregate", {}).get("text_evidence_accuracy"),
            "numeric_evidence_accuracy": evaluation.get("aggregate", {}).get("numeric_evidence_accuracy"),
            "table_evidence_accuracy": evaluation.get("aggregate", {}).get("table_evidence_accuracy"),
            "total_tool_elapsed_seconds": stability.get("total_tool_elapsed_seconds"),
            "recovery_executed_cases": stability.get("recovery_executed_cases"),
            "provenance_level_counts": stability.get("provenance_level_counts"),
        },
        "groups": groups,
        "boundary": [
            "Accuracy is computed from lightweight human labels, not full OCR character error rate.",
            "Tool elapsed time is read from saved trace tool calls; native parsers can show zero external-tool seconds.",
            "The comparison helps reviewers see tradeoffs between cheap native parsing, MinerU CLI provenance, online API PDFs, and recovery paths.",
            "A stronger future benchmark should add external baselines such as raw OCR, raw MinerU-only output, and direct LLM extraction on the same hidden label set.",
        ],
    }


def summarize_group(
    group: dict[str, Any],
    cases: list[dict[str, Any]],
    stability_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    totals: dict[str, float] = defaultdict(float)
    quality_scores = []
    tool_seconds = []
    steps = []
    provenance_counts: dict[str, int] = defaultdict(int)
    recovery_executed = 0
    tool_counts: dict[str, int] = defaultdict(int)
    case_rows = []
    for case in cases:
        case_id = str(case.get("id"))
        stable = stability_by_id.get(case_id, {})
        for key in ("fields", "text_evidence", "numeric_evidence", "table_evidence"):
            matched_key = f"matched_{key}"
            expected_key = f"expected_{key}"
            totals[matched_key] += float(case.get(matched_key, 0) or 0)
            totals[expected_key] += float(case.get(expected_key, 0) or 0)
        quality_score = stable.get("quality_score")
        if isinstance(quality_score, (int, float)):
            quality_scores.append(float(quality_score))
        tool_elapsed = float(stable.get("tool_elapsed_seconds") or 0)
        tool_seconds.append(tool_elapsed)
        steps.append(int(stable.get("step_count") or 0))
        provenance = str(stable.get("provenance_level") or "unknown")
        provenance_counts[provenance] += 1
        if stable.get("recovery_executed"):
            recovery_executed += 1
        for tool in stable.get("tools", []) if isinstance(stable.get("tools"), list) else []:
            tool_counts[str(tool)] += 1
        case_rows.append(
            {
                "id": case_id,
                "profile": case.get("profile"),
                "checks_passed": checks_passed(case),
                "checks_total": checks_total(case),
                "quality_score": quality_score,
                "provenance_level": provenance,
                "tool_elapsed_seconds": round(tool_elapsed, 3),
                "recovery_executed": bool(stable.get("recovery_executed")),
            }
        )
    total_checks = checks_total_from_totals(totals)
    passed_checks = checks_passed_from_totals(totals)
    return {
        "id": group["id"],
        "name": group["name"],
        "interpretation": group["interpretation"],
        "case_count": len(cases),
        "checks_passed": passed_checks,
        "checks_total": total_checks,
        "labeled_check_accuracy": passed_checks / total_checks if total_checks else 1.0,
        "field_accuracy": ratio(totals["matched_fields"], totals["expected_fields"]),
        "text_evidence_accuracy": ratio(totals["matched_text_evidence"], totals["expected_text_evidence"]),
        "numeric_evidence_accuracy": ratio(totals["matched_numeric_evidence"], totals["expected_numeric_evidence"]),
        "table_evidence_accuracy": ratio(totals["matched_table_evidence"], totals["expected_table_evidence"]),
        "average_quality_score": round(sum(quality_scores) / len(quality_scores), 2) if quality_scores else None,
        "total_tool_elapsed_seconds": round(sum(tool_seconds), 3),
        "average_tool_elapsed_seconds": round(sum(tool_seconds) / len(tool_seconds), 3) if tool_seconds else 0.0,
        "average_trace_steps": round(sum(steps) / len(steps), 2) if steps else 0.0,
        "page_provenance_cases": provenance_counts.get("page", 0),
        "document_provenance_cases": provenance_counts.get("document", 0),
        "recovery_executed_cases": recovery_executed,
        "tool_counts": dict(sorted(tool_counts.items())),
        "cases": case_rows,
    }


def checks_passed(case: dict[str, Any]) -> int:
    return int(case.get("matched_fields", 0) or 0) + int(case.get("matched_text_evidence", 0) or 0) + int(
        case.get("matched_numeric_evidence", 0) or 0
    ) + int(case.get("matched_table_evidence", 0) or 0)


def checks_total(case: dict[str, Any]) -> int:
    return int(case.get("expected_fields", 0) or 0) + int(case.get("expected_text_evidence", 0) or 0) + int(
        case.get("expected_numeric_evidence", 0) or 0
    ) + int(case.get("expected_table_evidence", 0) or 0)


def checks_passed_from_totals(totals: dict[str, float]) -> int:
    return int(
        totals["matched_fields"]
        + totals["matched_text_evidence"]
        + totals["matched_numeric_evidence"]
        + totals["matched_table_evidence"]
    )


def checks_total_from_totals(totals: dict[str, float]) -> int:
    return int(
        totals["expected_fields"]
        + totals["expected_text_evidence"]
        + totals["expected_numeric_evidence"]
        + totals["expected_table_evidence"]
    )


def ratio(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Baseline and Tradeoff Comparison",
        "",
        report["scope"],
        "",
        "## Overall",
        "",
        f"- Cases: {report['overall']['cases']}",
        f"- Field accuracy: {pct(report['overall']['field_accuracy'])}",
        f"- Text evidence accuracy: {pct(report['overall']['text_evidence_accuracy'])}",
        f"- Numeric evidence accuracy: {pct(report['overall']['numeric_evidence_accuracy'])}",
        f"- Table evidence accuracy: {pct(report['overall']['table_evidence_accuracy'])}",
        f"- Total tool elapsed seconds: {report['overall']['total_tool_elapsed_seconds']}",
        f"- Recovery executed cases: {report['overall']['recovery_executed_cases']}",
        f"- Provenance distribution: `{json.dumps(report['overall']['provenance_level_counts'], ensure_ascii=False)}`",
        "",
        "## Group Comparison",
        "",
        "| Group | Cases | Labeled Checks | Accuracy | Avg Quality | Tool Seconds | Avg Steps | Page Prov. | Recovery |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for group in report["groups"]:
        lines.append(
            "| {name} | {cases} | {passed}/{total} | {accuracy} | {quality} | {tool_seconds} | {steps} | {page}/{cases} | {recovery}/{cases} |".format(
                name=group["name"],
                cases=group["case_count"],
                passed=group["checks_passed"],
                total=group["checks_total"],
                accuracy=pct(group["labeled_check_accuracy"]),
                quality=group["average_quality_score"],
                tool_seconds=group["total_tool_elapsed_seconds"],
                steps=group["average_trace_steps"],
                page=group["page_provenance_cases"],
                recovery=group["recovery_executed_cases"],
            )
        )
    lines.extend(["", "## Reviewer Reading", ""])
    for group in report["groups"]:
        lines.append(f"- {group['name']}: {group['interpretation']}")
    lines.extend(["", "## Boundary", ""])
    lines.extend(f"- {item}" for item in report["boundary"])
    lines.append("")
    return "\n".join(lines)


def pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.1f}%"


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


if __name__ == "__main__":
    main()
