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
    ("cases", "HTML/网页 fixture", "HTML 原生路径，用于检查规划、抽取、trace、恢复和 retrieval 导出。"),
    ("mineru_cases", "MinerU CLI PDF", "本地 MinerU CLI PDF 运行证据，包含页级 provenance 和 middle/layout/model artifact。"),
    ("agent_api_cases", "MinerU 在线 Agent API PDF", "CPU 环境友好的在线 API PDF 运行证据，输出轻量 Markdown。"),
    ("recovery_cases", "恢复案例", "API-to-CLI fallback 和恢复尝试证据。"),
    ("failure_recovery_cases", "失败/恢复注入案例", "controlled 负样本和恢复样本，覆盖 retry、严格 provenance 和数字不一致路径。"),
    ("office_cases", "Office 文件案例", "DOCX/PPTX 原生解析运行证据。"),
    ("challenge_cases", "挑战样本", "跨页表格、OCR 噪声、标准矩阵和故障工作流 fixture。"),
    ("adaptive_cases", "自适应规划案例", "同一输入在不同自然语言任务下的任务特定结果。"),
    ("agent_decision_cases", "Agent 决策回归", "离线任务拆解、工具选择、质量后重规划和 scripted decision-hook schema 检查。"),
    ("memory_cases", "跨运行记忆", "controlled 本地 SQLite 恢复记忆案例，展示后续运行可读取历史恢复结果。"),
    ("public_real_cases", "官方公开真实 PDF", "IRS、NIST、SEC、CDC 公开 PDF 案例，附轻量标签。"),
    ("long_document_chunks", "长文档分片", "NIST AI RMF 跨在线 API 页数上限的 page-range 分片证据。"),
    ("llm_cases", "LLM 案例", "OpenAI-compatible LLM 预调度和解析后复核结果。"),
    ("agent_live_cases", "Live LLM Agent trace", "真实 OpenAI-compatible tool-calling trace；finalize completion 和 answer-quality pass 分开统计。"),
    ("evaluation", "评测指标", "保存的标签检查和字段 precision/recall/F1。"),
    ("stability", "稳定性报告", "trace、工具耗时、质量、provenance 和 recovery 聚合。"),
    ("api_smoke", "可选 API 冒烟", "二级 HTTP wrapper 的 health、同步 parse 和 PDF smoke 结果。"),
    ("api_load_smoke", "可选 API 并发 smoke", "二级本地 FastAPI TestClient 并发结果。"),
    ("http_load_test", "可选 HTTP 压测", "二级本地 TCP loopback 同步/异步 API 压测，保留 request artifact。"),
    ("http_load_test_100", "可选 HTTP 100 请求压测", "二级 100 请求本地 TCP loopback 同步/异步 API 压测。"),
    ("baseline_comparison", "成本/速度/质量对比", "按 runner/scenario group 汇总保存 artifact 的成本、速度和质量。"),
    ("agent_value", "Agent 增值报告", "统计 Agent 层相对 parser artifact 增加的 schema、审计、恢复、retrieval 和决策模式字段。"),
    ("cost_model", "成本模型", "native、CLI、在线 API 和 LLM 模式的价格参数化成本估算。"),
    ("llm_cost", "LLM 成本", "Provider token 用量和可选价格估算。"),
    ("llm_impact", "LLM 影响对比", "开启/关闭 LLM 的保存 artifact 对比。"),
    ("recovery_effectiveness", "恢复有效性", "保存的 recovery attempts、selected attempts、issue codes 和额外工具耗时。"),
    ("long_document_risk", "长文档风险", "已保存长文档分片在线 API 运行的已知风险和缓解措施。"),
    ("retrieval_validation", "Retrieval 校验", "chunk schema、去重、密度和 lexical label-query smoke。"),
    ("code_quality", "代码质量", "仓库规模、测试、模块和 CI workflow 摘要。"),
    ("coverage", "覆盖率", "本地 pytest 的 coverage.py 行覆盖率。"),
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
        "# 提交证据总索引",
        "",
        "本文件是保存提交证据的统一导航页，便于评委快速定位每类 artifact、result/trace 数量和主报告。",
        "",
        "## 快速指标",
        "",
    ]
    for key, value in report["quick_metrics"].items():
        lines.append(f"- `{key}`: `{json.dumps(value, ensure_ascii=False)}`")
    lines.extend(
        [
            "",
            "## 证据目录",
            "",
            "| 类别 | 路径 | Result JSON | Trace JSON | 主要报告 |",
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
    lines.extend(["", "## 说明", ""])
    lines.append("- `result.json` 是机器可读的结构化输出。")
    lines.append("- `trace.json` 是包含步骤、工具、耗时和错误信息的执行日志。")
    lines.append("- 报告文件用于总结已保存 artifact，不替代在目标环境中重新运行脚本。")
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
