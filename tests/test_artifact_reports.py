from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_cost_model_report_has_runtime_modes() -> None:
    module = _load_script("build_cost_model.py")
    report = module.build_report()

    scenario_ids = {item["id"] for item in report["scenarios"]}
    assert {"native_html_office_rules", "mineru_cli_pdf", "online_agent_api_pdf", "llm_preplan_review"} <= scenario_ids
    assert "MINERU_DATA_AGENT_GPU_CNY_PER_HOUR" in report["pricing_inputs"]["env_vars"]


def test_recovery_effectiveness_report_counts_saved_attempts() -> None:
    module = _load_script("build_recovery_effectiveness_report.py")
    report = module.build_report()

    aggregate = report["aggregate"]
    assert aggregate["results_with_recovery"] >= 17
    assert aggregate["attempt_counts"]["initial"] >= aggregate["results_with_recovery"]
    assert "no_page_provenance" in aggregate["initial_issue_counts"]


def test_long_document_risk_report_keeps_chunk_boundaries() -> None:
    module = _load_script("build_long_document_risk_report.py")
    report = module.build_report()

    assert report["aggregate"]["page_count"] == 48
    assert report["aggregate"]["total_chunks"] == 3
    assert {item["id"] for item in report["risks"]} >= {"cross_chunk_context", "document_level_provenance"}


def test_code_quality_report_counts_tests_and_ci() -> None:
    module = _load_script("build_code_quality_report.py")
    report = module.build_report()

    assert report["aggregate"]["test_functions"] >= 65
    assert ".github/workflows/tests.yml" in report["aggregate"]["workflow_files"]


def test_retrieval_validation_report_scans_saved_chunks() -> None:
    module = _load_script("build_retrieval_validation_report.py")
    report = module.build_report()

    assert report["aggregate"]["chunk_files"] >= 17
    assert report["aggregate"]["total_chunks"] > 0
    assert "label_query_checks" in report["aggregate"]


def test_agent_value_report_separates_live_and_offline_decisions() -> None:
    module = _load_script("build_agent_value_report.py")
    report = module.build_report()

    modes = report["aggregate"]["decision_modes"]
    assert modes["offline_scripted_decision_regression"] >= 5
    assert modes["controlled_fault_injection"] >= 5
    assert report["aggregate"]["with_live_llm_trace"] >= 1
    assert "execution_control.agent_action_plan.state_machine" in report["agent_layer_fields"]
    assert "execution_control.runtime_recovery_plan" in report["agent_layer_fields"]



def test_artifact_index_reports_live_agent_and_cost_schema() -> None:
    module = _load_script("build_artifacts_index.py")
    report = module.build_report()

    category_ids = {item["id"] for item in report["categories"]}
    assert "agent_live_cases" in category_ids
    assert report["quick_metrics"]["agent_live_cases"]["tool_call_completed_cases"] >= 4
    assert report["quick_metrics"]["agent_live_cases"]["answer_quality_pass_cases"] >= 2
    assert report["quick_metrics"]["agent_live_cases"]["answer_quality_questionable_cases"] >= 2
    assert report["quick_metrics"]["agent_live_cases"]["total_tokens"] > 0
    assert report["quick_metrics"]["cost_model"]["scenarios"] >= 4
    assert report["quick_metrics"]["cost_model"]["pricing_inputs"]


def _load_script(name: str) -> ModuleType:
    path = PROJECT_ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
