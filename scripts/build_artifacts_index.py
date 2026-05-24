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
    ("office_cases", "Office files", "DOCX/PPTX native extraction runs."),
    ("challenge_cases", "Challenge fixtures", "Cross-page table, OCR noise, standard matrix, and incident workflow fixtures."),
    ("adaptive_cases", "Adaptive planning", "Same input with different natural-language tasks and task-specific results."),
    ("public_real_cases", "Public real PDFs", "IRS, NIST, SEC, and CDC public PDF cases with lightweight labels."),
    ("long_document_chunks", "Long document chunks", "NIST AI RMF page-range chunking across the online API page limit."),
    ("llm_cases", "LLM cases", "OpenAI-compatible LLM preplanning and post-parse review results."),
    ("evaluation", "Evaluation metrics", "Saved label checks and field precision/recall/F1."),
    ("stability", "Stability report", "Trace, tool timing, quality, provenance, and recovery aggregation."),
    ("api_smoke", "API smoke", "Health, sync parse, and PDF API smoke results."),
    ("api_load_smoke", "API load smoke", "Local FastAPI TestClient concurrency results."),
    ("http_load_test", "HTTP load test", "Local TCP loopback sync/async API load test with request artifacts."),
    ("http_load_test_100", "HTTP load test 100", "100-request local TCP loopback sync/async API load test."),
    ("baseline_comparison", "Tradeoff comparison", "Saved-artifact cost/speed/quality comparison by runner/scenario group."),
    ("llm_cost", "LLM cost", "Provider token usage and optional price-based cost estimate."),
    ("llm_impact", "LLM impact", "With/without LLM artifact comparison."),
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
    llm_impact = load_json(ARTIFACT_ROOT / "llm_impact" / "llm_impact_report.json")
    if isinstance(llm_impact, dict):
        metrics["llm_impact"] = llm_impact.get("aggregate", {})
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
