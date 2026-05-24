"""Live LLM Agent batch runner for the competition submission.

Defines 12 designed-to-be-hard candidate tasks against the live
OpenAI-compatible tool-calling loop in ``agent_live.py``. Reviewers may run all
cases or a subset with ``--only``. Each case is chosen to require behaviour
that the deterministic rule-based agent cannot do:

- Disambiguate task vs. document mismatch (Q3 vs Q1, missing year).
- Decide between multiple parsers based on file extension at runtime.
- Trigger ``clean_text`` recovery in response to a validator code.
- Cross-reference numeric facts against narrative claims.
- Decline gracefully ("not_found") when an answer is not in the document.
- Choose ``method=ocr`` for low-quality PDFs.

We pace requests because hosted providers can return 429 aggressively. Failed,
quota-limited, and answer-quality-questionable cases are retained in the report
and must not be cited as semantic successes.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mineru_data_agent.agent_live import run_live_agent


CASES = [
    {
        "id": "live_01_financial_total_check",
        "input": "examples/cases/case_1_financial_report.html",
        "task": "识别这份 HTML 财报中 2026Q1 的营业收入和利润总额，验证合计行是否与明细一致，列出任何异常",
        "difficulty": "数值核对：LLM 需自己做合计行减法验算",
    },
    {
        "id": "live_02_q3_mismatch_decline",
        "input": "examples/cases/case_1_financial_report.html",
        "task": "请告诉我这份财报中 2025Q3 的营业收入。如果文档不包含该季度数据，请明确说明 not_found 并给出文档实际包含的季度",
        "difficulty": "拒答测试：文档只有 Q1/Q4，LLM 必须不幻觉",
    },
    {
        "id": "live_03_low_quality_recovery",
        "input": "examples/cases/case_2_low_quality_ocr.html",
        "task": "解析这份低质量 OCR 巡检报告。如果发现编码噪声/乱码（锟斤拷之类），先调用 clean_text 恢复，然后再抽取设备 B-17 的异常温度信息",
        "difficulty": "Recovery：LLM 必须根据 validate_quality 的 issue_codes 触发 clean_text",
    },
    {
        "id": "live_04_contract_obligations",
        "input": "examples/cases/case_3_standard_contract.html",
        "task": "从这份合同中提取所有甲方/乙方的关键义务条款，并指出哪一条最可能引发争议（基于条款措辞）",
        "difficulty": "语义判断：LLM 需对条款做风险排序，规则做不到",
    },
    {
        "id": "live_05_workflow_anomaly_chain",
        "input": "examples/cases/case_4_workflow_diagram.html",
        "task": "梳理这份工艺流程的所有步骤，找出可能导致异常的关键节点，并按业务影响排序给出优先处理建议",
        "difficulty": "推理排序：要 LLM 主动做风险传播分析",
    },
    {
        "id": "live_06_web_inspection_kv",
        "input": "examples/cases/case_5_web_inspection_report.html",
        "task": "从这份网页巡检日报中抽取出所有键值对（指标名 → 当前值 → 阈值），用 markdown 表格输出，并标记超阈值项",
        "difficulty": "结构化抽取 + 阈值比较",
    },
    {
        "id": "live_07_cross_page_table",
        "input": "examples/challenge_cases/case_6_cross_page_financial_table.html",
        "task": "这份财报有跨页合并的表格。请抽取完整表格，并验证：跨页延续行是否被正确合并？合计是否跨页一致？",
        "difficulty": "跨页指代：要求 LLM 调用 query_extracted 多次定位",
    },
    {
        "id": "live_08_noisy_contract_scan",
        "input": "examples/challenge_cases/case_7_noisy_contract_scan.html",
        "task": "这是噪声扫描合同。提取签署日期、双方主体、争议解决条款；如果某项被签章遮挡或乱码无法识别，标注为 unreadable",
        "difficulty": "鲁棒性：必须区分 unreadable vs not_found vs found",
    },
    {
        "id": "live_09_industry_standard_matrix",
        "input": "examples/challenge_cases/case_8_industry_standard_matrix.html",
        "task": "提取行业标准合规矩阵：每一项控制要求 → 当前合规状态 → 风险等级。最后给出整份文档的整体合规结论（pass/fail/needs_review）",
        "difficulty": "聚合判断：LLM 必须基于多行做整体决策",
    },
    {
        "id": "live_10_incident_workflow",
        "input": "examples/challenge_cases/case_9_incident_workflow_report.html",
        "task": "重建这份故障工单的时间线（事件 → 时间 → 处理人 → 结果），找出处理链中是否存在 SLA 违约或责任空档",
        "difficulty": "时间线重建 + SLA 违规检测",
    },
    {
        "id": "live_11_docx_compliance_review",
        "input": "examples/office_files/industry_standard_review.docx",
        "task": "解析这份 Word 标准评审包，列出：评审章节标题、合规矩阵中标记为 fail 或 risk 的条目、整体建议",
        "difficulty": "Office 解析 + 选择性抽取",
    },
    {
        "id": "live_12_pptx_workflow_review",
        "input": "examples/office_files/workflow_agent_review.pptx",
        "task": "解析这份 PowerPoint 工作流汇报，按 slide 顺序列出：每页主题、每页提到的执行矩阵或风险条目，最后给出汇报核心结论",
        "difficulty": "PPT 多 slide 提取 + 摘要",
    },
]


def _display_path(path: str | Path) -> str:
    target = Path(path)
    try:
        return str(target.resolve().relative_to(ROOT)).replace("\\", "/")
    except Exception:
        return str(path)


def _tool_call_completed(record: dict) -> bool:
    value = record.get("tool_call_completed")
    if isinstance(value, bool):
        return value
    return (
        record.get("status") == "completed"
        and int(record.get("tokens") or 0) > 0
        and "finalize" in (record.get("tool_sequence") or [])
    )


def _answer_quality_pass(record: dict) -> bool:
    return record.get("answer_quality_pass") is True


def _is_live_evidence(record: dict) -> bool:
    return _tool_call_completed(record)


def run_one(case: dict, *, output_root: Path, sleep_between: float, args: argparse.Namespace) -> dict:
    started = time.perf_counter()
    record = {
        "id": case["id"],
        "input": case["input"],
        "task": case["task"],
        "difficulty": case["difficulty"],
        "status": None,
        "turns": 0,
        "tokens": 0,
        "duration_seconds": None,
        "tool_sequence": [],
        "final_answer_preview": None,
        "evidence_count": 0,
        "tool_call_completed": False,
        "answer_quality_pass": None,
        "answer_quality_note": None,
        "trace_path": None,
        "summary_path": None,
        "error": None,
    }
    try:
        trace = run_live_agent(
            input_file=case["input"],
            output_root=str(output_root),
            task=case["task"],
            provider=args.provider,
            model=args.model,
            base_url=args.base_url,
            max_turns=args.max_turns,
            max_tokens=args.max_tokens,
            timeout=args.timeout,
        )
        record["status"] = trace.status
        record["turns"] = len(trace.turns)
        record["tokens"] = trace.total_tokens
        record["tool_sequence"] = [
            t.tool_call["name"] for t in trace.turns if t.tool_call
        ]
        record["final_answer_preview"] = (trace.final_answer or "")[:600]
        record["evidence_count"] = len(trace.final_evidence)
        record["tool_call_completed"] = _tool_call_completed(record)
        record["live_evidence"] = record["tool_call_completed"]
        record["answer_quality_pass"] = None
        record["answer_quality_note"] = "not manually reviewed"
        record["trace_path"] = _display_path(Path(trace.output_dir) / "live_agent_trace.json")
        record["summary_path"] = _display_path(Path(trace.output_dir) / "live_agent_summary.md")
    except Exception as exc:  # noqa: BLE001
        record["status"] = "error"
        record["error"] = f"{type(exc).__name__}: {exc}"
        traceback.print_exc()
    record["duration_seconds"] = round(time.perf_counter() - started, 2)
    if sleep_between > 0:
        time.sleep(sleep_between)
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=("modelscope", "deepseek"), default="modelscope")
    parser.add_argument("--model", default=None)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--output-root", default="submission_artifacts/agent_live_cases")
    parser.add_argument("--sleep-between", type=float, default=2.0)
    parser.add_argument("--only", nargs="*", help="case ids to run; omit to run all")
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--reset-output", action="store_true")
    parser.add_argument("--max-turns", type=int, default=18)
    parser.add_argument("--max-tokens", type=int, default=1400)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--min-completed-rate", type=float, default=0.0)
    args = parser.parse_args()
    if not 0 <= args.min_completed_rate <= 1:
        parser.error("--min-completed-rate must be between 0 and 1")

    key_env = "MODELSCOPE_API_KEY" if args.provider == "modelscope" else "DEEPSEEK_API_KEY"
    if not os.getenv(key_env):
        print(f"ERROR: {key_env} not set", file=sys.stderr)
        return 2

    output_root = Path(args.output_root).resolve()
    if args.reset_output and output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    report_path = output_root / "agent_live_report.json"
    md_report_path = output_root / "agent_live_report.md"

    existing: dict[str, dict] = {}
    if args.skip_existing and report_path.exists():
        try:
            existing = {r["id"]: r for r in json.loads(report_path.read_text(encoding="utf-8")).get("cases", [])}
        except Exception:  # noqa: BLE001
            existing = {}

    if args.only:
        known = {case["id"] for case in CASES}
        missing = sorted(set(args.only) - known)
        if missing:
            parser.error(f"unknown case id(s): {', '.join(missing)}")
        selected = [c for c in CASES if c["id"] in set(args.only)]
    else:
        selected = CASES

    results = []
    for i, case in enumerate(selected, 1):
        if args.skip_existing and case["id"] in existing and existing[case["id"]].get("status") == "completed":
            print(f"[{i}/{len(selected)}] SKIP (already completed) {case['id']}")
            results.append(existing[case["id"]])
            continue
        print(f"[{i}/{len(selected)}] RUN {case['id']} :: {case['task'][:60]}")
        rec = run_one(case, output_root=output_root, sleep_between=args.sleep_between, args=args)
        print(
            f"    -> status={rec['status']} turns={rec['turns']} tokens={rec['tokens']} "
            f"dur={rec['duration_seconds']}s live_evidence={rec.get('live_evidence')} tools={rec['tool_sequence']}"
        )
        results.append(rec)
        # incremental save so we never lose progress
        report_path.write_text(
            json.dumps(
                {
                    "cases": results,
                    "summary": _summary(results),
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )

    md_report_path.write_text(_render_markdown(results), encoding="utf-8")
    print(f"\nReport JSON: {report_path}")
    print(f"Report MD:   {md_report_path}")
    summary = _summary(results)
    completed_rate = summary["live_evidence_cases"] / max(1, summary["total"])
    if completed_rate < args.min_completed_rate:
        print(
            f"ERROR: live evidence completion rate {completed_rate:.3f} < {args.min_completed_rate:.3f}",
            file=sys.stderr,
        )
        return 1
    return 0


def _summary(results: list[dict]) -> dict:
    tool_completed = [r for r in results if _tool_call_completed(r)]
    quality_pass = [r for r in tool_completed if _answer_quality_pass(r)]
    quality_questionable = [r for r in tool_completed if r.get("answer_quality_pass") is False]
    quality_unreviewed = [r for r in tool_completed if r.get("answer_quality_pass") is None]
    return {
        "total": len(results),
        "live_evidence_cases": len(tool_completed),
        "tool_call_completed_cases": len(tool_completed),
        "answer_quality_pass_cases": len(quality_pass),
        "semantic_success_cases": len(quality_pass),
        "answer_quality_questionable_cases": len(quality_questionable),
        "answer_quality_unreviewed_cases": len(quality_unreviewed),
        "completed_status": len([r for r in results if r["status"] == "completed"]),
        "failed_or_incomplete": len([r for r in results if not _tool_call_completed(r)]),
        "total_tokens": sum(r["tokens"] or 0 for r in results),
        "total_duration_seconds": round(sum(r["duration_seconds"] or 0 for r in results), 2),
        "avg_turns": round(sum(r["turns"] or 0 for r in tool_completed) / max(1, len(tool_completed)), 2),
    }


def _render_markdown(results: list[dict]) -> str:
    s = _summary(results)
    lines = [
        "# Live LLM Agent — Decision Trace Attempts",
        "",
        "This report separates live tool-call evidence from semantic answer quality.",
        "A case has tool-call evidence when it reached `completed`, used provider tokens, and called `finalize`; it is a semantic success only when `answer_quality_pass=true` after review.",
        "Failed, empty, max-turn, quota-limited, or assistant-answer-without-finalize cases are retained for debugging but must not be cited as successful semantic evidence.",
        "",
        "## Summary",
        "",
        f"- Total attempted cases: **{s['total']}**",
        f"- Tool-call completed cases: **{s['tool_call_completed_cases']}** ({s['tool_call_completed_cases']*100//max(1,s['total'])}%)",
        f"- Answer-quality pass cases: **{s['answer_quality_pass_cases']}**",
        f"- Answer-quality questionable cases: **{s['answer_quality_questionable_cases']}**",
        f"- Answer-quality unreviewed cases: **{s['answer_quality_unreviewed_cases']}**",
        f"- Completed status: {s['completed_status']}",
        f"- Failed or incomplete: {s['failed_or_incomplete']}",
        f"- Total tokens: **{s['total_tokens']:,}**",
        f"- Total wall time: {s['total_duration_seconds']}s",
        f"- Avg turns/tool-call-completed case: {s['avg_turns']}",
        "",
        "## Cases",
        "",
        "| # | Case | Difficulty | Tool-call completed | Answer-quality pass | Status | Turns | Tokens | Duration | Tool sequence |",
        "| - | --- | --- | --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for i, r in enumerate(results, 1):
        seq = " → ".join(r["tool_sequence"] or []) or "-"
        quality = r.get("answer_quality_pass")
        quality_display = "unreviewed" if quality is None else str(quality).lower()
        lines.append(
            f"| {i} | `{r['id']}` | {r['difficulty']} | {str(_tool_call_completed(r)).lower()} | {quality_display} | {r['status']} | {r['turns']} | {r['tokens']:,} | "
            f"{r['duration_seconds']}s | {seq} |"
        )
    lines.append("")
    lines.append("## Per-case detail")
    lines.append("")
    for r in results:
        lines.append(f"### `{r['id']}`")
        lines.append("")
        lines.append(f"- **Task**: {r['task']}")
        lines.append(f"- **Why hard**: {r['difficulty']}")
        lines.append(f"- **Tool-call completed**: `{str(_tool_call_completed(r)).lower()}`")
        quality = r.get("answer_quality_pass")
        quality_display = "unreviewed" if quality is None else str(quality).lower()
        lines.append(f"- **Answer-quality pass**: `{quality_display}`")
        if r.get("answer_quality_note"):
            lines.append(f"- **Answer-quality note**: {r['answer_quality_note']}")
        lines.append(f"- **Status**: {r['status']} (turns={r['turns']}, tokens={r['tokens']:,}, dur={r['duration_seconds']}s)")
        if r.get("trace_path"):
            lines.append(f"- **Trace**: `{r['trace_path']}`")
        if r.get("summary_path"):
            lines.append(f"- **Summary**: `{r['summary_path']}`")
        if r.get("tool_sequence"):
            lines.append(f"- **Tool calls (LLM-chosen)**: {' → '.join(r['tool_sequence'])}")
        if r.get("final_answer_preview"):
            lines.append("")
            lines.append("<details><summary>final answer preview</summary>")
            lines.append("")
            lines.append("```")
            lines.append(r["final_answer_preview"])
            lines.append("```")
            lines.append("")
            lines.append("</details>")
        if r.get("error"):
            lines.append(f"- **Error**: `{r['error']}`")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
