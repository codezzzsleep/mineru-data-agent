from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = PROJECT_ROOT / "submission_artifacts"
OUT_JSON = ARTIFACT_ROOT / "ARTIFACTS_INDEX.json"
OUT_MD = ARTIFACT_ROOT / "ARTIFACTS_INDEX.md"


CATEGORIES = [
    ("cases", "HTML/Web fixtures", "Native HTML path for planning, extraction, trace, recovery, and retrieval checks."),
    ("mineru_cases", "MinerU CLI PDFs", "Local MinerU CLI PDF runs with page provenance and middle/layout/model artifacts."),
    ("agent_api_cases", "MinerU Agent API PDF", "CPU-friendly online API PDF run with lightweight Markdown output."),
    ("recovery_cases", "Recovery", "API-to-CLI fallback and recovery attempt evidence."),
    ("failure_recovery_cases", "Failure/recovery fault injection", "Controlled negative and recovery cases for retry, strict provenance, and numeric mismatch paths."),
    ("office_cases", "Office files", "DOCX/PPTX native extraction runs."),
    ("challenge_cases", "Challenge fixtures", "Cross-page table, OCR noise, standard matrix, and incident workflow fixtures."),
    ("adaptive_cases", "Adaptive planning", "Same input with different natural-language tasks and task-specific results."),
    ("agent_decision_cases", "Agent decision regression", "Offline task decomposition, tool selection, quality replanning, and scripted decision-hook schema checks."),
    ("memory_cases", "Cross-run memory", "Controlled local SQLite recovery-memory case showing a later run can read prior recovery outcomes."),
    ("public_real_cases", "Public real PDFs", "IRS, NIST, SEC, and CDC public PDF cases with lightweight labels."),
    ("long_document_chunks", "Long document chunks", "NIST AI RMF page-range chunking across the online API page limit."),
    ("llm_cases", "LLM cases", "OpenAI-compatible LLM preplanning and post-parse review results."),
    ("agent_live_cases", "Live LLM agent traces", "Real OpenAI-compatible tool-calling traces; finalize completion and answer-quality pass are reported separately."),
    ("evaluation", "Evaluation metrics", "Saved label checks and field precision/recall/F1."),
    ("stability", "Stability report", "Trace, tool timing, quality, provenance, and recovery aggregation."),
    ("api_smoke", "Optional API smoke", "Secondary HTTP wrapper health, sync parse, and PDF smoke results."),
    ("api_load_smoke", "Optional API load smoke", "Secondary local FastAPI TestClient concurrency results."),
    ("http_load_test", "Optional HTTP load test", "Secondary local TCP loopback sync/async API load test with request artifacts."),
    ("http_load_test_100", "Optional HTTP load test 100", "Secondary 100-request local TCP loopback sync/async API load test."),
    ("baseline_comparison", "Tradeoff comparison", "Saved-artifact cost/speed/quality comparison by runner/scenario group."),
    ("agent_value", "Agent value report", "Saved-artifact report of Agent-layer schema, audit, recovery, retrieval, and decision-mode additions over parser artifacts."),
    ("cost_model", "Cost model", "Price-parameterized cost estimates for native, CLI, online API, and LLM modes."),
    ("llm_cost", "LLM cost", "Provider token usage and optional price-based cost estimate."),
    ("llm_impact", "LLM impact", "With/without LLM artifact comparison."),
    ("recovery_effectiveness", "Recovery effectiveness", "Saved recovery attempts, selected attempts, issue codes, and extra tool time."),
    ("long_document_risk", "Long-document risk", "Known risks and mitigations for the saved long-document chunked API run."),
    ("retrieval_validation", "Retrieval validation", "Chunk schema, de-duplication, density, and lexical label-query smoke checks."),
    ("code_quality", "Code quality", "Static repository size, tests, modules, and CI workflow summary."),
    ("coverage", "Coverage", "coverage.py line coverage for the local pytest suite."),
]


def main() -> None:
    report = build_report()
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_MD.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"index": display_path(OUT_MD), "categories": len(report["categories"])}, ensure_ascii=False))


def build_report() -> dict[str, Any]:
    categories = []
    for dirname, title, description in CATEGORIES:
        path = ARTIFACT_ROOT / dirname
        categories.append(summarize_category(path, title, description))
    return {
        "schema_version": "2026-05-24",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "root": display_path(ARTIFACT_ROOT),
        "quick_metrics": quick_metrics(),
        "categories": categories,
    }


def summarize_category(path: Path, title: str, description: str) -> dict[str, Any]:
    exists = path.exists()
    result_files = list(path.rglob("result.json")) if exists else []
    trace_files = list(path.rglob("trace.json")) if exists else []
    readmes = [item for item in path.rglob("README.md")] if exists else []
    reports = [
        item
        for item in path.rglob("*.md")
        if item.name.lower() != "readme.md" and "request_artifacts" not in item.parts
    ] if exists else []
    json_reports = [
        item
        for item in path.rglob("*.json")
        if item.name not in {"result.json", "trace.json"} and "request_artifacts" not in item.parts
    ] if exists else []
    return {
        "id": path.name,
        "title": title,
        "description": description,
        "path": display_path(path),
        "exists": exists,
        "result_files": len(result_files),
        "trace_files": len(trace_files),
        "readmes": [display_path(item) for item in sorted(readmes)[:8]],
        "reports": [display_path(item) for item in sorted(reports)[:12]],
        "json_reports": [display_path(item) for item in sorted(json_reports)[:12]],
    }


