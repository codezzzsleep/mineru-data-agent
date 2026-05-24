from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = PROJECT_ROOT / "submission_artifacts"
OUT_DIR = ARTIFACT_ROOT / "llm_impact"


PAIRS = [
    {
        "id": "financial_html_llm_vs_rules",
        "baseline_result": ARTIFACT_ROOT / "cases" / "case_1_financial_report" / "result.json",
        "llm_result": ARTIFACT_ROOT / "llm_cases" / "case_llm_financial_review" / "result.json",
        "description": "Same financial HTML fixture family, comparing deterministic extraction with LLM preplanning/post-parse review.",
    }
]


def main() -> None:
    report = build_report()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "llm_impact_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "llm_impact_report.md").write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"out_dir": display_path(OUT_DIR), "pairs": len(report["pairs"])}, ensure_ascii=False))


def build_report() -> dict[str, Any]:
    pairs = []
    for pair in PAIRS:
        baseline = load_json(pair["baseline_result"])
        llm = load_json(pair["llm_result"])
        if not isinstance(baseline, dict) or not isinstance(llm, dict):
            pairs.append({"id": pair["id"], "status": "missing_artifact", "description": pair["description"]})
            continue
        pairs.append(compare_pair(pair, baseline, llm))
    return {
        "schema_version": "2026-05-24",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "scope": "Saved-artifact comparison of LLM-enabled runs against deterministic runs.",
        "aggregate": aggregate(pairs),
        "pairs": pairs,
        "rerun_plan": {
            "goal": "Use scripts/run_live_llm_matrix.py with a real provider key for a 5-case live rerun, then run the same manifest without LLM for a larger on/off comparison.",
            "metrics": [
                "quality status and score",
                "field precision/recall/F1",
                "trace steps and tool calls",
                "LLM applied/ignored recommendations",
                "token usage and estimated cost",
                "recovery decision changes",
            ],
            "current_live_matrix_manifest": "examples/llm_live_cases.json",
            "live_matrix_runbook": "docs/LIVE_LLM_RUNBOOK.md",
            "minimum_next_set": "10 cases: 4 financial, 2 noisy OCR, 2 contract/standard, 1 workflow, 1 long document chunk.",
        },
    }


def compare_pair(pair: dict[str, Any], baseline: dict[str, Any], llm: dict[str, Any]) -> dict[str, Any]:
    baseline_summary = summarize_result(pair["baseline_result"], baseline)
    llm_summary = summarize_result(pair["llm_result"], llm)
    llm_analysis = llm.get("llm_analysis", {}) if isinstance(llm.get("llm_analysis"), dict) else {}
    preplan = llm_analysis.get("pre_execution_plan", {}) if isinstance(llm_analysis.get("pre_execution_plan"), dict) else {}
    post = llm_analysis.get("post_parse_analysis", {}) if isinstance(llm_analysis.get("post_parse_analysis"), dict) else {}
    execution_control = llm.get("execution_control", {}) if isinstance(llm.get("execution_control"), dict) else {}
    applied = execution_control.get("applied", []) if isinstance(execution_control.get("applied"), list) else []
    ignored = execution_control.get("ignored", []) if isinstance(execution_control.get("ignored"), list) else []
    quality_decision = llm_analysis.get("quality_decision", {}) if isinstance(llm_analysis.get("quality_decision"), dict) else {}
    quality_decision_status = "present" if quality_decision else "not_present_in_saved_artifact"
    return {
        "id": pair["id"],
        "status": "compared",
        "description": pair["description"],
        "baseline": baseline_summary,
        "llm": llm_summary,
        "delta": {
            "quality_score": score_delta(llm_summary, baseline_summary),
            "trace_steps": llm_summary["trace_steps"] - baseline_summary["trace_steps"],
            "tool_calls": llm_summary["tool_calls"] - baseline_summary["tool_calls"],
            "target_schema_fields": len(preplan.get("target_schema", {})) if isinstance(preplan.get("target_schema"), dict) else 0,
            "verification_focus_items": len(preplan.get("verification_focus", [])) if isinstance(preplan.get("verification_focus"), list) else 0,
            "risk_findings": len(post.get("risk_findings", [])) if isinstance(post.get("risk_findings"), list) else 0,
            "recovery_suggestions": len(post.get("recovery_suggestions", [])) if isinstance(post.get("recovery_suggestions"), list) else 0,
            "applied_controls": len(applied),
            "ignored_controls": len(ignored),
        },
        "llm_decision_points": {
            "pre_execution_plan_status": preplan.get("status"),
            "recommended_profile": preplan.get("recommended_profile"),
            "recommended_runner": preplan.get("recommended_runner"),
            "recommended_backend": preplan.get("recommended_backend"),
            "recommended_method": preplan.get("recommended_method"),
            "recommended_lang": preplan.get("recommended_lang"),
            "applied": applied,
            "ignored": ignored,
            "post_parse_status": post.get("status"),
            "quality_decision": quality_decision,
            "quality_decision_status": quality_decision_status,
            "usage_summary": llm_analysis.get("usage_summary", {}),
        },
    }


