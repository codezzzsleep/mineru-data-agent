from mineru_data_agent.validators import build_quality_report


def test_empty_markdown_is_error() -> None:
    report = build_quality_report("", {"content_summary": {"item_count": 0}}, "general_document")
    assert report["status"] == "needs_review"
    assert any(item["code"] == "empty_markdown" for item in report["issues"])


def test_financial_profile_warns_when_numeric_signal_missing() -> None:
    extracted = {
        "content_summary": {"item_count": 2, "page_count": 1},
        "tables": [],
        "numeric_facts": [],
        "sections": [{"title": "A", "text": "plain text"}],
    }
    report = build_quality_report("plain text about report", extracted, "financial_report")
    assert any(item["code"] == "financial_signal_missing" for item in report["issues"])


def test_missing_page_provenance_is_flagged() -> None:
    extracted = {
        "content_summary": {"item_count": 3, "page_count": 0, "provenance_level": "none"},
        "tables": [],
        "numeric_facts": [],
        "sections": [{"title": "A", "text": "plain text"}],
    }
    report = build_quality_report("plain text about report", extracted, "general_document")
    assert any(item["code"] == "no_page_provenance" for item in report["issues"])


def test_html_document_provenance_is_informational() -> None:
    markdown = "plain text about report " * 20
    extracted = {
        "content_summary": {
            "item_count": 3,
            "page_count": 0,
            "provenance_level": "document",
            "source_counts": {"html": 3},
        },
        "tables": [],
        "numeric_facts": [],
        "sections": [{"title": "A", "text": "plain text"}],
    }
    report = build_quality_report(markdown, extracted, "general_document")
    issue = next(item for item in report["issues"] if item["code"] == "document_level_provenance")
    assert issue["level"] == "info"
    assert report["score"] == 100
    assert report["status"] == "pass"
    assert report["issue_counts"] == {"error": 0, "warning": 0, "info": 1}


def test_short_general_html_document_does_not_warn_as_ocr_failure() -> None:
    extracted = {
        "content_summary": {
            "item_count": 2,
            "page_count": 0,
            "provenance_level": "document",
            "source_counts": {"html": 2},
        },
        "tables": [],
        "numeric_facts": [],
        "sections": [{"title": "A", "text": "短日报"}],
    }
    report = build_quality_report("报告日期：2026-05-23\n结论：正常，无需整改。", extracted, "general_document")
    codes = {item["code"] for item in report["issues"]}
    assert "short_text" not in codes
    assert report["status"] == "pass"


def test_short_pdf_page_text_still_warns_for_ocr_review() -> None:
    extracted = {
        "content_summary": {"item_count": 1, "page_count": 1, "provenance_level": "page", "source_counts": {"native": 1}},
        "tables": [],
        "numeric_facts": [],
        "sections": [{"title": "A", "text": "too short"}],
    }
    report = build_quality_report("too short", extracted, "general_document")
    assert any(item["code"] == "short_text" for item in report["issues"])


def test_total_row_is_verified() -> None:
    extracted = {
        "content_summary": {"item_count": 5, "page_count": 2},
        "sections": [],
        "numeric_facts": [{"line": 1, "numbers": ["100"]}],
        "tables": [{"rows": [["revenue", "100"], ["total", "100"]]}],
    }
    report = build_quality_report("revenue 100\ntotal 100", extracted, "financial_report")
    assert any(item["code"] == "numeric_total_needs_review" for item in report["issues"])


def test_total_row_sum_is_verified_when_comparable() -> None:
    markdown = "revenue 100\ncost 60\ntotal 160\n" + ("financial table evidence " * 20)
    extracted = {
        "content_summary": {"item_count": 5, "page_count": 2},
        "sections": [],
        "numeric_facts": [{"line": 1, "numbers": ["100"]}],
        "tables": [{"rows": [["revenue", "100"], ["cost", "60"], ["total", "160"]]}],
    }
    report = build_quality_report(markdown, extracted, "financial_report")
    assert any(item["code"] == "numeric_total_verified" for item in report["issues"])
    assert report["score"] == 100


def test_total_row_sum_mismatch_is_warned() -> None:
    markdown = "revenue 100\ncost 60\ntotal 150\n" + ("financial table evidence " * 20)
    extracted = {
        "content_summary": {"item_count": 5, "page_count": 2},
        "sections": [],
        "numeric_facts": [{"line": 1, "numbers": ["100"]}],
        "tables": [{"rows": [["revenue", "100"], ["cost", "60"], ["total", "150"]]}],
    }
    report = build_quality_report(markdown, extracted, "financial_report")
    assert any(item["code"] == "numeric_total_mismatch" for item in report["issues"])
    assert report["score"] == 92
    assert report["status"] == "pass_with_warnings"


def test_total_row_tolerance_is_strict_for_financial_values() -> None:
    markdown = "a 50000\nb 50050\ntotal 100000\n" + ("financial table evidence " * 20)
    extracted = {
        "content_summary": {"item_count": 5, "page_count": 2},
        "sections": [],
        "numeric_facts": [{"line": 1, "numbers": ["50000"]}],
        "tables": [{"rows": [["a", "50000"], ["b", "50050"], ["total", "100000"]]}],
    }
    report = build_quality_report(markdown, extracted, "financial_report")
    assert any(item["code"] == "numeric_total_mismatch" for item in report["issues"])


def test_task_expected_fields_are_checked() -> None:
    extracted = {
        "content_summary": {"item_count": 3, "page_count": 1},
        "sections": [{"title": "A", "text": "plain text"}],
        "tables": [],
        "numeric_facts": [],
        "key_values": [],
        "semantic_signals": {
            "dates": [],
            "recommendations": [],
            "anomaly_lines": [],
            "field_coverage": {
                "has_date": False,
                "has_recommendation": False,
                "has_anomaly_signal": False,
            },
        },
        "structure_quality": {"heading_section_count": 0, "fallback_section_count": 1},
    }
    report = build_quality_report("plain text about report", extracted, "general_document", task="抽取日期和处理建议")
    codes = {item["code"] for item in report["issues"]}
    assert "expected_date_missing" in codes
    assert "expected_recommendation_missing" in codes
