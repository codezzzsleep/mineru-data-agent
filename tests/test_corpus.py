from pathlib import Path

from mineru_data_agent.corpus import build_corpus_catalog, load_document_reference, search_corpus_catalog
from mineru_data_agent.skill_exporter import build_document_skill_package


def test_build_search_and_load_corpus_catalog(tmp_path: Path) -> None:
    result = {
        "run_id": "abc123",
        "task": "整理近代史资料",
        "profile": "general_document",
        "input_file": str(tmp_path / "history.pdf"),
        "schema_version": "2026-05-24",
        "execution_control": {},
        "extracted": {
            "content_summary": {"item_count": 2, "page_count": 3},
            "sections": [{"level": 1, "title": "太行根据地", "text": "兵工材料与民兵组织"}],
            "tables": [],
            "key_values": [],
            "field_evidence": [],
        },
        "quality": {"status": "pass", "score": 90, "issues": []},
        "recovery_decision": {"decision": "accept", "selected_attempt": "initial", "attempts": []},
        "retrieval_export": {"stats": {"total_chunks": 1, "by_type": {"text": 1}, "pages": [1]}},
    }
    package = build_document_skill_package(
        result=result,
        output_dir=tmp_path / "doc1" / "document_skill",
        understanding={
            "name": "taihang-history",
            "description": "太行根据地兵工材料、民兵组织与抗战史料。",
            "compressed": "这份资料概述太行根据地的兵工材料、民兵组织和抗战时期基层动员。",
            "topics": ["太行根据地", "兵工材料"],
        },
        full_markdown="# 太行根据地\n\n兵工材料与民兵组织",
    )

    catalog = build_corpus_catalog(root=tmp_path, output_dir=tmp_path / "catalog")

    assert catalog["total_documents"] == 1
    assert catalog["entries"][0]["name"] == "taihang-history"
    hits = search_corpus_catalog(catalog_path=Path(catalog["files"]["catalog_json"]), query="民兵 兵工")
    assert hits[0]["name"] == "taihang-history"
    loaded = load_document_reference(package_dir=Path(package["package_dir"]), reference="compressed")
    assert loaded["ok"] is True
    assert "太行根据地" in loaded["content"]
