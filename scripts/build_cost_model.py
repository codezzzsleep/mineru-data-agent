from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = PROJECT_ROOT / "submission_artifacts"
OUT_DIR = ARTIFACT_ROOT / "cost_model"


def main() -> None:
    report = build_report()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "cost_model.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "cost_model.md").write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"out_dir": display_path(OUT_DIR), "scenarios": len(report["scenarios"])}, ensure_ascii=False))


def build_report() -> dict[str, Any]:
    baseline = load_json(ARTIFACT_ROOT / "baseline_comparison" / "baseline_comparison.json")
    llm_cost = load_json(ARTIFACT_ROOT / "llm_cost" / "llm_cost_report.json")
    groups = baseline.get("groups", []) if isinstance(baseline, dict) else []
    llm_aggregate = llm_cost.get("aggregate", {}) if isinstance(llm_cost, dict) else {}
    pricing = read_pricing()
    scenarios = [
        native_text_like_scenario(groups),
        mineru_cli_scenario(groups, pricing),
        public_api_scenario(groups, pricing),
        llm_scenario(llm_aggregate, pricing),
    ]
    return {
        "schema_version": "2026-05-24",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "scope": "Cost and latency projection from saved artifacts and optional price environment variables.",
        "pricing_inputs": pricing,
        "scenarios": scenarios,
        "decision_tree": [
            {
                "condition": "HTML, DOCX, PPTX, or trusted text-like input",
                "suggested_mode": "native extractor without LLM",
                "reason": "No external parser seconds in saved artifacts; enough for structure, field evidence, and retrieval export.",
            },
            {
                "condition": "PDF requiring page-level provenance or full MinerU artifacts",
                "suggested_mode": "local MinerU CLI",
                "reason": "Saved CLI PDF cases provide page provenance and intermediate artifacts, with higher runtime.",
            },
            {
                "condition": "CPU-only environment or quick PDF smoke",
                "suggested_mode": "MinerU online Agent API",
                "reason": "Runs without local GPU but can lack page provenance; fallback to CLI when audit requires it.",
            },
            {
                "condition": "Ambiguous task, custom schema, or high-risk review",
                "suggested_mode": "enable LLM preplanning and post-parse review",
                "reason": "Adds target schema, verification focus, and recovery suggestions; token cost should be tracked.",
            },
        ],
        "notes": [
            "Prices are not hard-coded because competition/cloud prices can change.",
            "Set the listed environment variables to turn formulas into currency estimates.",
            "Saved quality metrics are lightweight label checks, not full OCR or table-cell benchmarks.",
        ],
    }


def native_text_like_scenario(groups: list[dict[str, Any]]) -> dict[str, Any]:
    group = combine_groups(groups, ["html_native_fixtures", "office_native", "challenge_fixtures"])
    return {
        "id": "native_html_office_rules",
        "mode": "Native HTML/Office/challenge fixtures without LLM",
        "saved_cases": group.get("case_count", 0),
        "average_tool_seconds": group.get("average_tool_elapsed_seconds"),
        "labeled_check_accuracy": group.get("labeled_check_accuracy"),
        "estimated_cost_per_100_docs": {"currency": "CNY", "value": 0.0, "formula": "no external parser or LLM price"},
        "use_when": "Input is already text-like or Office-native and page-level PDF layout is not required.",
    }


def mineru_cli_scenario(groups: list[dict[str, Any]], pricing: dict[str, Any]) -> dict[str, Any]:
    group = find_group(groups, "mineru_cli_pdf")
    seconds = float(group.get("average_tool_elapsed_seconds") or 0)
    gpu_price = pricing.get("gpu_cny_per_hour")
    value = round(seconds * 100 * gpu_price / 3600, 4) if isinstance(gpu_price, (int, float)) else None
    return {
        "id": "mineru_cli_pdf",
        "mode": "Local MinerU CLI PDF",
        "saved_cases": group.get("case_count", 0),
        "average_tool_seconds": seconds,
        "labeled_check_accuracy": group.get("labeled_check_accuracy"),
        "estimated_cost_per_100_docs": {
            "currency": "CNY",
            "value": value,
            "formula": "average_tool_seconds * 100 * MINERU_DATA_AGENT_GPU_CNY_PER_HOUR / 3600",
        },
        "use_when": "PDF output needs page-level provenance, layout artifacts, or local audit trail.",
    }


def public_api_scenario(groups: list[dict[str, Any]], pricing: dict[str, Any]) -> dict[str, Any]:
    group = find_group(groups, "public_real_pdf")
    page_price = pricing.get("agent_api_cny_per_page")
    avg_pages = pricing.get("assumed_pages_per_pdf")
    value = round(100 * page_price * avg_pages, 4) if isinstance(page_price, (int, float)) and isinstance(avg_pages, (int, float)) else None
    return {
        "id": "online_agent_api_pdf",
        "mode": "MinerU online Agent API PDF",
        "saved_cases": group.get("case_count", 0),
        "average_tool_seconds": group.get("average_tool_elapsed_seconds"),
        "labeled_check_accuracy": group.get("labeled_check_accuracy"),
        "estimated_cost_per_100_docs": {
            "currency": "CNY",
            "value": value,
            "formula": "100 * MINERU_DATA_AGENT_AGENT_API_CNY_PER_PAGE * MINERU_DATA_AGENT_ASSUMED_PAGES_PER_PDF",
        },
        "use_when": "Need CPU-friendly PDF parsing and can accept online API page/provenance limitations.",
    }


