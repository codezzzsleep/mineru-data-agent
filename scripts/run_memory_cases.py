from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from mineru_data_agent.agent import MinerUDataAgent


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEST_ROOT = PROJECT_ROOT / "submission_artifacts" / "memory_cases" / "cross_run_text_cleanup_memory"
RUN_ROOT = PROJECT_ROOT / "runs" / "memory_cases"


def main() -> None:
    if DEST_ROOT.exists():
        shutil.rmtree(DEST_ROOT)
    if RUN_ROOT.exists():
        shutil.rmtree(RUN_ROOT)
    DEST_ROOT.mkdir(parents=True, exist_ok=True)
    RUN_ROOT.mkdir(parents=True, exist_ok=True)

    input_path = DEST_ROOT / "input.html"
    input_path.write_text(_fixture_html(), encoding="utf-8")

    agent = MinerUDataAgent()
    first = agent.run(
        input_path,
        RUN_ROOT,
        task="清理网页巡检日报并输出结构化结果",
        profile="general_document",
    )
    second = agent.run(
        input_path,
        RUN_ROOT,
        task="清理网页巡检日报并输出结构化结果",
        profile="general_document",
    )

    _copy_run(first.output_dir, DEST_ROOT / "first_run")
    _copy_run(second.output_dir, DEST_ROOT / "second_run")
    _copy_selected_outputs(second.output_dir, DEST_ROOT)
    report = _report(first.to_jsonable(), second.to_jsonable())
    (DEST_ROOT / "memory_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (DEST_ROOT / "README.md").write_text(_readme(report), encoding="utf-8")
    _sanitize_artifact_paths(DEST_ROOT)
    print(
        json.dumps(
            {
                "dest": display_path(DEST_ROOT),
                "first_selected_attempt": report["first_run"]["selected_attempt"],
                "second_memory_recommended_actions": report["second_run"]["memory_recommended_actions"],
            },
            ensure_ascii=False,
        )
    )


def _fixture_html() -> str:
    noisy = "锟斤拷" + ("这是一段需要清理但仍可结构化的巡检文本。" * 20)
    return (
        "<html><body>"
        "<h1>巡检日报</h1>"
        "<p>报告日期：2026-05-23</p>"
        f"<p>{noisy}</p>"
        "</body></html>"
    )


def _copy_run(source_dir: str, target_dir: Path) -> None:
    source = Path(source_dir)
    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(source, target_dir)


def _copy_selected_outputs(source_dir: str, target_dir: Path) -> None:
    source = Path(source_dir)
    for name in ["result.json", "trace.json", "summary.md"]:
        shutil.copy2(source / name, target_dir / name)
    retrieval_source = source / "retrieval"
    if retrieval_source.exists():
        shutil.copytree(retrieval_source, target_dir / "retrieval")


def _sanitize_artifact_paths(root: Path) -> None:
    text_extensions = {".md", ".json", ".jsonl", ".txt", ".html"}
    project_text = str(PROJECT_ROOT)
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in text_extensions:
            continue
        text = path.read_text(encoding="utf-8")
        cleaned = text.replace(project_text, "<PROJECT_ROOT>")
        if cleaned != text:
            path.write_text(cleaned, encoding="utf-8")


def _report(first: dict[str, Any], second: dict[str, Any]) -> dict[str, Any]:
    first_memory = first.get("execution_control", {}).get("cross_run_memory", {})
    second_memory = second.get("execution_control", {}).get("cross_run_memory", {})
    second_runtime = second.get("execution_control", {}).get("runtime_recovery_plan", {})
    return {
        "schema_version": "2026-05-24",
        "case_id": "cross_run_text_cleanup_memory",
        "boundary": (
            "This is a controlled local-memory regression case. It proves deterministic SQLite recovery statistics "
            "are read by a later run; it is not live LLM autonomy, reinforcement learning, or model fine-tuning."
        ),
        "first_run": {
            "run_id": first.get("run_id"),
            "selected_attempt": first.get("recovery_decision", {}).get("selected_attempt"),
            "memory_recommended_actions": first_memory.get("recommended_actions", []),
            "quality": first.get("quality", {}).get("status"),
        },
        "second_run": {
            "run_id": second.get("run_id"),
            "selected_attempt": second.get("recovery_decision", {}).get("selected_attempt"),
            "memory_recommended_actions": second_memory.get("recommended_actions", []),
            "runtime_memory_recommended_actions": second_runtime.get("memory_recommended_actions", []),
            "quality": second.get("quality", {}).get("status"),
        },
    }


def _readme(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Cross-run Memory Case",
            "",
            "This controlled case runs the same noisy HTML document twice under the same output root.",
            "",
            f"- First run selected attempt: `{report['first_run']['selected_attempt']}`",
            f"- First run memory recommendations: `{report['first_run']['memory_recommended_actions']}`",
            f"- Second run memory recommendations: `{report['second_run']['memory_recommended_actions']}`",
            f"- Second runtime memory actions: `{report['second_run']['runtime_memory_recommended_actions']}`",
            "",
            "Boundary: local memory is a SQLite statistics table over prior recovery outcomes, not model learning or live LLM autonomy.",
            "",
        ]
    )


def display_path(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


if __name__ == "__main__":
    main()
