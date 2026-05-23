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
