from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = PROJECT_ROOT / "submission_artifacts"
OUT_DIR = ARTIFACT_ROOT / "llm_cost"


def main() -> None:
    report = build_report()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "llm_cost_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "llm_cost_report.md").write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"out_dir": display_path(OUT_DIR), "llm_cases": report["aggregate"]["llm_enabled_results"]}))


def build_report() -> dict[str, Any]:
    result_rows = []
    trace_rows = []
    for path in sorted(ARTIFACT_ROOT.rglob("result.json")):
        result = load_json(path)
        if not isinstance(result, dict):
            continue
        llm_analysis = result.get("llm_analysis", {})
        if not isinstance(llm_analysis, dict) or not llm_analysis.get("enabled"):
            continue
        result_rows.append(summarize_result(path, result, llm_analysis))
    for path in sorted(ARTIFACT_ROOT.rglob("trace.json")):
        trace = load_json(path)
        if not isinstance(trace, dict):
            continue
        calls = trace.get("tool_calls", [])
        if not isinstance(calls, list):
            continue
        for call in calls:
            if isinstance(call, dict) and "llm" in str(call.get("tool", "")).lower():
                trace_rows.append(summarize_tool_call(path, call))
    return {
        "schema_version": "2026-05-24",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "scope": "LLM token and cost audit over saved submission artifacts.",
        "aggregate": aggregate(result_rows, trace_rows),
        "results": result_rows,
        "trace_tool_calls": trace_rows,
        "pricing_configuration": {
            "provider_specific": [
                "MINERU_DATA_AGENT_DEEPSEEK_INPUT_USD_PER_MILLION_TOKENS",
                "MINERU_DATA_AGENT_DEEPSEEK_OUTPUT_USD_PER_MILLION_TOKENS",
                "MINERU_DATA_AGENT_MODELSCOPE_INPUT_USD_PER_MILLION_TOKENS",
                "MINERU_DATA_AGENT_MODELSCOPE_OUTPUT_USD_PER_MILLION_TOKENS",
            ],
            "generic": [
                "MINERU_DATA_AGENT_LLM_INPUT_USD_PER_MILLION_TOKENS",
                "MINERU_DATA_AGENT_LLM_OUTPUT_USD_PER_MILLION_TOKENS",
            ],
        },
        "boundary": [
            "New LLM runs record provider-returned token usage when the OpenAI-compatible API includes a usage object.",
            "Cost is computed only when token prices are configured through environment variables.",
            "Older saved LLM artifacts may show enabled LLM execution but missing token usage because they were generated before this instrumentation existed.",
            "This report does not claim a live DeepSeek/ModelScope cost benchmark unless saved artifacts contain provider usage.",
        ],
    }


def summarize_result(path: Path, result: dict[str, Any], llm_analysis: dict[str, Any]) -> dict[str, Any]:
    usage_summary = llm_analysis.get("usage_summary") if isinstance(llm_analysis.get("usage_summary"), dict) else {}
    preplan = llm_analysis.get("pre_execution_plan") if isinstance(llm_analysis.get("pre_execution_plan"), dict) else {}
    post = llm_analysis.get("post_parse_analysis") if isinstance(llm_analysis.get("post_parse_analysis"), dict) else {}
    usage_items = [
        item.get("llm_usage")
        for item in (preplan, post)
        if isinstance(item, dict) and isinstance(item.get("llm_usage"), dict)
    ]
    return {
        "result_path": display_path(path),
        "run_id": result.get("run_id"),
        "profile": result.get("profile"),
        "status": llm_analysis.get("status", "completed"),
        "usage_summary": usage_summary,
        "usage_item_count": len(usage_items),
        "has_token_usage": any(has_token_usage(item) for item in usage_items),
        "has_cost_estimate": bool(usage_summary.get("estimated_cost_usd") is not None),
        "providers": usage_summary.get("providers", []),
    }


