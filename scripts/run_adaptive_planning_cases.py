from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from mineru_data_agent.agent import MinerUDataAgent


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT = PROJECT_ROOT / "examples" / "cases" / "case_1_financial_report.html"
RUN_ROOT = PROJECT_ROOT / "runs" / "adaptive_cases"
DEST_ROOT = PROJECT_ROOT / "submission_artifacts" / "adaptive_cases"


CASES = [
    {
        "id": "case_financial_growth_query",
        "task": "找出财报中与上一期相比增长最快的项目，计算变化幅度，并给出证据。",
        "profile": "financial_report",
    },
    {
        "id": "case_financial_anomaly_evidence_query",
        "task": "找出财报中需要复核的异常或风险信号，列出来源证据和建议处理动作。",
        "profile": "financial_report",
    },
]


def main() -> None:
    if DEST_ROOT.exists():
        shutil.rmtree(DEST_ROOT)
    DEST_ROOT.mkdir(parents=True, exist_ok=True)
    RUN_ROOT.mkdir(parents=True, exist_ok=True)

    rows = [
        "# Adaptive Planning Case Pack",
        "",
        "Same input document, different natural-language tasks. The evidence checks whether the Agent changes task intents, target schema, post-processors, and task-specific answers.",
        "",
        f"- Input: `{_display(INPUT)}`",
        "",
        "| Case | Task Intents | Schema Keys | Answer Keys | Top Growth |",
        "| --- | --- | --- | --- | --- |",
    ]
    index = []
    agent = MinerUDataAgent()
    for case in CASES:
        result = agent.run(
            INPUT,
            RUN_ROOT,
            task=case["task"],
            profile=case["profile"],
            method="auto",
            lang="ch",
        )
        case_dir = DEST_ROOT / case["id"]
        shutil.copytree(Path(result.output_dir), case_dir)
        shutil.copy2(INPUT, case_dir / "input.html")
        sanitize_tree(case_dir)

        task_result = result.extracted.get("task_result", {})
        adaptive = result.execution_control.get("adaptive_decision", {})
        answers = task_result.get("answers", {}) if isinstance(task_result, dict) else {}
        top_growth = answers.get("top_growth_candidate") if isinstance(answers, dict) else None
        top_growth_text = ""
        if isinstance(top_growth, dict):
            top_growth_text = f"{top_growth.get('label')} ({top_growth.get('percent_change')}%)"
        rows.append(
            "| {case_id} | {intents} | {schema} | {answers} | {growth} |".format(
                case_id=case["id"],
                intents=", ".join(task_result.get("task_intents", [])) if isinstance(task_result, dict) else "",
                schema=", ".join(list(adaptive.get("target_schema", {}).keys())[:8])
                if isinstance(adaptive.get("target_schema"), dict)
                else "",
                answers=", ".join(answers.keys()) if isinstance(answers, dict) else "",
                growth=top_growth_text,
            )
        )
        index.append(
            {
                "id": case["id"],
                "task": case["task"],
                "result_path": _display(case_dir / "result.json"),
                "trace_path": _display(case_dir / "trace.json"),
                "summary_path": _display(case_dir / "summary.md"),
                "task_intents": task_result.get("task_intents", []) if isinstance(task_result, dict) else [],
                "target_schema": adaptive.get("target_schema", {}) if isinstance(adaptive, dict) else {},
                "answers": list(answers.keys()) if isinstance(answers, dict) else [],
            }
        )

    (DEST_ROOT / "README.md").write_text("\n".join(rows).strip() + "\n", encoding="utf-8")
    (DEST_ROOT / "artifact_index.json").write_text(
        json.dumps({"input": _display(INPUT), "cases": index}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"dest": _display(DEST_ROOT), "cases": [case["id"] for case in CASES]}, ensure_ascii=False, indent=2))


def sanitize_tree(path: Path) -> None:
    for item in path.rglob("*"):
        if not item.is_file() or item.suffix.lower() not in {".json", ".jsonl", ".md", ".txt", ".html"}:
            continue
        text = item.read_text(encoding="utf-8", errors="replace")
        clean = text.replace(str(PROJECT_ROOT), "<PROJECT_ROOT>")
        clean = clean.replace(str(PROJECT_ROOT).replace("\\", "\\\\"), "<PROJECT_ROOT>")
        item.write_text(clean, encoding="utf-8")


def _display(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


if __name__ == "__main__":
    main()