def summarize_result(path: Path, result: dict[str, Any]) -> dict[str, Any]:
    trace = load_json(resolve_trace_path(result, path))
    if not isinstance(trace, dict):
        trace = {}
    extracted = result.get("extracted", {}) if isinstance(result.get("extracted"), dict) else {}
    quality = result.get("quality", {}) if isinstance(result.get("quality"), dict) else {}
    recovery = result.get("recovery_decision", {}) if isinstance(result.get("recovery_decision"), dict) else {}
    summary = extracted.get("content_summary", {}) if isinstance(extracted.get("content_summary"), dict) else {}
    llm_analysis = result.get("llm_analysis", {}) if isinstance(result.get("llm_analysis"), dict) else {}
    return {
        "path": display_path(path),
        "profile": result.get("profile"),
        "quality_status": quality.get("status"),
        "quality_score": quality.get("score"),
        "field_evidence_count": len(extracted.get("field_evidence", [])) if isinstance(extracted.get("field_evidence"), list) else 0,
        "tables": len(extracted.get("tables", [])) if isinstance(extracted.get("tables"), list) else 0,
        "key_values": len(extracted.get("key_values", [])) if isinstance(extracted.get("key_values"), list) else 0,
        "numeric_facts": len(extracted.get("numeric_facts", [])) if isinstance(extracted.get("numeric_facts"), list) else 0,
        "provenance_level": summary.get("provenance_level"),
        "trace_steps": len(trace.get("steps", [])) if isinstance(trace.get("steps"), list) else 0,
        "tool_calls": len(trace.get("tool_calls", [])) if isinstance(trace.get("tool_calls"), list) else 0,
        "recovery_decision": recovery.get("decision"),
        "llm_enabled": bool(llm_analysis.get("enabled")),
    }


def aggregate(pairs: list[dict[str, Any]]) -> dict[str, Any]:
    compared = [item for item in pairs if item.get("status") == "compared"]
    return {
        "compared_pairs": len(compared),
        "llm_enabled_pairs": sum(1 for item in compared if item.get("llm", {}).get("llm_enabled")),
        "pairs_with_applied_controls": sum(1 for item in compared if item.get("delta", {}).get("applied_controls", 0) > 0),
        "pairs_with_recovery_suggestions": sum(1 for item in compared if item.get("delta", {}).get("recovery_suggestions", 0) > 0),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# LLM Impact Report",
        "",
        report["scope"],
        "",
        "## Aggregate",
        "",
    ]
    for key, value in report["aggregate"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Compared Pairs",
            "",
            "| Pair | Baseline quality | LLM quality | Applied controls | Recovery suggestions | Tokens |",
            "| --- | --- | --- | ---: | ---: | ---: |",
        ]
    )
    for pair in report["pairs"]:
        if pair.get("status") != "compared":
            lines.append(f"| {pair.get('id')} | missing | missing | 0 | 0 | 0 |")
            continue
        usage = pair["llm_decision_points"].get("usage_summary", {})
        lines.append(
            "| {id} | {bq} ({bs}) | {lq} ({ls}) | {applied} | {suggestions} | {tokens} |".format(
                id=pair["id"],
                bq=pair["baseline"]["quality_status"],
                bs=pair["baseline"]["quality_score"],
                lq=pair["llm"]["quality_status"],
                ls=pair["llm"]["quality_score"],
                applied=pair["delta"]["applied_controls"],
                suggestions=pair["delta"]["recovery_suggestions"],
                tokens=usage.get("total_tokens", 0) if isinstance(usage, dict) else 0,
            )
        )
    lines.extend(["", "## Decision Details", ""])
    for pair in report["pairs"]:
        if pair.get("status") != "compared":
            continue
        lines.append(f"### {pair['id']}")
        lines.append("")
        lines.append(f"- Baseline: `{pair['baseline']['path']}`")
        lines.append(f"- LLM: `{pair['llm']['path']}`")
        lines.append(f"- Recommended profile: `{pair['llm_decision_points'].get('recommended_profile')}`")
        lines.append(f"- Recommended runner: `{pair['llm_decision_points'].get('recommended_runner')}`")
        lines.append(f"- Recommended method: `{pair['llm_decision_points'].get('recommended_method')}`")
        lines.append(f"- Quality decision status: `{pair['llm_decision_points'].get('quality_decision_status')}`")
        lines.append(f"- Quality decision: `{json.dumps(pair['llm_decision_points'].get('quality_decision', {}), ensure_ascii=False)}`")
        lines.append("")
    lines.extend(["## Rerun Plan", ""])
    rerun = report["rerun_plan"]
    lines.append(rerun["goal"])
    lines.append("")
    lines.append("Metrics:")
    lines.extend(f"- {item}" for item in rerun["metrics"])
    lines.append("")
    lines.append(f"Minimum next set: {rerun['minimum_next_set']}")
    lines.append("")
    return "\n".join(lines)


def score_delta(llm_summary: dict[str, Any], baseline_summary: dict[str, Any]) -> float | None:
    if not isinstance(llm_summary.get("quality_score"), (int, float)):
        return None
    if not isinstance(baseline_summary.get("quality_score"), (int, float)):
        return None
    return float(llm_summary["quality_score"]) - float(baseline_summary["quality_score"])


def resolve_trace_path(result: dict[str, Any], result_path: Path) -> Path:
    raw = result.get("trace_path")
    if raw:
        path = Path(str(raw).replace("<PROJECT_ROOT>", str(PROJECT_ROOT)))
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        if path.exists():
            return path
    return result_path.with_name("trace.json")


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
