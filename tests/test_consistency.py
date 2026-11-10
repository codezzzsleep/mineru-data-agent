from mineru_data_agent.consistency import build_fine_grained_escalation_plan, compare_parser_outputs


def test_escalation_plan_targets_vlm_for_tables_and_ocr_for_missing_text() -> None:
    extracted = {
        "content_summary": {"page_count": 3, "page_indices": [0, 1, 2]},
        "tables": [{"headers": ["A"], "rows": [["1"]]}],
    }
    quality = {
        "issues": [
            {"code": "short_text", "level": "warning"},
            {"code": "numeric_total_mismatch", "level": "warning"},
        ]
    }

    plan = build_fine_grained_escalation_plan(
        extracted=extracted,
        quality=quality,
        input_metadata={"page_count": 3, "has_text_layer": False},
    )

    actions = {item["action"]: item for item in plan["actions"]}
    assert actions["ocr_pipeline_retry"]["method"] == "ocr"
    assert actions["vlm_region_or_page_retry"]["backend"] == "vlm-transformers"
    assert actions["vlm_region_or_page_retry"]["pages"] == [1, 2, 3]


def test_compare_parser_outputs_marks_vlm_hallucination_risk() -> None:
    report = compare_parser_outputs(
        [
            {"name": "pdf-text-layer", "role": "text", "text": "太行 根据地 民兵 兵工 材料"},
            {"name": "mineru-vlm", "role": "vlm", "text": "完全不同的虚构公司收入利润"},
        ]
    )

    assert report["status"] == "needs_review"
    assert report["hallucination_risks"][0]["parser"] == "mineru-vlm"
