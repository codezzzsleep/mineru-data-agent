from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from mineru_data_agent.agent import MinerUDataAgent
from mineru_data_agent.models import ToolCall


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUN_ROOT = PROJECT_ROOT / "runs" / "agent_decision_cases"
DEST_ROOT = PROJECT_ROOT / "submission_artifacts" / "agent_decision_cases"


CASES = [
    {
        "id": "financial_growth_agent_plan",
        "input": PROJECT_ROOT / "examples" / "cases" / "case_1_financial_report.html",
        "task": "找出财报中与上一期相比增长最快的项目，计算变化幅度，并列出证据。",
        "profile": "auto",
        "preplan": {
            "recommended_profile": "financial_report",
            "recommended_runner": "native",
            "recommended_method": "auto",
            "target_schema": {"增长最快项目": "ranked financial line item", "变化幅度": "delta and percent"},
            "verification_focus": ["comparison_values_have_same_unit", "subtotal_total_consistency"],
            "recovery_policy": ["numeric mismatch requires manual review"],
        },
        "post_findings": [{"level": "info", "message": "growth ranking has table evidence", "evidence": "task_result.top_growth_candidate"}],
    },
    {
        "id": "noisy_contract_recovery_plan",
        "input": PROJECT_ROOT / "examples" / "challenge_cases" / "case_7_noisy_contract_scan.html",
        "task": "解析 OCR 噪声合同，抽取合同编号、双方和日期；如果有乱码，先清理后再接受。",
        "profile": "auto",
        "preplan": {
            "recommended_profile": "low_quality_ocr",
            "recommended_runner": "native",
            "recommended_method": "ocr",
            "target_schema": {"合同编号": "contract id", "双方": "party names", "签署日期": "date"},
            "verification_focus": ["mojibake cleaned", "critical fields keep evidence"],
            "recovery_policy": ["run text_cleanup when possible_mojibake appears"],
        },
        "post_findings": [{"level": "warning", "message": "OCR-like contract should keep review note", "evidence": "initial noise signal"}],
    },
    {
        "id": "standard_clause_entity_plan",
        "input": PROJECT_ROOT / "examples" / "cases" / "case_3_standard_contract.html",
        "task": "识别合同条款中的甲方、乙方、义务、例外条件和来源证据。",
        "profile": "auto",
        "preplan": {
            "recommended_profile": "standard_or_contract",
            "recommended_runner": "native",
            "recommended_method": "auto",
            "target_schema": {"甲方": "party", "乙方": "party", "义务": "obligation", "例外条件": "exception"},
            "verification_focus": ["clause ids preserved", "entity evidence exists"],
            "recovery_policy": ["manual review if party field is missing"],
        },
        "post_findings": [{"level": "info", "message": "contract fields have evidence candidates", "evidence": "field_evidence"}],
    },
    {
        "id": "workflow_diagram_agent_plan",
        "input": PROJECT_ROOT / "examples" / "cases" / "case_4_workflow_diagram.html",
        "task": "把流程图文档拆成步骤、责任角色、输入输出、异常触发条件，并标记需要视觉复核的节点。",
        "profile": "auto",
        "preplan": {
            "recommended_profile": "workflow_or_diagram",
            "recommended_runner": "native",
            "recommended_method": "auto",
            "target_schema": {"步骤": "process step", "责任角色": "actor", "异常触发条件": "risk condition"},
            "verification_focus": ["workflow order preserved", "visual review hints retained"],
            "recovery_policy": ["visual review if diagram evidence is missing"],
        },
        "post_findings": [{"level": "info", "message": "workflow anomaly signal retained", "evidence": "semantic_signals.anomaly_lines"}],
    },
    {
        "id": "cross_page_table_agent_plan",
        "input": PROJECT_ROOT / "examples" / "challenge_cases" / "case_6_cross_page_financial_table.html",
        "task": "处理跨页财报表格，合并上下文，检查小计和总计，并输出需要人工复核的差异。",
        "profile": "auto",
        "preplan": {
            "recommended_profile": "financial_report",
            "recommended_runner": "native",
            "recommended_method": "auto",
            "target_schema": {"跨页表格": "table span", "小计": "subtotal", "总计": "total", "差异": "mismatch"},
            "verification_focus": ["page_or_chunk_span_is_recorded", "subtotal_total_consistency"],
            "recovery_policy": ["manual_numeric_review on total mismatch", "chunk_stitch_review for cross-page reference"],
        },
        "post_findings": [{"level": "warning", "message": "cross-page table should remain reviewable", "evidence": "numeric_total_mismatch"}],
    },
]


