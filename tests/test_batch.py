import json

from mineru_data_agent.agent import MinerUDataAgent
from mineru_data_agent.batch import run_batch


def test_run_batch_continues_after_failure(tmp_path) -> None:
    html_path = tmp_path / "demo.html"
    html_path.write_text("<h1>Demo</h1><p>value: 42</p>", encoding="utf-8")
    manifest_path = tmp_path / "batch.json"
    manifest_path.write_text(
        json.dumps(
            {
                "tasks": [
                    {"id": "html_demo", "input": str(html_path), "task": "clean html"},
                    {"input": str(tmp_path / "missing.pdf"), "task": "missing file"},
                ]
            }
        ),
        encoding="utf-8",
    )

    report = run_batch(
        manifest_path=manifest_path,
        output_root=tmp_path / "runs",
        agent=MinerUDataAgent(),
    )

    assert report["total"] == 2
    assert report["completed"] == 1
    assert report["failed"] == 1
    assert report["items"][0]["status"] == "completed"
    assert report["items"][0]["id"] == "html_demo"
    assert report["items"][1]["status"] == "failed"
    assert (tmp_path / "runs" / "batch_report.json").exists()


def test_run_batch_resolves_relative_inputs_from_manifest_dir(tmp_path, monkeypatch) -> None:
    manifest_dir = tmp_path / "manifest_dir"
    input_dir = manifest_dir / "inputs"
    input_dir.mkdir(parents=True)
    html_path = input_dir / "demo.html"
    html_path.write_text("<h1>Demo</h1><p>value: 42</p>", encoding="utf-8")
    manifest_path = manifest_dir / "batch.json"
    manifest_path.write_text(
        json.dumps({"tasks": [{"id": "relative_html", "input": "inputs/demo.html", "task": "clean html"}]}),
        encoding="utf-8",
    )
    other_cwd = tmp_path / "other"
    other_cwd.mkdir()
    monkeypatch.chdir(other_cwd)

    report = run_batch(
        manifest_path=manifest_path,
        output_root=tmp_path / "runs",
        agent=MinerUDataAgent(),
    )

    assert report["completed"] == 1
    assert report["items"][0]["status"] == "completed"
    assert report["items"][0]["resolved_input"] == str(html_path.resolve())


def test_run_batch_passes_page_range_and_source_metadata(tmp_path) -> None:
    pdf_path = tmp_path / "archive.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    manifest_path = tmp_path / "batch.json"
    manifest_path.write_text(
        json.dumps(
            {
                "tasks": [
                    {
                        "id": "chunk_1",
                        "input": str(pdf_path),
                        "source_file": "archive.pdf",
                        "page_range": "1-200",
                        "start_page": 1,
                        "end_page": 200,
                        "task": "chunk parse",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    calls = {}

    class FakeAgent:
        def run(self, input_file, output_root, **kwargs):
            calls["input_file"] = input_file
            calls["output_root"] = output_root
            calls.update(kwargs)
            out = tmp_path / "fake_run"
            out.mkdir()
            return type(
                "Result",
                (),
                {
                    "run_id": "abc123",
                    "output_dir": str(out),
                    "trace_path": str(out / "trace.json"),
                    "summary_path": str(out / "summary.md"),
                    "quality": {"status": "pass", "score": 90},
                    "retrieval_export": {"chunks_path": str(out / "retrieval.jsonl")},
                },
            )()

    report = run_batch(manifest_path=manifest_path, output_root=tmp_path / "runs", agent=FakeAgent())

    assert calls["start_page"] == 1
    assert calls["end_page"] == 200
    assert report["items"][0]["source_file"] == "archive.pdf"
    assert report["items"][0]["page_range"] == "1-200"


def test_run_batch_records_runtime_harness_gate(tmp_path) -> None:
    pdf_path = tmp_path / "table.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    manifest_path = tmp_path / "batch.json"
    manifest_path.write_text(
        json.dumps({"tasks": [{"id": "table", "input": str(pdf_path), "task": "parse table"}]}),
        encoding="utf-8",
    )

    class FakeAgent:
        def run(self, input_file, output_root, **kwargs):
            out = tmp_path / "fake_run"
            out.mkdir(exist_ok=True)
            return type(
                "Result",
                (),
                {
                    "run_id": "abc123",
                    "output_dir": str(out),
                    "trace_path": str(out / "trace.json"),
                    "summary_path": str(out / "summary.md"),
                    "quality": {"status": "pass", "score": 90},
                    "retrieval_export": {"chunks_path": str(out / "retrieval.jsonl")},
                    "execution_control": {
                        "harness_gate": {
                            "blocked": True,
                            "initial_decision": "local-pdf-text",
                            "target": "precise-api",
                            "reason": "table risk",
                        }
                    },
                },
            )()

    seen = []
    report = run_batch(
        manifest_path=manifest_path,
        output_root=tmp_path / "runs",
        agent=FakeAgent(),
        progress_callback=seen.append,
    )

    assert report["items"][0]["harness_gate"]["blocked"] is True
    assert seen[0]["harness_gate"]["target"] == "precise-api"
