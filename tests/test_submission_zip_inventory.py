from __future__ import annotations

import os
import zipfile
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


REQUIRED_ZIP_ENTRIES = {
    "README.md",
    "技术报告.md",
    "pyproject.toml",
    ".github/workflows/tests.yml",
    "src/mineru_data_agent/cli.py",
    "src/mineru_data_agent/agent.py",
    "src/mineru_data_agent/agent_live.py",
    "tests/test_cli.py",
    "tests/test_agent_live.py",
    "docs/技术报告.md",
    "docs/TECHNICAL_REPORT.md",
    "docs/CLI_CONTRACT.md",
    "docs/LIVE_LLM_RUNBOOK.md",
    "scripts/run_agent_live_cases.py",
    "submission_artifacts/ARTIFACTS_INDEX.md",
    "submission_artifacts/ARTIFACTS_INDEX.json",
    "submission_artifacts/agent_live_cases/agent_live_report.json",
}


FORBIDDEN_ENTRY_PARTS = {
    ".venv",
    ".env",
    "runs",
    "dist",
    "logs",
    "review_exchange",
    "real_world_docs",
    "__pycache__",
}

TEXT_ENTRY_SUFFIXES = {".md", ".json", ".jsonl", ".txt", ".py", ".toml", ".ps1", ".html", ".yml", ".yaml"}
TEXT_ENTRY_NAMES = {".dockerignore", ".gitattributes", ".gitignore", "Dockerfile"}


def _forbidden_local_path_markers() -> set[str]:
    drive_f = "F:"
    drive_c = "C:"
    markers = {
        drive_f + "\\" + "data_agent",
        drive_f + "\\\\" + "data_agent",
        drive_f + "/" + "data_agent",
        drive_c + "\\" + "Users",
        drive_c + "\\\\" + "Users",
        drive_c + "/" + "Users",
    }
    for path in {PROJECT_ROOT, PROJECT_ROOT.parent, Path.home()}:
        raw = str(path)
        markers.update({raw, raw.replace("\\", "\\\\"), raw.replace("\\", "/")})
    return {marker for marker in markers if marker}


def test_submission_zip_script_includes_required_project_areas() -> None:
    script = (PROJECT_ROOT / "scripts" / "make_submission_zip.ps1").read_text(encoding="utf-8")

    for item in [
        "README.md",
        "CONTRIBUTING.md",
        "LICENSE",
        ".github",
        "pyproject.toml",
        "src",
        "docs",
        "examples",
        "scripts",
        "submission_artifacts",
        "tests",
    ]:
        assert f'"{item}"' in script

    for excluded in [".venv", "runs", "dist", "logs", "real_world_docs", "*.log", ".env", "_audit_traces.py"]:
        assert excluded in script


def test_submission_zip_inventory_if_present() -> None:
    zip_path = Path(os.getenv("SUBMISSION_ZIP_PATH", PROJECT_ROOT / "dist" / "mineru-data-agent-submission.zip"))
    if not zip_path.exists():
        pytest.skip("submission zip has not been generated in this environment")

    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())

        assert REQUIRED_ZIP_ENTRIES <= names
        for name in names:
            normalized = name.replace("\\", "/")
            parts = set(normalized.split("/"))
            assert not normalized.startswith("/")
            assert ".." not in parts
            assert ":" not in normalized
            assert not normalized.endswith(".pyc")
            assert not (parts & FORBIDDEN_ENTRY_PARTS), normalized
            if Path(normalized).suffix.lower() in TEXT_ENTRY_SUFFIXES or Path(normalized).name in TEXT_ENTRY_NAMES:
                text = archive.read(name).decode("utf-8", errors="ignore")
                for marker in _forbidden_local_path_markers():
                    assert marker not in text, f"{marker!r} leaked in {normalized}"
