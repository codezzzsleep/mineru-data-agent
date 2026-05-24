from mineru_data_agent.planner import analyze_requirement, build_agent_action_plan, build_quality_replan, build_task_result


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
