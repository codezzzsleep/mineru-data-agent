from __future__ import annotations

import ast
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "submission_artifacts" / "code_quality"
SCAN_DIRS = ("src", "scripts", "tests")


def main() -> None:
    report = build_report()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "code_quality_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (OUT_DIR / "code_quality_report.md").write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"out_dir": display_path(OUT_DIR), "python_files": report["aggregate"]["python_files"]}, ensure_ascii=False))


def build_report() -> dict[str, Any]:
    files = [path for dirname in SCAN_DIRS for path in (PROJECT_ROOT / dirname).rglob("*.py")]
    files = [path for path in files if "__pycache__" not in path.parts]
    file_rows = [summarize_file(path) for path in sorted(files)]
    by_area: dict[str, dict[str, Any]] = {}
    for area in SCAN_DIRS:
        rows = [row for row in file_rows if row["area"] == area]
        by_area[area] = {
            "python_files": len(rows),
            "physical_lines": sum(row["physical_lines"] for row in rows),
            "code_lines": sum(row["code_lines"] for row in rows),
            "classes": sum(row["classes"] for row in rows),
            "functions": sum(row["functions"] for row in rows),
            "test_functions": sum(row["test_functions"] for row in rows),
        }
    workflow_files = sorted((PROJECT_ROOT / ".github" / "workflows").glob("*.yml"))
    coverage = load_json(PROJECT_ROOT / "submission_artifacts" / "coverage" / "coverage_report.json")
    coverage_aggregate = coverage.get("aggregate", {}) if isinstance(coverage, dict) else {}
    coverage_measured = bool(coverage_aggregate.get("measured"))
    return {
        "schema_version": "2026-05-24",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "scope": "Static repository quality summary generated from local files.",
        "aggregate": {
            "python_files": len(file_rows),
            "physical_lines": sum(row["physical_lines"] for row in file_rows),
            "code_lines": sum(row["code_lines"] for row in file_rows),
            "classes": sum(row["classes"] for row in file_rows),
            "functions": sum(row["functions"] for row in file_rows),
            "test_functions": sum(row["test_functions"] for row in file_rows),
            "test_files": sum(1 for row in file_rows if row["area"] == "tests"),
            "workflow_files": [display_path(path) for path in workflow_files],
            "coverage_measured": coverage_measured,
            "line_coverage_percent": coverage_aggregate.get("line_coverage_percent") if coverage_measured else None,
            "coverage_report": "submission_artifacts/coverage/coverage_report.md" if coverage_measured else None,
        },
        "by_area": by_area,
        "largest_files": sorted(file_rows, key=lambda row: row["code_lines"], reverse=True)[:12],
        "test_modules": [row for row in file_rows if row["area"] == "tests"],
        "notes": [
            "This report counts files, lines, functions, tests, and CI workflow files. It reads coverage output when present but does not itself run coverage.",
            "Run `python scripts/build_coverage_report.py` before this script to refresh line coverage.",
            "The GitHub Actions workflow is in `.github/workflows/tests.yml`; the current CI status should be checked on GitHub for the submitted commit.",
        ],
    }


def summarize_file(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    tree = ast.parse(text, filename=str(path))
    counts = Counter(type(node).__name__ for node in ast.walk(tree))
    test_functions = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
            test_functions += 1
    return {
        "path": display_path(path),
        "area": path.relative_to(PROJECT_ROOT).parts[0],
        "physical_lines": len(lines),
        "code_lines": sum(1 for line in lines if line.strip() and not line.lstrip().startswith("#")),
        "classes": counts["ClassDef"],
        "functions": counts["FunctionDef"] + counts["AsyncFunctionDef"],
        "test_functions": test_functions,
    }


def render_markdown(report: dict[str, Any]) -> str:
    aggregate = report["aggregate"]
    lines = [
        "# Code Quality Report",
        "",
        report["scope"],
        "",
        "## Aggregate",
        "",
        f"- Python files: {aggregate['python_files']}",
        f"- Physical lines: {aggregate['physical_lines']}",
        f"- Code lines: {aggregate['code_lines']}",
        f"- Classes: {aggregate['classes']}",
        f"- Functions: {aggregate['functions']}",
        f"- Test files: {aggregate['test_files']}",
        f"- Test functions: {aggregate['test_functions']}",
        f"- CI workflows: `{json.dumps(aggregate['workflow_files'], ensure_ascii=False)}`",
        f"- Coverage measured: {str(aggregate['coverage_measured']).lower()}",
        f"- Line coverage: {aggregate.get('line_coverage_percent')}",
        f"- Coverage report: `{aggregate.get('coverage_report')}`",
        "",
        "## By Area",
        "",
        "| Area | Files | Physical Lines | Code Lines | Classes | Functions | Test Functions |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for area, row in report["by_area"].items():
        lines.append(
            f"| {area} | {row['python_files']} | {row['physical_lines']} | {row['code_lines']} | "
            f"{row['classes']} | {row['functions']} | {row['test_functions']} |"
        )
    lines.extend(
        [
            "",
            "## Largest Python Files",
            "",
            "| File | Area | Code Lines | Functions | Classes |",
            "| --- | --- | ---: | ---: | ---: |",
        ]
    )
    for row in report["largest_files"]:
        lines.append(f"| `{row['path']}` | {row['area']} | {row['code_lines']} | {row['functions']} | {row['classes']} |")
    lines.extend(["", "## Test Modules", "", "| File | Tests |", "| --- | ---: |"])
    for row in report["test_modules"]:
        lines.append(f"| `{row['path']}` | {row['test_functions']} |")
    lines.extend(["", "## Notes", ""])
    lines.extend(f"- {item}" for item in report["notes"])
    lines.append("")
    return "\n".join(lines)


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


if __name__ == "__main__":
    main()
