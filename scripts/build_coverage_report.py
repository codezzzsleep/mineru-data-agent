from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "submission_artifacts" / "coverage"
RAW_JSON = OUT_DIR / "coverage_raw.json"
OUT_JSON = OUT_DIR / "coverage_report.json"
OUT_MD = OUT_DIR / "coverage_report.md"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report = build_report()
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_MD.write_text(render_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "out_dir": display_path(OUT_DIR),
                "measured": report["aggregate"]["measured"],
                "line_coverage_percent": report["aggregate"].get("line_coverage_percent"),
            },
            ensure_ascii=False,
        )
    )
    if not report["aggregate"]["measured"]:
        raise SystemExit(1)


def build_report() -> dict[str, Any]:
    commands: list[dict[str, Any]] = []
    measured = False
    raw: dict[str, Any] | None = None
    failure: str | None = None

    for command in [
        [sys.executable, "-m", "coverage", "erase"],
        [sys.executable, "-m", "coverage", "run", "--source", "src/mineru_data_agent", "-m", "pytest", "-q"],
        [sys.executable, "-m", "coverage", "json", "-o", display_path(RAW_JSON)],
    ]:
        record = run_command(command)
        commands.append(record)
        if record["returncode"] != 0:
            failure = f"command_failed: {' '.join(command[1:])}"
            break

    if failure is None:
        try:
            raw = json.loads(RAW_JSON.read_text(encoding="utf-8"))
            measured = True
        except Exception as exc:
            failure = f"coverage_json_unreadable: {exc!r}"

    totals = raw.get("totals", {}) if isinstance(raw, dict) else {}
    files = raw.get("files", {}) if isinstance(raw, dict) else {}
    file_rows = summarize_files(files) if isinstance(files, dict) else []
    return {
        "schema_version": "2026-05-24",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "scope": "Line coverage measured by coverage.py while running the local pytest suite.",
        "aggregate": {
            "measured": measured,
            "line_coverage_percent": round(float(totals.get("percent_covered") or 0.0), 2) if measured else None,
            "covered_lines": totals.get("covered_lines"),
            "num_statements": totals.get("num_statements"),
            "missing_lines": totals.get("missing_lines"),
            "excluded_lines": totals.get("excluded_lines"),
            "pytest_command": f"{Path(sys.executable).name} -m coverage run --source src/mineru_data_agent -m pytest -q",
            "failure": failure,
        },
        "commands": commands,
        "files": file_rows,
        "lowest_coverage_files": sorted(file_rows, key=lambda row: row["line_coverage_percent"])[:12],
        "notes": [
            "This is source line coverage for the local test suite, not a live MinerU/LLM/GPU integration benchmark.",
            "The measured denominator is `src/mineru_data_agent`; scripts are excluded from the coverage target.",
            "Use the raw coverage JSON for exact missing-line lists.",
        ],
        "raw_coverage_json": display_path(RAW_JSON) if RAW_JSON.exists() else None,
    }


def run_command(command: list[str]) -> dict[str, Any]:
    started = perf_counter()
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return {
        "command": " ".join(command[1:]) if command and command[0] == sys.executable else " ".join(command),
        "returncode": completed.returncode,
        "elapsed_seconds": round(perf_counter() - started, 3),
        "stdout_tail": completed.stdout[-2000:],
        "stderr_tail": completed.stderr[-2000:],
    }


def summarize_files(files: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path, payload in files.items():
        if not isinstance(payload, dict):
            continue
        summary = payload.get("summary", {}) if isinstance(payload.get("summary"), dict) else {}
        rows.append(
            {
                "path": path.replace("\\", "/"),
                "line_coverage_percent": round(float(summary.get("percent_covered") or 0.0), 2),
                "covered_lines": summary.get("covered_lines"),
                "num_statements": summary.get("num_statements"),
                "missing_lines": summary.get("missing_lines"),
                "excluded_lines": summary.get("excluded_lines"),
            }
        )
    return sorted(rows, key=lambda row: row["path"])


def render_markdown(report: dict[str, Any]) -> str:
    aggregate = report["aggregate"]
    lines = [
        "# Coverage Report",
        "",
        report["scope"],
        "",
        "## Aggregate",
        "",
        f"- Measured: {str(aggregate['measured']).lower()}",
        f"- Line coverage: {aggregate.get('line_coverage_percent')}%",
        f"- Covered lines: {aggregate.get('covered_lines')}",
        f"- Statements: {aggregate.get('num_statements')}",
        f"- Missing lines: {aggregate.get('missing_lines')}",
        f"- Pytest command: `{aggregate.get('pytest_command')}`",
    ]
    if aggregate.get("failure"):
        lines.append(f"- Failure: `{aggregate['failure']}`")
    lines.extend(
        [
            "",
            "## Lowest Coverage Files",
            "",
            "| File | Coverage | Statements | Missing |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for row in report["lowest_coverage_files"]:
        lines.append(
            f"| `{row['path']}` | {row['line_coverage_percent']}% | {row['num_statements']} | {row['missing_lines']} |"
        )
    lines.extend(
        [
            "",
            "## Command Log",
            "",
            "| Command | Exit | Seconds |",
            "| --- | ---: | ---: |",
        ]
    )
    for command in report["commands"]:
        lines.append(f"| `{command['command']}` | {command['returncode']} | {command['elapsed_seconds']} |")
    lines.extend(["", "## Notes", ""])
    lines.extend(f"- {item}" for item in report["notes"])
    lines.append("")
    return "\n".join(lines)


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


if __name__ == "__main__":
    main()
