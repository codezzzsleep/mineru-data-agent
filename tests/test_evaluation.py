import json
from pathlib import Path

from mineru_data_agent.evaluation import evaluate_cases, render_markdown_report


def test_evaluate_cases_computes_labeled_metrics(tmp_path: Path) -> None:
    result_path = tmp_path / "result.json"
    result_path.write_text(
        json.dumps(
            {
                "profile": "financial_report",
                "extracted": {
                    "key_value_map": {"报告日期": "2026-05-23", "公司名称": "测试公司"},
                    "sections": [{}, {}],
                    "tables": [{}],
                    "numeric_facts": [{}, {}],
                    "content_summary": {"provenance_level": "page"},
                },
                "quality": {
                    "status": "pass",
                    "score": 100,
                    "issues": [{"code": "numeric_total_verified"}],
                },
                "recovery_decision": {
                    "executed": True,
                    "selected_attempt": "text_cleanup",
                    "decision": "recovered_accept",
                    "initial_issue_codes": ["possible_mojibake"],
                },
                "retrieval_export": {"stats": {"total_chunks": 2}},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    labels_path = tmp_path / "labels.json"
    labels_path.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "id": "demo",
                        "result_path": "result.json",
                        "expected_profile": "financial_report",
                        "expected_fields": {"报告日期": "2026-05-23", "公司名称": "测试公司"},
                        "expected_text_contains": ["测试公司", "page"],
                        "minimums": {
                            "sections": 2,
                            "tables": 1,
                            "numeric_facts": 2,
                            "retrieval_chunks": 2,
                            "issue_codes": ["numeric_total_verified"],
                        },
                        "expected_quality": {"status": "pass", "min_score": 95},
                        "expected_provenance": "page",
                        "expected_recovery": {
                            "executed": True,
                            "selected_attempt": "text_cleanup",
                            "decision": "recovered_accept",
                            "initial_issue_codes": ["possible_mojibake"],
                        },
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = evaluate_cases(labels_path, project_root=tmp_path)

    assert report["aggregate"]["field_accuracy"] == 1.0
    assert report["aggregate"]["text_evidence_accuracy"] == 1.0
    assert report["aggregate"]["profile_accuracy"] == 1.0
    assert report["aggregate"]["structure_gate_pass_rate"] == 1.0
    assert report["aggregate"]["recovery_gate_pass_rate"] == 1.0
    assert "Expected-field accuracy: 100.0%" in render_markdown_report(report)
    assert "Text evidence accuracy: 100.0%" in render_markdown_report(report)
    assert "Recovery gate pass rate: 100.0%" in render_markdown_report(report)
