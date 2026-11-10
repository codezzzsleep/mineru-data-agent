import json
from pathlib import Path

from mineru_data_agent.skill_exporter import build_document_skill_package


def test_document_skill_package_writes_skill_and_references(tmp_path: Path) -> None:
    result = {
        "run_id": "abc123",
        "task": "extract financial fields",
        "profile": "financial_report",
        "input_file": str(tmp_path / "report.pdf"),
        "schema_version": "2026-05-24",
        "execution_control": {
            "workflow_routing": {
                "requested_runner": "auto",
                "selected_runner": "precise-api",
                "selected_tool": "mineru_precise_api",
                "route_mode": "auto_precise_for_complex_or_large_input",
                "status": "ready",
                "reasons": ["complex table task"],
            }
        },
        "extracted": {
            "content_summary": {"item_count": 3, "page_count": 1},
            "sections": [{"level": 1, "title": "Summary", "text": "Revenue increased."}],
            "tables": [{"headers": ["Item", "Value"], "rows": [["Revenue", "100"]], "row_count": 1, "column_count": 2}],
            "key_values": [{"key": "Revenue", "value": "100"}],
            "field_evidence": [{"key": "Revenue", "confidence": 0.9, "evidence_text": "Revenue 100", "provenance": {"page_no": 1}}],
            "task_result": {"answers": {"Revenue": "100"}},
        },
        "quality": {"status": "pass", "score": 96, "issues": []},
        "recovery_decision": {"decision": "accept", "selected_attempt": "initial", "attempts": []},
        "retrieval_export": {"stats": {"total_chunks": 2, "by_type": {"text": 2}, "pages": [1]}},
    }

    package = build_document_skill_package(result=result, output_dir=tmp_path / "document_skill")

    skill_path = Path(package["files"]["skill"])
    overview_path = Path(package["files"]["overview"])
    raw_path = Path(package["files"]["raw_result"])

    assert skill_path.exists()
    assert overview_path.exists()
    assert raw_path.exists()
    assert "name: document-report-abc123" in skill_path.read_text(encoding="utf-8")
    assert "description: Use this skill" in skill_path.read_text(encoding="utf-8")
    assert "selected runner: `precise-api`".lower() in overview_path.read_text(encoding="utf-8").lower()
    assert json.loads(raw_path.read_text(encoding="utf-8"))["run_id"] == "abc123"
    assert package["loading_policy"]["default_context"] == ["name", "description"]
