from types import SimpleNamespace

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
