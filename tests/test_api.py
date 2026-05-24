from pathlib import Path
import time

from fastapi.testclient import TestClient

from mineru_data_agent import api as api_module
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
    assert data["execution_control"]["strict_page_provenance"]["enabled"] is False


def test_parse_api_accepts_strict_page_provenance_for_native_input(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MINERU_DATA_AGENT_ALLOWED_OUTPUT_BASE", str(tmp_path))
    client = TestClient(app)
    response = client.post(
        "/v1/parse",
        data={
            "task": "抽取报告日期",
            "profile": "general_document",
            "strict_page_provenance": "true",
            "output_root": str(tmp_path / "api_runs"),
        },
        files={
            "file": (
                "report.html",
                "<html><body><h1>日报</h1><p>报告日期：2026-05-22</p></body></html>",
                "text/html",
            )
        },
    )

    assert response.status_code == 200
    gate = response.json()["execution_control"]["strict_page_provenance"]
    assert gate["enabled"] is True
    assert gate["required"] is False
    assert gate["satisfied"] is True


def test_async_parse_job_exposes_status_and_result(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MINERU_DATA_AGENT_ALLOWED_OUTPUT_BASE", str(tmp_path))
    client = TestClient(app)
    response = client.post(
        "/v1/jobs",
        data={
            "task": "异步抽取报告日期",
            "profile": "general_document",
            "output_root": str(tmp_path / "api_jobs"),
        },
        files={
            "file": (
                "report.html",
                "<html><body><h1>日报</h1><p>报告日期：2026-05-23</p></body></html>",
                "text/html",
            )
        },
    )

    assert response.status_code == 202
    job_id = response.json()["job_id"]
    status = {}
    for _ in range(30):
        status_response = client.get(f"/v1/jobs/{job_id}")
        assert status_response.status_code == 200
        status = status_response.json()
        if status["status"] == "completed":
            break
        time.sleep(0.05)

    assert status["status"] == "completed"
    assert status["result"]["extracted"]["key_value_map"]["报告日期"] == "2026-05-23"
    assert Path(status["result"]["trace_path"]).exists()
    assert Path(status["job_path"]).exists()


def test_async_parse_job_reports_not_found() -> None:
    client = TestClient(app)
    response = client.get("/v1/jobs/missing-job")

    assert response.status_code == 404
    assert response.json()["detail"]["error"] == "job_not_found"


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


def test_parse_api_failure_returns_trace_path(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MINERU_DATA_AGENT_ALLOWED_OUTPUT_BASE", str(tmp_path))
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    client = TestClient(app)
    response = client.post(
        "/v1/parse",
        data={
            "task": "解析文档",
            "llm": "deepseek",
            "output_root": str(tmp_path / "api_runs"),
        },
        files={"file": ("report.html", "<html><body>ok</body></html>", "text/html")},
    )

    assert response.status_code == 500
    detail = response.json()["detail"]
    assert detail["error"] == "parse_failed"
    assert Path(detail["trace_path"]).exists()
    assert detail["run_id"]


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


def test_api_fallback_runner_skips_when_cli_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(api_module, "resolve_mineru_executable", lambda executable=None: None)

    runner = api_module._build_fallback_runner(
        runner="agent-api",
        enabled=True,
        fallback_mineru_executable=None,
        mineru_executable=None,
    )

    assert runner is None


def test_api_fallback_runner_uses_explicit_executable(monkeypatch) -> None:
    monkeypatch.setattr(api_module, "resolve_mineru_executable", lambda executable=None: executable)

    runner = api_module._build_fallback_runner(
        runner="agent-api",
        enabled=True,
        fallback_mineru_executable="/opt/mineru/bin/mineru",
        mineru_executable=None,
    )

    assert runner is not None
    assert runner.executable == "/opt/mineru/bin/mineru"
