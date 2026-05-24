from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_live_llm_matrix.py"
SPEC = importlib.util.spec_from_file_location("run_live_llm_matrix", SCRIPT_PATH)
assert SPEC and SPEC.loader
matrix = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(matrix)


def test_load_cases_validates_and_resolves_project_paths() -> None:
    cases = matrix.load_cases(matrix.DEFAULT_MANIFEST)
    assert len(cases) >= 5
    assert cases[0]["id"] == "financial_review"
    assert Path(cases[0]["input"]).exists()
    assert cases[0]["input_display"].startswith("examples/")


def test_load_cases_rejects_missing_required_fields(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"cases": [{"id": "bad", "input": "examples/cases/case_1_financial_report.html"}]}')

    with pytest.raises(ValueError, match="missing required fields"):
        matrix.load_cases(manifest)


def test_select_cases_filters_and_limits() -> None:
    cases = [
        {"id": "a"},
        {"id": "b"},
        {"id": "c"},
    ]
    assert [case["id"] for case in matrix.select_cases(cases, ["c", "a"], None)] == ["c", "a"]
    assert [case["id"] for case in matrix.select_cases(cases, None, 2)] == ["a", "b"]

    with pytest.raises(ValueError, match="Unknown case"):
        matrix.select_cases(cases, ["missing"], None)


def test_skip_report_is_not_live_evidence() -> None:
    args = argparse.Namespace(
        provider="modelscope",
        model=None,
        manifest=str(matrix.DEFAULT_MANIFEST),
    )
    cases = matrix.select_cases(matrix.load_cases(matrix.DEFAULT_MANIFEST), None, 1)
    report = matrix.build_skip_report(args, cases, "MODELSCOPE_API_KEY")

    assert report["status"] == "skipped_missing_provider_key"
    assert report["live_provider_evidence"] is False
    assert report["aggregate"]["total_tokens"] == 0
    assert "not live LLM evidence" in report["boundary"][0]


def test_render_markdown_marks_live_evidence_flag() -> None:
    report = {
        "status": "skipped_missing_provider_key",
        "live_provider_evidence": False,
        "provider": "deepseek",
        "model": "provider default",
        "manifest": "examples/llm_live_cases.json",
        "aggregate": {
            "completed": 0,
            "failed": 0,
            "llm_enabled_results": 0,
            "llm_tool_calls": 0,
            "total_tokens": 0,
            "cases_with_recovery_suggestions": 0,
            "cases_with_applied_controls": 0,
        },
        "cases": [{"id": "financial_review", "status": "not_run"}],
        "boundary": ["This is a skip report, not live LLM evidence."],
    }

    markdown = matrix.render_markdown(report)
    assert "Live provider evidence: `False`" in markdown
    assert "not live LLM evidence" in markdown