def summarize_tool_call(path: Path, call: dict[str, Any]) -> dict[str, Any]:
    metadata = call.get("metadata") if isinstance(call.get("metadata"), dict) else {}
    usage_payload = metadata.get("llm_usage") if isinstance(metadata.get("llm_usage"), dict) else {}
    usage = usage_payload.get("usage") if isinstance(usage_payload.get("usage"), dict) else {}
    cost = usage_payload.get("cost_estimate") if isinstance(usage_payload.get("cost_estimate"), dict) else {}
    return {
        "trace_path": display_path(path),
        "tool": call.get("tool"),
        "status": call.get("status"),
        "elapsed_seconds": call.get("elapsed_seconds"),
        "provider": usage_payload.get("provider"),
        "model": usage_payload.get("model"),
        "prompt_tokens": int(usage.get("prompt_tokens") or 0),
        "completion_tokens": int(usage.get("completion_tokens") or 0),
        "total_tokens": int(usage.get("total_tokens") or 0),
        "cost_configured": bool(cost.get("configured")),
        "estimated_cost_usd": cost.get("estimated_cost"),
    }


def aggregate(result_rows: list[dict[str, Any]], trace_rows: list[dict[str, Any]]) -> dict[str, Any]:
    total_tokens = sum(int(row.get("total_tokens") or 0) for row in trace_rows)
    prompt_tokens = sum(int(row.get("prompt_tokens") or 0) for row in trace_rows)
    completion_tokens = sum(int(row.get("completion_tokens") or 0) for row in trace_rows)
    costs = [float(row["estimated_cost_usd"]) for row in trace_rows if row.get("estimated_cost_usd") is not None]
    return {
        "llm_enabled_results": len(result_rows),
        "llm_trace_tool_calls": len(trace_rows),
        "tool_calls_with_token_usage": sum(1 for row in trace_rows if int(row.get("total_tokens") or 0) > 0),
        "results_with_token_usage": sum(1 for row in result_rows if row.get("has_token_usage")),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "cost_configured_tool_calls": len(costs),
        "estimated_cost_usd": round(sum(costs), 8) if costs else None,
    }


def has_token_usage(item: Any) -> bool:
    if not isinstance(item, dict):
        return False
    usage = item.get("usage") if isinstance(item.get("usage"), dict) else {}
    return int(usage.get("total_tokens") or 0) > 0


def render_markdown(report: dict[str, Any]) -> str:
    aggregate_data = report["aggregate"]
    lines = [
        "# LLM Cost Report",
        "",
        report["scope"],
        "",
        "## Aggregate",
        "",
        f"- LLM-enabled results: {aggregate_data['llm_enabled_results']}",
        f"- LLM trace tool calls: {aggregate_data['llm_trace_tool_calls']}",
        f"- Tool calls with token usage: {aggregate_data['tool_calls_with_token_usage']}",
        f"- Results with token usage: {aggregate_data['results_with_token_usage']}",
        f"- Prompt tokens: {aggregate_data['prompt_tokens']}",
        f"- Completion tokens: {aggregate_data['completion_tokens']}",
        f"- Total tokens: {aggregate_data['total_tokens']}",
        f"- Cost-configured tool calls: {aggregate_data['cost_configured_tool_calls']}",
        f"- Estimated cost USD: {aggregate_data['estimated_cost_usd']}",
        "",
        "## LLM Results",
        "",
        "| Result | Status | Usage Items | Has Tokens | Has Cost |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for row in report["results"]:
        lines.append(
            "| {path} | {status} | {items} | {tokens} | {cost} |".format(
                path=row["result_path"],
                status=row["status"],
                items=row["usage_item_count"],
                tokens="yes" if row["has_token_usage"] else "no",
                cost="yes" if row["has_cost_estimate"] else "no",
            )
        )
    lines.extend(["", "## LLM Tool Calls", ""])
    lines.extend(
        [
            "| Trace | Tool | Status | Tokens | Cost USD |",
            "| --- | --- | --- | ---: | ---: |",
        ]
    )
    for row in report["trace_tool_calls"]:
        lines.append(
            "| {trace} | {tool} | {status} | {tokens} | {cost} |".format(
                trace=row["trace_path"],
                tool=row["tool"],
                status=row["status"],
                tokens=row["total_tokens"],
                cost=row["estimated_cost_usd"],
            )
        )
    lines.extend(["", "## Pricing Configuration", ""])
    lines.append("- Provider-specific env vars: " + ", ".join(f"`{item}`" for item in report["pricing_configuration"]["provider_specific"]))
    lines.append("- Generic env vars: " + ", ".join(f"`{item}`" for item in report["pricing_configuration"]["generic"]))
    lines.extend(["", "## Boundary", ""])
    lines.extend(f"- {item}" for item in report["boundary"])
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
