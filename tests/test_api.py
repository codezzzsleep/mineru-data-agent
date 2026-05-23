from pathlib import Path

from fastapi.testclient import TestClient

from mineru_data_agent.api import app


def test_parse_api_keeps_trace_files(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MINERU_DATA_AGENT_ALLOWED_OUTPUT_BASE", str(tmp_path))
    client = TestClient(app)
    response = client.post(
        "/v1/parse",
        data={
            "task": "抽取报告日期和处理建议",
            "profile": "general_document",
            "output_root": str(tmp_path / "api_runs"),
        },
        files={
            "file": (
                "report.html",
                "<html><body><h1>日报</h1><p>报告日期：2026-05-22</p><p>处理建议：复查。</p></body></html>",
                "text/html",
            )
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert Path(data["trace_path"]).exists()
    assert Path(data["summary_path"]).exists()
    assert Path(data["artifacts"]["markdown_path"]).exists()
    assert data["api_output_root"] == str((tmp_path / "api_runs").resolve())


def test_parse_api_rejects_invalid_runner() -> None:
    client = TestClient(app)
    response = client.post(
        "/v1/parse",
        data={"task": "解析文档", "runner": "bad-runner"},
        files={"file": ("report.html", "<html><body>ok</body></html>", "text/html")},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "invalid_runner"


def test_parse_api_rejects_invalid_llm() -> None:
    client = TestClient(app)
    response = client.post(
        "/v1/parse",
        data={"task": "解析文档", "llm": "unknown"},
        files={"file": ("report.html", "<html><body>ok</body></html>", "text/html")},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "invalid_llm"


def test_parse_api_rejects_oversized_upload(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MINERU_DATA_AGENT_ALLOWED_OUTPUT_BASE", str(tmp_path))
    monkeypatch.setenv("MINERU_DATA_AGENT_MAX_UPLOAD_BYTES", "8")
    client = TestClient(app)
    response = client.post(
        "/v1/parse",
        data={"task": "解析文档", "output_root": str(tmp_path / "api_runs")},
        files={"file": ("report.html", "<html><body>too large</body></html>", "text/html")},
    )

    assert response.status_code == 413
    assert response.json()["detail"]["error"] == "upload_too_large"


def test_parse_api_rejects_output_root_outside_allowed_base(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MINERU_DATA_AGENT_ALLOWED_OUTPUT_BASE", str(tmp_path / "allowed"))
    client = TestClient(app)
    response = client.post(
        "/v1/parse",
        data={"task": "解析文档", "output_root": str(tmp_path / "outside")},
        files={"file": ("report.html", "<html><body>ok</body></html>", "text/html")},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "output_root_outside_allowed_base"
