from mineru_data_agent.planner import analyze_requirement, build_task_result


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