def main() -> None:
    if DEST_ROOT.exists():
        shutil.rmtree(DEST_ROOT)
    DEST_ROOT.mkdir(parents=True, exist_ok=True)
    RUN_ROOT.mkdir(parents=True, exist_ok=True)

    rows = [
        "# Agent Decision Case Pack",
        "",
        "Five deterministic local cases that exercise task decomposition, dynamic tool selection, quality-triggered replanning, and LLM-compatible pre/post decision hooks.",
        "",
        "Boundary: these cases use a scripted local LLM client so they are reproducible without API keys. They do not replace the saved live ModelScope case in `submission_artifacts/llm_cases/`.",
        "",
        "| Case | Profile | Intents | Selected Tools | Replan Issues | LLM Tokens |",
        "| --- | --- | --- | --- | --- | ---: |",
    ]
    index = []
    for case in CASES:
        llm = _ScriptedLLM(case)
        agent = MinerUDataAgent(llm_client=llm)
        result = agent.run(
            case["input"],
            RUN_ROOT,
            task=case["task"],
            profile=case["profile"],
            method="auto",
            lang="ch",
        )
        case_dir = DEST_ROOT / case["id"]
        shutil.copytree(Path(result.output_dir), case_dir)
        shutil.copy2(case["input"], case_dir / f"input{case['input'].suffix.lower()}")
        sanitize_tree(case_dir)

        action_plan = result.execution_control.get("agent_action_plan", {})
        tools = [
            item.get("name")
            for item in action_plan.get("tool_registry", [])
            if isinstance(item, dict) and item.get("selected")
        ]
        task_result = result.extracted.get("task_result", {}) if isinstance(result.extracted, dict) else {}
        replan = result.execution_control.get("replan_after_quality", {})
        usage = result.llm_analysis.get("usage_summary", {}) if isinstance(result.llm_analysis, dict) else {}
        rows.append(
            "| {case_id} | {profile} | {intents} | {tools} | {issues} | {tokens} |".format(
                case_id=case["id"],
                profile=result.profile,
                intents=", ".join(task_result.get("task_intents", [])),
                tools=", ".join(str(item) for item in tools[:8]),
                issues=", ".join(replan.get("issue_codes", [])) or "-",
                tokens=usage.get("total_tokens", 0),
            )
        )
        index.append(
            {
                "id": case["id"],
                "input": display_path(case["input"]),
                "task": case["task"],
                "profile": result.profile,
                "result_path": display_path(case_dir / "result.json"),
                "trace_path": display_path(case_dir / "trace.json"),
                "summary_path": display_path(case_dir / "summary.md"),
                "task_intents": task_result.get("task_intents", []),
                "selected_tools": tools,
                "replan_after_quality": replan,
                "llm_usage_summary": usage,
            }
        )

    (DEST_ROOT / "README.md").write_text("\n".join(rows).strip() + "\n", encoding="utf-8")
    (DEST_ROOT / "artifact_index.json").write_text(
        json.dumps({"cases": index, "boundary": "scripted local LLM client; live provider case remains in llm_cases"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"dest": display_path(DEST_ROOT), "cases": [case["id"] for case in CASES]}, ensure_ascii=False, indent=2))


class _ScriptedLLM:
    def __init__(self, case: dict[str, Any]) -> None:
        self.case = case

    def plan_execution(self, **kwargs: object) -> tuple[dict[str, Any], ToolCall]:
        preplan = {
            "enabled": True,
            "status": "completed",
            "task_understanding": self.case["task"],
            "recommended_backend": "pipeline",
            "recommended_lang": "ch",
            "execution_plan": [
                "Decompose task into extraction, validation, and recovery decisions",
                "Select tools based on profile, provenance need, and quality risks",
            ],
            "confidence": 0.82,
            "llm_usage": _usage("scripted-preplan", 620, 180),
        }
        preplan.update(self.case["preplan"])
        return (
            preplan,
            ToolCall(
                tool="scripted-llm-preplan",
                command=["scripted-llm", "preplan", self.case["id"]],
                status="completed",
                elapsed_seconds=0.0,
                metadata={"llm_usage": preplan["llm_usage"]},
            ),
        )

    def analyze(self, **kwargs: object) -> tuple[dict[str, Any], ToolCall]:
        analysis = {
            "status": "completed",
            "task_understanding": self.case["task"],
            "execution_plan": ["Review quality issues", "Map issue codes to replan actions"],
            "target_schema": self.case["preplan"].get("target_schema", {}),
            "verification_focus": self.case["preplan"].get("verification_focus", []),
            "risk_findings": self.case.get("post_findings", []),
            "recovery_suggestions": self.case["preplan"].get("recovery_policy", []),
            "llm_usage": _usage("scripted-post-review", 520, 140),
        }
        return (
            analysis,
            ToolCall(
                tool="scripted-llm-review",
                command=["scripted-llm", "review", self.case["id"]],
                status="completed",
                elapsed_seconds=0.0,
                metadata={"llm_usage": analysis["llm_usage"]},
            ),
        )


def _usage(model: str, prompt_tokens: int, completion_tokens: int) -> dict[str, Any]:
    return {
        "provider": "scripted-local",
        "model": model,
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
        "cost_estimate": {"configured": False, "estimated_cost": None, "currency": "USD"},
    }


def sanitize_tree(path: Path) -> None:
    for item in path.rglob("*"):
        if not item.is_file() or item.suffix.lower() not in {".json", ".jsonl", ".md", ".txt", ".html"}:
            continue
        text = item.read_text(encoding="utf-8", errors="replace")
        clean = text.replace(str(PROJECT_ROOT), "<PROJECT_ROOT>")
        clean = clean.replace(str(PROJECT_ROOT).replace("\\", "\\\\"), "<PROJECT_ROOT>")
        item.write_text(clean, encoding="utf-8")


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


if __name__ == "__main__":
    main()
