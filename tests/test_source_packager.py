from __future__ import annotations

import json
from pathlib import Path

from mineru_data_agent.source_packager import build_source_document_packages


def test_package_sources_merges_chunk_runs_by_original_source(tmp_path: Path) -> None:
    source_root = tmp_path / "史料part"
    source_root.mkdir()
    (source_root / "archive.pdf").write_bytes(b"%PDF-1.4")
    run_root = tmp_path / "runs" / "raw"
    run_root.mkdir(parents=True)
    chunks_dir = run_root / "chunks"
    chunks_dir.mkdir()
    chunk_inputs = [
        chunks_dir / "archive__pages_001-002.pdf",
        chunks_dir / "archive__pages_003-004.pdf",
    ]
    for input_path in chunk_inputs:
        input_path.write_bytes(b"%PDF-1.4")

    items = []
    chunk_plan = []
    for index, input_path in enumerate(chunk_inputs, start=1):
        run_id = f"run{index}"
        output_dir = run_root / "chunk_outputs" / run_id
        _write_minimal_run(
            output_dir,
            run_id=run_id,
            input_file=input_path,
            page_no=1,
            description=f"archive part {index}",
        )
        page_range = "1-2" if index == 1 else "3-4"
        item = {
            "id": f"scan_{index:02d}",
            "source": input_path.name,
            "status": "completed",
            "output_dir": str(output_dir),
            "result_path": str(output_dir / "result.json"),
            "summary_path": str(output_dir / "summary.md"),
            "retrieval_chunks_path": str(output_dir / "retrieval" / "retrieval_chunks.jsonl"),
            "skill_package_dir": str(output_dir / "document_skill"),
            "quality_status": "pass",
            "quality_score": 90 + index,
        }
        items.append(item)
        chunk_plan.append(
            {
                "id": item["id"],
                "source_file": "archive.pdf",
                "page_range": page_range,
                "input": str(input_path),
            }
        )
    (run_root / "run_summary.json").write_text(
        json.dumps({"items": items}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (run_root / "scan_chunk_plan.json").write_text(
        json.dumps({"chunks": chunk_plan}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    report = build_source_document_packages(run_root=run_root, source_root=source_root, output_root=tmp_path / "packaged")

    assert report["total_source_documents"] == 1
    assert report["merged_scanned_packages"] == 1
    doc_dir = Path(report["document_root"]) / "archive"
    assert (doc_dir / "result.json").exists()
    assert (doc_dir / "summary.md").exists()
    assert (doc_dir / "trace.json").exists()
    assert (doc_dir / "retrieval" / "retrieval_chunks.jsonl").exists()
    assert (doc_dir / "document_skill" / "SKILL.md").exists()
    assert (doc_dir / "document_skill" / "references" / "compressed.md").exists()
    result = json.loads((doc_dir / "result.json").read_text(encoding="utf-8"))
    assert result["source_document_name"] == "archive.pdf"
    assert len(result["source_runs"]) == 2
    merged_lines = (doc_dir / "retrieval" / "retrieval_chunks.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(merged_lines) == 2
    assert json.loads(merged_lines[1])["page_no"] == 3
    assert not report["records"][0]["missing_standard_files"]


def test_package_sources_reads_batch_report_source_metadata(tmp_path: Path) -> None:
    source_root = tmp_path / "史料part"
    source_root.mkdir()
    (source_root / "archive.pdf").write_bytes(b"%PDF-1.4")
    run_root = tmp_path / "runs" / "raw"
    run_root.mkdir(parents=True)
    items = []
    for index, page_range in enumerate(["1-200", "201-220"], start=1):
        output_dir = run_root / f"run_{index}"
        _write_minimal_run(
            output_dir,
            run_id=f"run{index}",
            input_file=source_root / "archive.pdf",
            page_no=1,
            description=f"part {index}",
        )
        items.append(
            {
                "id": f"doc_{index:03d}",
                "status": "completed",
                "source_file": "archive.pdf",
                "page_range": page_range,
                "output_dir": str(output_dir),
                "result_path": str(output_dir / "result.json"),
                "summary_path": str(output_dir / "summary.md"),
                "retrieval_chunks_path": str(output_dir / "retrieval" / "retrieval_chunks.jsonl"),
                "skill_package_dir": str(output_dir / "document_skill"),
                "quality_status": "pass",
                "quality_score": 90,
            }
        )
    (run_root / "batch_report.json").write_text(json.dumps({"items": items}, ensure_ascii=False), encoding="utf-8")

    report = build_source_document_packages(run_root=run_root, source_root=source_root, output_root=tmp_path / "packaged")

    doc_dir = Path(report["document_root"]) / "archive"
    result = json.loads((doc_dir / "result.json").read_text(encoding="utf-8"))
    assert report["total_source_documents"] == 1
    assert len(result["source_runs"]) == 2
    assert [item["page_range"] for item in result["source_runs"]] == ["1-200", "201-220"]


def _write_minimal_run(output_dir: Path, *, run_id: str, input_file: Path, page_no: int, description: str) -> None:
    references = output_dir / "document_skill" / "references"
    retrieval = output_dir / "retrieval"
    references.mkdir(parents=True)
    retrieval.mkdir(parents=True)
    result = {
        "run_id": run_id,
        "input_file": str(input_file),
        "task": "整理资料",
        "profile": "low_quality_ocr",
        "quality": {"status": "pass", "score": 95, "issues": []},
        "retrieval_export": {
            "chunks_path": str(retrieval / "retrieval_chunks.jsonl"),
            "stats": {"total_chunks": 1, "by_type": {"text": 1}, "pages": [page_no]},
        },
        "skill_package": {"package_dir": str(output_dir / "document_skill")},
    }
    (output_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    (output_dir / "summary.md").write_text(f"# {run_id}\n", encoding="utf-8")
    (output_dir / "trace.json").write_text(json.dumps({"run_id": run_id}), encoding="utf-8")
    (retrieval / "retrieval_chunks.jsonl").write_text(
        json.dumps({"chunk_id": run_id, "page_no": page_no, "pages": [page_no], "content_type": "text", "chunk_text": description}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output_dir / "document_skill" / "SKILL.md").write_text(
        f"---\nname: {run_id}\ndescription: {description}\n---\n",
        encoding="utf-8",
    )
    for name in ["compressed.md", "content.md", "overview.md", "structured.md", "evidence.md", "segments.md", "tables.md"]:
        (references / name).write_text(f"# {name}\n\n{description}\n", encoding="utf-8")
