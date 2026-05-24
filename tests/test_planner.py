import json

from mineru_data_agent.planner import (
    analyze_requirement,
    build_agent_action_plan,
    build_quality_replan,
    build_task_result,
    infer_profile,
    infer_profile_evidence,
)
from mineru_data_agent.profile_config import load_profile_definitions


def test_profile_inference_uses_configurable_evidence(monkeypatch, tmp_path) -> None:
    config_path = tmp_path / "profiles.json"
    config_path.write_text(
        json.dumps(
            {
                "profiles": {
                    "standard_or_contract": {
                        "description": "Environmental penalty reports and compliance clauses.",
                        "keywords": ["环保", "处罚", "整改"],
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("MINERU_DATA_AGENT_PROFILE_CONFIG", str(config_path))
    load_profile_definitions.cache_clear()

    evidence = infer_profile_evidence("提取这份环保报告中的所有处罚条款和整改要求", "notice.pdf")

    assert infer_profile("提取这份环保报告中的所有处罚条款和整改要求", "notice.pdf") == "standard_or_contract"
    assert evidence["selected_profile"] == "standard_or_contract"
    assert evidence["source"] == "profile_config"
    assert evidence["matches"][0]["keyword_hits"]
    assert "not a learned embedding model" in evidence["boundary"]

    load_profile_definitions.cache_clear()


def test_unknown_configured_profile_maps_to_general_document(monkeypatch, tmp_path) -> None:
    config_path = tmp_path / "profiles.json"
    config_path.write_text(
        json.dumps(
            {
                "profiles": {
                    "medical_claim": {
                        "description": "Insurance claims, diagnosis, patient records.",
                        "keywords": ["诊断", "医保", "理赔"],
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("MINERU_DATA_AGENT_PROFILE_CONFIG", str(config_path))
    load_profile_definitions.cache_clear()

    evidence = infer_profile_evidence("抽取医保理赔诊断结论", "claim.pdf")

    assert evidence["configured_profile"] == "medical_claim"
    assert evidence["selected_profile"] == "general_document"
    assert evidence["unsupported_profile_mapped_to"] == "general_document"

    load_profile_definitions.cache_clear()


def test_adaptive_planner_detects_growth_ranking_intent() -> None:
    decision = analyze_requirement(
        "找出财报中与去年相比增长最快的项目，并给出证据",
        "financial_report",
        input_metadata={"suffix": ".pdf"},
    )

    assert "growth_analysis" in decision.task_intents
    assert "ranking" in decision.task_intents
    assert "comparison" in decision.task_intents
    assert "percent_change" in decision.target_schema
    assert "trend_and_ranking_analyzer" in decision.post_processors
    assert decision.quality_thresholds["require_numeric_facts"] is True
    assert any(item["action"] == "cli_fallback" for item in decision.recovery_strategy)


def test_task_result_computes_top_growth_candidate() -> None:
    extracted = {
        "tables": [
            {
                "headers": ["项目", "2026", "2025"],
                "rows": [
                    ["收入", "120", "100"],
                    ["利润", "90", "50"],
                ],
            }
        ],
        "semantic_signals": {"anomaly_lines": []},
        "field_evidence": [],
    }
    decision = analyze_requirement("找出增长最快的项目", "financial_report")

    result = build_task_result(extracted, decision)

    assert result["answers"]["top_growth_candidate"]["label"] == "利润"
    assert result["answers"]["top_growth_candidate"]["percent_change"] == 80.0


def test_agent_action_plan_selects_dynamic_tools() -> None:
    decision = analyze_requirement(
        "解析跨页财报，检查合计并给出页码证据",
        "financial_report",
        input_metadata={"suffix": ".pdf"},
    )

    action_plan = build_agent_action_plan(
        "解析跨页财报，检查合计并给出页码证据",
        "financial_report",
        decision,
        input_metadata={"suffix": ".pdf"},
        runner="agent-api",
        backend="pipeline",
        method="auto",
        lang="ch",
        llm_enabled=True,
    ).to_jsonable()

    selected = {item["name"] for item in action_plan["tool_registry"] if item["selected"]}
    assert "mineru_agent_api" in selected
    assert "llm_preplanner" in selected
    assert "numeric_validator" in selected
    assert "cli_fallback" in selected
    assert action_plan["subtasks"][0]["id"] == "understand_task"
    assert any(item["issue_code"] == "no_page_provenance" for item in action_plan["replan_triggers"])
    assert action_plan["state_machine"]["model"] == "single-run conditional DAG"
    cli_edge = next(
        item
        for item in action_plan["state_machine"]["conditional_edges"]
        if item["condition"] == "quality_issue:no_page_provenance"
    )
    assert cli_edge["runner_change"] == "agent-api->cli"


def test_quality_replan_maps_issues_to_actions() -> None:
    decision = analyze_requirement("解析财报并检查合计", "financial_report", input_metadata={"suffix": ".pdf"})
    action_plan = build_agent_action_plan(
        "解析财报并检查合计",
        "financial_report",
        decision,
        input_metadata={"suffix": ".pdf"},
        runner="agent-api",
        backend="pipeline",
        method="auto",
        lang="ch",
        llm_enabled=False,
    )
    quality = {
        "status": "pass_with_warnings",
        "score": 76,
        "issues": [
            {"code": "no_page_provenance"},
            {"code": "numeric_total_mismatch"},
        ],
    }
    replan = build_quality_replan(
        quality=quality,
        attempts=[{"name": "initial"}, {"name": "cli_fallback"}],
        selected_attempt="cli_fallback",
        decision=decision,
        action_plan=action_plan,
    )

    assert replan["selected_attempt"] == "cli_fallback"
    assert {"issue_code": "no_page_provenance", "candidate_action": "cli_fallback", "available_in_attempts": True} in replan[
        "considered_actions"
    ]
    assert "manual_numeric_review" in replan["next_action_if_still_risky"]
    triggered = replan["quality_triggered_replan"]["triggered"]
    assert any(item["issue_code"] == "no_page_provenance" and item["runner_change"] == "agent-api->cli" for item in triggered)
