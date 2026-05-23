from mineru_data_agent.llm_client import (
    _chat_completions_url,
    _extract_message_parts,
    _normalize_analysis,
    _normalize_preplan,
    _parse_json_object,
    _parser_context,
    _sanitize_error_text,
)


def test_parse_json_object_accepts_plain_json() -> None:
    data = _parse_json_object('{"task_understanding": "ok", "execution_plan": ["a"]}')
    assert data["task_understanding"] == "ok"
    assert data["execution_plan"] == ["a"]


def test_parse_json_object_accepts_markdown_fence() -> None:
    data = _parse_json_object('```json\n{"target_schema": {"amount": "number"}}\n```')
    assert data["target_schema"]["amount"] == "number"


def test_chat_completions_url_handles_v1_base_url() -> None:
    assert _chat_completions_url("https://api-inference.modelscope.cn/v1") == (
        "https://api-inference.modelscope.cn/v1/chat/completions"
    )
    assert _chat_completions_url("https://api.deepseek.com") == "https://api.deepseek.com/v1/chat/completions"


def test_extract_message_parts_reads_reasoning_content() -> None:
    content, reasoning = _extract_message_parts(
        {
            "choices": [
                {
                    "message": {
                        "reasoning_content": "think",
                        "content": '{"task_understanding": "ok"}',
                    }
                }
            ]
        }
    )
    assert reasoning == "think"
    assert content == '{"task_understanding": "ok"}'


def test_parser_context_marks_html_extractor() -> None:
    context = _parser_context({"content_summary": {"source_counts": {"html": 2}, "provenance_level": "document"}})
    assert context["actual_parser"] == "native-html-extractor"
    assert "Do not describe" in context["warning"]


def test_normalize_analysis_downgrades_llm_error_without_quality_error() -> None:
    analysis = {"risk_findings": [{"level": "error", "message": "model overcalled this"}]}
    normalized = _normalize_analysis(analysis, {"issues": [{"level": "info", "code": "document_level_provenance"}]})
    assert normalized["risk_findings"][0]["level"] == "warning"


def test_normalize_preplan_coerces_scheduler_fields() -> None:
    plan = _normalize_preplan(
        {
            "recommended_profile": " low_quality_ocr ",
            "recommended_method": "ocr",
            "execution_plan": ["parse", 2],
            "target_schema": {"报告日期": "date"},
            "verification_focus": "bad",
            "confidence": "1.7",
        }
    )
    assert plan["recommended_profile"] == "low_quality_ocr"
    assert plan["execution_plan"] == ["parse", "2"]
    assert plan["verification_focus"] == []
    assert plan["target_schema"] == {"报告日期": "date"}
    assert plan["confidence"] == 1.0


def test_sanitize_error_text_removes_api_key_and_bearer_token() -> None:
    bearer = "Bearer abc.def-123"
    text = f"request failed Authorization: {bearer} api_key=secret-key"
    clean = _sanitize_error_text(text, api_key="secret-key")
    assert "secret-key" not in clean
    assert bearer not in clean
    assert "Bearer ***" in clean
    assert "api_key=***" in clean