def llm_scenario(llm_aggregate: dict[str, Any], pricing: dict[str, Any]) -> dict[str, Any]:
    tokens = int(llm_aggregate.get("total_tokens") or 0)
    results_with_tokens = int(llm_aggregate.get("results_with_token_usage") or 0)
    tokens_per_doc = tokens / results_with_tokens if results_with_tokens else 0
    price = pricing.get("llm_cny_per_million_tokens")
    value = round(tokens_per_doc * 100 * price / 1_000_000, 4) if isinstance(price, (int, float)) else None
    return {
        "id": "llm_preplan_review",
        "mode": "LLM preplanning and post-parse review",
        "saved_llm_results_with_tokens": results_with_tokens,
        "tokens_per_saved_doc": round(tokens_per_doc, 2),
        "estimated_cost_per_100_docs": {
            "currency": "CNY",
            "value": value,
            "formula": "tokens_per_saved_doc * 100 * MINERU_DATA_AGENT_LLM_CNY_PER_MILLION_TOKENS / 1_000_000",
        },
        "use_when": "Task is ambiguous, schema is custom, or the result needs post-parse risk review.",
    }


def read_pricing() -> dict[str, Any]:
    return {
        "gpu_cny_per_hour": read_float("MINERU_DATA_AGENT_GPU_CNY_PER_HOUR"),
        "agent_api_cny_per_page": read_float("MINERU_DATA_AGENT_AGENT_API_CNY_PER_PAGE"),
        "assumed_pages_per_pdf": read_float("MINERU_DATA_AGENT_ASSUMED_PAGES_PER_PDF") or 20,
        "llm_cny_per_million_tokens": read_float("MINERU_DATA_AGENT_LLM_CNY_PER_MILLION_TOKENS"),
        "env_vars": [
            "MINERU_DATA_AGENT_GPU_CNY_PER_HOUR",
            "MINERU_DATA_AGENT_AGENT_API_CNY_PER_PAGE",
            "MINERU_DATA_AGENT_ASSUMED_PAGES_PER_PDF",
            "MINERU_DATA_AGENT_LLM_CNY_PER_MILLION_TOKENS",
        ],
    }


def find_group(groups: list[dict[str, Any]], group_id: str) -> dict[str, Any]:
    for group in groups:
        if isinstance(group, dict) and group.get("id") == group_id:
            return group
    return {}


def combine_groups(groups: list[dict[str, Any]], group_ids: list[str]) -> dict[str, Any]:
    selected = [find_group(groups, group_id) for group_id in group_ids]
    selected = [group for group in selected if group]
    case_count = sum(int(group.get("case_count") or 0) for group in selected)
    total_seconds = sum(float(group.get("total_tool_elapsed_seconds") or 0) for group in selected)
    checks_passed = sum(int(group.get("checks_passed") or 0) for group in selected)
    checks_total = sum(int(group.get("checks_total") or 0) for group in selected)
    return {
        "case_count": case_count,
        "average_tool_elapsed_seconds": round(total_seconds / case_count, 3) if case_count else 0.0,
        "labeled_check_accuracy": checks_passed / checks_total if checks_total else None,
    }


def read_float(name: str) -> float | None:
    raw = os.getenv(name)
    if raw in (None, ""):
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    return value if value >= 0 else None


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Cost Model",
        "",
        report["scope"],
        "",
        "## Pricing Inputs",
        "",
    ]
    pricing = report["pricing_inputs"]
    for name in pricing["env_vars"]:
        key = name.replace("MINERU_DATA_AGENT_", "").lower()
        lines.append(f"- `{name}`: `{pricing.get(key)}`")
    lines.extend(
        [
            "",
            "## Scenarios",
            "",
            "| Scenario | Saved cases | Avg tool seconds | Labeled checks | Estimated CNY / 100 docs | Formula |",
            "| --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for item in report["scenarios"]:
        cost = item["estimated_cost_per_100_docs"]
        lines.append(
            "| {mode} | {cases} | {seconds} | {accuracy} | {cost} | `{formula}` |".format(
                mode=item["mode"],
                cases=item.get("saved_cases", item.get("saved_llm_results_with_tokens", "-")),
                seconds=item.get("average_tool_seconds", "-"),
                accuracy=item.get("labeled_check_accuracy", "-"),
                cost=cost.get("value"),
                formula=cost.get("formula"),
            )
        )
    lines.extend(["", "## Decision Tree", ""])
    for item in report["decision_tree"]:
        lines.append(f"- If {item['condition']}: use **{item['suggested_mode']}**. {item['reason']}")
    lines.extend(["", "## Notes", ""])
    lines.extend(f"- {item}" for item in report["notes"])
    lines.append("")
    return "\n".join(lines)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


if __name__ == "__main__":
    main()
