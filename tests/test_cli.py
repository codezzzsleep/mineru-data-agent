import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from mineru_data_agent import cli as cli_module


def test_cli_fallback_runner_skips_when_cli_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(cli_module, "resolve_mineru_executable", lambda executable=None: None)
    args = SimpleNamespace(
        runner="agent-api",
        cli_fallback_on_no_page_provenance=True,
        fallback_mineru_executable=None,
        mineru_executable=None,
    )

    assert cli_module._build_fallback_runner(args) is None


def test_cli_fallback_runner_uses_explicit_executable(monkeypatch) -> None:
    monkeypatch.setattr(cli_module, "resolve_mineru_executable", lambda executable=None: executable)
    args = SimpleNamespace(
        runner="agent-api",
        cli_fallback_on_no_page_provenance=True,
        fallback_mineru_executable="/opt/mineru/bin/mineru",
        mineru_executable=None,
    )

    runner = cli_module._build_fallback_runner(args)

    assert runner is not None
    assert runner.executable == "/opt/mineru/bin/mineru"


def test_cli_parser_accepts_strict_page_provenance() -> None:
    args = cli_module.build_parser().parse_args(
        [
            "run",
            "--input",
            "sample.pdf",
            "--out",
            "runs",
            "--task",
            "extract with page evidence",
            "--strict-page-provenance",
        ]
    )

    assert args.strict_page_provenance is True


def test_cli_parser_accepts_agent_run() -> None:
    args = cli_module.build_parser().parse_args(
        [
            "agent-run",
            "--input",
            "sample.html",
            "--out",
            "runs/agent_live",
            "--task",
            "extract live evidence",
            "--provider",
            "deepseek",
            "--max-turns",
            "6",
            "--max-tokens",
            "512",
        ]
    )

    assert args.command == "agent-run"
    assert args.provider == "deepseek"
    assert args.max_turns == 6
    assert args.max_tokens == 512


def test_cli_agent_run_invokes_live_agent(monkeypatch, capsys, tmp_path: Path) -> None:
    input_path = tmp_path / "input.html"
    input_path.write_text("<html><body>ok</body></html>", encoding="utf-8")
    captured: dict[str, object] = {}

    def fake_run_live_agent(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(run_id="abc123")

    def fake_jsonable(trace, **kwargs):
        return {"run_id": trace.run_id, "agent_mode": "live_tool_calling", "tool_call_completed": True}

    monkeypatch.setattr(cli_module, "run_live_agent", fake_run_live_agent)
    monkeypatch.setattr(cli_module, "live_trace_to_jsonable", fake_jsonable)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "data-agent",
            "agent-run",
            "--input",
            str(input_path),
            "--out",
            str(tmp_path / "runs"),
            "--task",
            "extract live evidence",
            "--provider",
            "modelscope",
        ],
    )

    cli_module.main()

    data = json.loads(capsys.readouterr().out)
    assert data == {"run_id": "abc123", "agent_mode": "live_tool_calling", "tool_call_completed": True}
    assert captured["input_file"] == input_path
    assert captured["output_root"] == tmp_path / "runs"
    assert captured["task"] == "extract live evidence"
    assert captured["provider"] == "modelscope"
    assert "base_url" not in captured
    assert "api_key" not in captured


def test_cli_agent_run_rejects_excessive_limits() -> None:
    with pytest.raises(SystemExit):
        cli_module._validate_live_agent_limits(31, 1024, 60.0)
    with pytest.raises(SystemExit):
        cli_module._validate_live_agent_limits(12, 4097, 60.0)
    with pytest.raises(SystemExit):
        cli_module._validate_live_agent_limits(12, 1024, 601.0)
