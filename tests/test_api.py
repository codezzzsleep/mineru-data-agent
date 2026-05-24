import json
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


def test_async_parse_job_rejects_invalid_job_id(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MINERU_DATA_AGENT_ALLOWED_OUTPUT_BASE", str(tmp_path))
    client = TestClient(app)
    response = client.get("/v1/jobs/..%5Csecret", params={"output_root": str(tmp_path)})

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "invalid_job_id"


def test_async_parse_job_reports_not_found_for_valid_missing_id() -> None:
    client = TestClient(app)
    response = client.get(f"/v1/jobs/{'0' * 32}")

    assert response.status_code == 404
    assert response.json()["detail"]["error"] == "job_not_found"


def test_async_parse_job_loads_persisted_record(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MINERU_DATA_AGENT_ALLOWED_OUTPUT_BASE", str(tmp_path))
    root = tmp_path / "api_jobs"
    jobs_dir = root / "_jobs"
    jobs_dir.mkdir(parents=True)
    job_id = "a" * 32
    api_module._JOBS.pop(job_id, None)
    record = {
        "job_id": job_id,
        "status": "completed",
        "created_at": "2026-05-25T00:00:00Z",
        "started_at": "2026-05-25T00:00:00Z",
        "ended_at": "2026-05-25T00:00:01Z",
        "input_path": str(root / "_uploads" / "input.html"),
        "output_root": str(root),
        "config": {},
        "result": {"ok": True},
        "error": None,
        "job_path": str(jobs_dir / f"{job_id}.json"),
    }
    (jobs_dir / f"{job_id}.json").write_text(json.dumps(record), encoding="utf-8")
    client = TestClient(app)

    response = client.get(f"/v1/jobs/{job_id}", params={"output_root": str(root)})

    assert response.status_code == 200
    assert response.json()["job_id"] == job_id
    assert response.json()["result"] == {"ok": True}


def test_health_reports_version() -> None:
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "version": api_module.__version__}


def test_http_api_does_not_expose_live_agent_endpoint() -> None:
    client = TestClient(app)
    response = client.post(
        "/v1/agent/parse",
        data={"task": "解析文档"},
        files={"file": ("report.html", "<html><body>ok</body></html>", "text/html")},
    )

    assert response.status_code == 404


def test_parse_api_rejects_request_level_deployment_fields() -> None:
    client = TestClient(app)
    for field in ["llm_base_url", "mineru_executable", "fallback_mineru_executable"]:
        response = client.post(
            "/v1/parse",
            data={"task": "解析文档", field: "https://example.invalid"},
            files={"file": ("report.html", "<html><body>ok</body></html>", "text/html")},
        )

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert detail["error"] == "request_field_not_allowed"
        assert detail["fields"] == [field]



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


def test_parse_api_rejects_invalid_profile_backend_method_lang() -> None:
    client = TestClient(app)
    cases = [
        ({"profile": "unknown"}, "invalid_profile"),
        ({"backend": "bad-backend"}, "invalid_backend"),
        ({"method": "bad-method"}, "invalid_method"),
        ({"lang": "jp"}, "invalid_lang"),
    ]
    for fields, error in cases:
        response = client.post(
            "/v1/parse",
            data={"task": "解析文档", **fields},
            files={"file": ("report.html", "<html><body>ok</body></html>", "text/html")},
        )

        assert response.status_code == 400
        assert response.json()["detail"]["error"] == error


def test_parse_api_rejects_blank_task() -> None:
    client = TestClient(app)
    response = client.post(
        "/v1/parse",
        data={"task": "   "},
        files={"file": ("report.html", "<html><body>ok</body></html>", "text/html")},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "invalid_task"


def test_parse_api_rejects_unsupported_upload_suffix(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MINERU_DATA_AGENT_ALLOWED_OUTPUT_BASE", str(tmp_path))
    client = TestClient(app)
    response = client.post(
        "/v1/parse",
        data={"task": "解析文档", "output_root": str(tmp_path / "api_runs")},
        files={"file": ("report.exe", "not a document", "application/octet-stream")},
    )

    assert response.status_code == 415
    assert response.json()["detail"]["error"] == "unsupported_upload_suffix"


def test_parse_api_rejects_default_output_root_outside_allowed_base(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MINERU_DATA_AGENT_OUTPUT_DIR", str(tmp_path / "outside"))
    monkeypatch.setenv("MINERU_DATA_AGENT_ALLOWED_OUTPUT_BASE", str(tmp_path / "allowed"))
    client = TestClient(app)
    response = client.post(
        "/v1/parse",
        data={"task": "解析文档"},
        files={"file": ("report.html", "<html><body>ok</body></html>", "text/html")},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "output_root_outside_allowed_base"


def test_api_fallback_runner_skips_when_cli_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(api_module, "resolve_mineru_executable", lambda executable=None: None)

    runner = api_module._build_fallback_runner(runner="agent-api", enabled=True)

    assert runner is None


def test_api_fallback_runner_uses_server_configured_executable(monkeypatch) -> None:
    monkeypatch.setattr(api_module, "resolve_mineru_executable", lambda executable=None: "/opt/mineru/bin/mineru")

    runner = api_module._build_fallback_runner(runner="agent-api", enabled=True)

    assert runner is not None
    assert runner.executable == "/opt/mineru/bin/mineru"
