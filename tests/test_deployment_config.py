from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_project_docs_are_cli_first() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    cli_contract = (PROJECT_ROOT / "docs" / "CLI_CONTRACT.md").read_text(encoding="utf-8")
    workflow = (PROJECT_ROOT / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")

    assert "CLI-first" in readme
    assert "stable review" in readme
    assert "data-agent run" in cli_contract
    assert "data-agent batch" in cli_contract
    assert "data-agent agent-run" in cli_contract
    assert "CLI smoke" in workflow
    assert "API performance smoke" not in workflow
    assert "Docker build smoke" not in workflow


def test_ignore_files_exclude_local_artifacts() -> None:
    gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
    dockerignore = (PROJECT_ROOT / ".dockerignore").read_text(encoding="utf-8")

    for expected in ["logs/", "review_exchange/", "examples/real_world_docs/", ".env", "*.zip"]:
        assert expected in gitignore
    for expected in ["logs", "review_exchange", "examples/real_world_docs", ".env", "*.zip"]:
        assert expected in dockerignore


def test_public_api_docs_mark_dangerous_fields_as_server_side() -> None:
    contract = (PROJECT_ROOT / "docs" / "API_CONTRACT.md").read_text(encoding="utf-8")
    deployment = (PROJECT_ROOT / "docs" / "DEPLOYMENT_AND_API.md").read_text(encoding="utf-8")

    assert "optional local HTTP wrapper" in contract
    assert "CLI-first" in deployment
    assert "request_field_not_allowed" in contract
    assert "llm_base_url" in contract
    assert "mineru_executable" in contract
    assert "fallback_mineru_executable" in contract
    assert "HTTP API 不接受" in deployment
    assert "只能由服务端环境变量或本地 CLI 参数配置" in deployment