def quick_metrics() -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    evaluation = load_json(ARTIFACT_ROOT / "evaluation" / "evaluation_metrics.json")
    if isinstance(evaluation, dict):
        aggregate = evaluation.get("aggregate", {}) if isinstance(evaluation.get("aggregate"), dict) else {}
        metrics["evaluation"] = {
            "cases": evaluation.get("case_count"),
            "expected_fields": aggregate.get("expected_fields"),
            "field_precision": aggregate.get("field_precision"),
            "field_recall": aggregate.get("field_recall"),
            "field_f1": aggregate.get("field_f1"),
        }
    stability = load_json(ARTIFACT_ROOT / "stability" / "stability_report.json")
    if isinstance(stability, dict):
        metrics["stability"] = {
            "cases": stability.get("case_count"),
            "tool_calls": stability.get("total_tool_calls"),
            "tool_elapsed_seconds": stability.get("total_tool_elapsed_seconds"),
            "recovery_executed_cases": stability.get("recovery_executed_cases"),
        }
    http = load_json(ARTIFACT_ROOT / "http_load_test_100" / "http_load_test_report.json")
    if isinstance(http, dict):
        aggregate = http.get("aggregate", {}) if isinstance(http.get("aggregate"), dict) else http
        latency = aggregate.get("latency_seconds", {}) if isinstance(aggregate.get("latency_seconds"), dict) else {}
        metrics["http_load_test_100"] = {
            "requests": first_present(aggregate, "requests", "total_requests"),
            "success": first_present(aggregate, "success", "successful_requests"),
            "failed": first_present(aggregate, "failed", "failed_requests"),
            "p95_seconds": aggregate.get("p95_seconds") or aggregate.get("latency_p95_seconds") or latency.get("p95"),
        }
    llm_cost = load_json(ARTIFACT_ROOT / "llm_cost" / "llm_cost_report.json")
    if isinstance(llm_cost, dict):
        aggregate = llm_cost.get("aggregate", {}) if isinstance(llm_cost.get("aggregate"), dict) else {}
        metrics["llm_cost"] = {
            "llm_enabled_results": aggregate.get("llm_enabled_results"),
            "llm_trace_tool_calls": aggregate.get("llm_trace_tool_calls"),
            "total_tokens": aggregate.get("total_tokens"),
            "estimated_cost_usd": aggregate.get("estimated_cost_usd"),
        }
    agent_decision = load_json(ARTIFACT_ROOT / "agent_decision_cases" / "artifact_index.json")
    if isinstance(agent_decision, dict):
        cases = agent_decision.get("cases", []) if isinstance(agent_decision.get("cases"), list) else []
        metrics["agent_decision_cases"] = {
            "cases": len(cases),
            "selected_tool_names": sorted(
                {
                    str(tool)
                    for case in cases
                    if isinstance(case, dict)
                    for tool in case.get("selected_tools", [])
                }
            ),
            "boundary": agent_decision.get("boundary"),
        }
    llm_impact = load_json(ARTIFACT_ROOT / "llm_impact" / "llm_impact_report.json")
    if isinstance(llm_impact, dict):
        metrics["llm_impact"] = llm_impact.get("aggregate", {})
    live_agent = load_json(ARTIFACT_ROOT / "agent_live_cases" / "agent_live_report.json")
    if isinstance(live_agent, dict):
        summary = live_agent.get("summary", {}) if isinstance(live_agent.get("summary"), dict) else {}
        cases = live_agent.get("cases", []) if isinstance(live_agent.get("cases"), list) else []
        tool_completed = [
            item
            for item in cases
            if isinstance(item, dict)
            and (
                item.get("tool_call_completed") is True
                or item.get("live_evidence") is True
                or (
                    item.get("status") == "completed"
                    and int(item.get("tokens") or 0) > 0
                    and "finalize" in (item.get("tool_sequence") or [])
                )
            )
        ]
        metrics["agent_live_cases"] = {
            "provider": live_agent.get("provider"),
            "model": live_agent.get("model"),
            "evidence_generation": live_agent.get("evidence_generation"),
            "skill_gate_live_rerun_completed": live_agent.get("skill_gate_live_rerun_completed"),
            "total_cases": summary.get("total", len(cases)),
            "tool_call_completed_cases": summary.get("tool_call_completed_cases", len(tool_completed)),
            "tool_validated_cases": summary.get(
                "tool_validated_cases",
                sum(1 for item in tool_completed if item.get("answer_validation_ok") is True),
            ),
            "answer_quality_pass_cases": summary.get(
                "answer_quality_pass_cases",
                sum(1 for item in tool_completed if item.get("answer_quality_pass") is True),
            ),
            "answer_quality_questionable_cases": summary.get(
                "answer_quality_questionable_cases",
                sum(1 for item in tool_completed if item.get("answer_quality_pass") is False),
            ),
            "answer_quality_unreviewed_cases": summary.get(
                "answer_quality_unreviewed_cases",
                sum(1 for item in tool_completed if item.get("answer_quality_pass") is None),
            ),
            "live_evidence_cases": summary.get("live_evidence_cases", len(tool_completed)),
            "completed_status": sum(1 for item in cases if isinstance(item, dict) and item.get("status") == "completed"),
            "failed_or_incomplete": sum(1 for item in cases if isinstance(item, dict) and item.get("status") != "completed"),
            "total_tokens": summary.get(
                "total_tokens",
                sum(int(item.get("tokens") or 0) for item in cases if isinstance(item, dict)),
            ),
        }
    cost_model = load_json(ARTIFACT_ROOT / "cost_model" / "cost_model.json")
    if isinstance(cost_model, dict):
        tradeoff_table = cost_model.get("tradeoff_table", []) if isinstance(cost_model.get("tradeoff_table"), list) else []
        metrics["cost_model"] = {
            "scenarios": len(cost_model.get("scenarios", [])) or len(tradeoff_table),
            "pricing_inputs": cost_model.get("pricing_inputs") or cost_model.get("pricing_assumptions", {}),
            "live_evidence_available": cost_model.get("live_evidence_available"),
        }
    recovery = load_json(ARTIFACT_ROOT / "recovery_effectiveness" / "recovery_effectiveness_report.json")
    if isinstance(recovery, dict):
        metrics["recovery_effectiveness"] = recovery.get("aggregate", {})
    long_doc = load_json(ARTIFACT_ROOT / "long_document_risk" / "long_document_risk_report.json")
    if isinstance(long_doc, dict):
        metrics["long_document_risk"] = long_doc.get("aggregate", {})
    retrieval = load_json(ARTIFACT_ROOT / "retrieval_validation" / "retrieval_validation_report.json")
    if isinstance(retrieval, dict):
        aggregate = retrieval.get("aggregate", {}) if isinstance(retrieval.get("aggregate"), dict) else {}
        metrics["retrieval_validation"] = {
            "chunk_files": aggregate.get("chunk_files"),
            "total_chunks": aggregate.get("total_chunks"),
            "schema_error_count": aggregate.get("schema_error_count"),
            "duplicate_text_rate": aggregate.get("duplicate_text_rate"),
            "label_query_checks": aggregate.get("label_query_checks"),
        }
    agent_value = load_json(ARTIFACT_ROOT / "agent_value" / "agent_value_report.json")
    if isinstance(agent_value, dict):
        metrics["agent_value"] = agent_value.get("aggregate", {})
    code_quality = load_json(ARTIFACT_ROOT / "code_quality" / "code_quality_report.json")
    if isinstance(code_quality, dict):
        metrics["code_quality"] = code_quality.get("aggregate", {})
    coverage = load_json(ARTIFACT_ROOT / "coverage" / "coverage_report.json")
    if isinstance(coverage, dict):
        aggregate = coverage.get("aggregate", {}) if isinstance(coverage.get("aggregate"), dict) else {}
        metrics["coverage"] = {
            "measured": aggregate.get("measured"),
            "line_coverage_percent": aggregate.get("line_coverage_percent"),
            "num_statements": aggregate.get("num_statements"),
            "missing_lines": aggregate.get("missing_lines"),
        }
    return metrics


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Artifact Index",
        "",
        "This file is a single navigation page for saved submission artifacts.",
        "",
        "## Quick Metrics",
        "",
    ]
    for key, value in report["quick_metrics"].items():
        lines.append(f"- `{key}`: `{json.dumps(value, ensure_ascii=False)}`")
    lines.extend(
        [
            "",
            "## Directories",
            "",
            "| Area | Path | Result JSON | Trace JSON | Main reports |",
            "| --- | --- | ---: | ---: | --- |",
        ]
    )
    for item in report["categories"]:
        report_links = ", ".join(f"`{path}`" for path in item["reports"][:3])
        if not report_links and item["readmes"]:
            report_links = ", ".join(f"`{path}`" for path in item["readmes"][:2])
        if not report_links:
            report_links = "-"
        lines.append(
            f"| {item['title']} | `{item['path']}` | {item['result_files']} | {item['trace_files']} | {report_links} |"
        )
    lines.extend(["", "## Notes", ""])
    lines.append("- `result.json` is the machine-readable output.")
    lines.append("- `trace.json` is the execution log with steps, tools, elapsed time, and errors.")
    lines.append("- Report files summarize saved artifacts; they do not replace rerunning the scripts in a target environment.")
    lines.append("")
    return "\n".join(lines)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def first_present(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data:
            return data[key]
    return None


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


if __name__ == "__main__":
    main()
