from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mineru_data_agent.agent import MinerUDataAgent
from mineru_data_agent.llm_client import DeepSeekLLMClient, ModelScopeLLMClient
from mineru_data_agent.mineru_client import MinerURunner


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = PROJECT_ROOT / "examples" / "llm_live_cases.json"
RUN_ROOT = PROJECT_ROOT / "runs" / "live_llm_matrix"
DEST_ROOT = PROJECT_ROOT / "submission_artifacts" / "llm_live_matrix"
PROVIDER_KEY_ENVS = {
    "deepseek": "DEEPSEEK_API_KEY",
    "modelscope": "MODELSCOPE_API_KEY",
}
REQUIRED_CASE_FIELDS = {"id", "input", "task"}


def main() -> None:
    args = parse_args()
    cases = select_cases(load_cases(Path(args.manifest)), args.case, args.limit)
    key_env = provider_key_env(args.provider)
    if not os.getenv(key_env):
        if args.write_skip_report:
            write_matrix_report(
                Path(args.output_dir).resolve(),
                build_skip_report(args, cases, key_env),
            )
            print(
                json.dumps(
                    {
                        "status": "skipped_missing_provider_key",
                        "provider": args.provider,
                        "key_env": key_env,
                        "output_dir": display_path(Path(args.output_dir).resolve()),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return
        raise SystemExit(f"{key_env} is required for --provider {args.provider}")

    output_dir = Path(args.output_dir).resolve()
    run_root = Path(args.run_root).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    run_root.mkdir(parents=True, exist_ok=True)
    llm_client = build_llm_client(args)
    records: list[dict[str, Any]] = []

    for case in cases:
        try:
            records.append(run_live_case(case, args, llm_client, run_root, output_dir))
        except Exception as exc:
            if not args.continue_on_error:
                raise
            records.append(case_failure_record(case, exc))

    report = build_live_report(args, cases, records)
    write_matrix_report(output_dir, report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "provider": args.provider,
                "cases": len(records),
                "completed": report["aggregate"]["completed"],
                "failed": report["aggregate"]["failed"],
                "total_tokens": report["aggregate"]["total_tokens"],
                "output_dir": display_path(output_dir),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a multi-case live LLM matrix. This requires a real DeepSeek or "
            "ModelScope key unless --write-skip-report is used."
        )
    )
    parser.add_argument("--provider", choices=("modelscope", "deepseek"), default="modelscope")
    parser.add_argument("--model", default=None)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--output-dir", default=str(DEST_ROOT))
    parser.add_argument("--run-root", default=str(RUN_ROOT))
    parser.add_argument("--case", action="append", help="Run one case id. May be provided multiple times.")
    parser.add_argument("--limit", type=int, default=None, help="Run only the first N selected cases.")
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument(
        "--write-skip-report",
        action="store_true",
        help="When the provider key is absent, write a non-evidence skip report instead of failing.",
    )
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--max-preview-chars", type=int, default=4000)
    return parser.parse_args()


def load_cases(manifest_path: Path) -> list[dict[str, Any]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError(f"Manifest must contain a non-empty cases list: {manifest_path}")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(cases, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"Case #{index} must be an object.")
        missing = sorted(REQUIRED_CASE_FIELDS - raw.keys())
        if missing:
            raise ValueError(f"Case #{index} is missing required fields: {', '.join(missing)}")
        case_id = str(raw["id"]).strip()
        if not case_id or any(char in case_id for char in "\\/:*?\"<>|"):
            raise ValueError(f"Case #{index} has an unsafe id: {case_id!r}")
        if case_id in seen:
            raise ValueError(f"Duplicate case id in manifest: {case_id}")
        seen.add(case_id)
        input_path = resolve_project_path(str(raw["input"]))
        if not input_path.exists():
            raise ValueError(f"Case {case_id} input does not exist: {raw['input']}")
        normalized.append(
            {
                "id": case_id,
                "input": str(input_path),
                "input_display": display_path(input_path),
                "task": str(raw["task"]).strip(),
                "profile": str(raw.get("profile") or "auto"),
                "method": str(raw.get("method") or "auto"),
                "lang": str(raw.get("lang") or "ch"),
                "expected_focus": normalize_string_list(raw.get("expected_focus", [])),
            }
        )
    return normalized


def select_cases(cases: list[dict[str, Any]], selected_ids: list[str] | None, limit: int | None) -> list[dict[str, Any]]:
    if selected_ids:
        by_id = {case["id"]: case for case in cases}
        missing = [case_id for case_id in selected_ids if case_id not in by_id]
        if missing:
            raise ValueError(f"Unknown case id(s): {', '.join(missing)}")
        cases = [by_id[case_id] for case_id in selected_ids]
    if limit is not None:
        if limit <= 0:
            raise ValueError("--limit must be greater than 0")
        cases = cases[:limit]
    return cases


def build_llm_client(args: argparse.Namespace) -> DeepSeekLLMClient | ModelScopeLLMClient:
    kwargs = {
        "model": args.model,
        "base_url": args.base_url,
        "timeout_seconds": args.timeout,
        "max_preview_chars": args.max_preview_chars,
    }
    if args.provider == "deepseek":
        return DeepSeekLLMClient(**kwargs)
    return ModelScopeLLMClient(**kwargs)


def run_live_case(
    case: dict[str, Any],
    args: argparse.Namespace,
    llm_client: DeepSeekLLMClient | ModelScopeLLMClient,
    run_root: Path,
    output_dir: Path,
) -> dict[str, Any]:
    case_dir = output_dir / case["id"]
    if case_dir.exists():
        shutil.rmtree(case_dir)
    agent = MinerUDataAgent(MinerURunner(), llm_client=llm_client)
    result = agent.run(
        case["input"],
        run_root / case["id"],
        task=case["task"],
        profile=case["profile"],
        method=case["method"],
        lang=case["lang"],
    )
    shutil.copytree(Path(result.output_dir), case_dir)
    input_path = Path(case["input"])
    shutil.copy2(input_path, case_dir / f"input{input_path.suffix.lower()}")
    record = summarize_result(case, case_dir, result)
    write_case_readme(case_dir, args, record)
    sanitize_tree(case_dir)
    return record


def summarize_result(case: dict[str, Any], case_dir: Path, result: Any) -> dict[str, Any]:
    llm_analysis = result.llm_analysis if isinstance(result.llm_analysis, dict) else {}
    usage = llm_analysis.get("usage_summary") if isinstance(llm_analysis.get("usage_summary"), dict) else {}
    execution_control = result.execution_control if isinstance(result.execution_control, dict) else {}
    applied = execution_control.get("applied") if isinstance(execution_control.get("applied"), list) else []
    ignored = execution_control.get("ignored") if isinstance(execution_control.get("ignored"), list) else []
    post_parse = llm_analysis.get("post_parse_analysis") if isinstance(llm_analysis.get("post_parse_analysis"), dict) else {}
    recovery_suggestions = (
        post_parse.get("recovery_suggestions") if isinstance(post_parse.get("recovery_suggestions"), list) else []
    )
    risk_findings = post_parse.get("risk_findings") if isinstance(post_parse.get("risk_findings"), list) else []
    return {
        "id": case["id"],
        "status": "completed",
        "case_dir": display_path(case_dir),
        "input": case["input_display"],
        "profile": result.profile,
        "requested_profile": case["profile"],
        "quality_status": result.quality.get("status") if isinstance(result.quality, dict) else None,
        "quality_score": result.quality.get("score") if isinstance(result.quality, dict) else None,
        "llm_status": llm_analysis.get("status"),
        "llm_enabled": bool(llm_analysis.get("enabled")),
        "llm_calls": int(usage.get("tool_call_count") or 0),
        "total_tokens": int(usage.get("total_tokens") or 0),
        "estimated_cost_usd": usage.get("estimated_cost_usd"),
        "applied_controls": len(applied),
        "ignored_controls": len(ignored),
        "risk_findings": len(risk_findings),
        "recovery_suggestions": len(recovery_suggestions),
        "expected_focus": case.get("expected_focus", []),
        "result_path": display_path(case_dir / "result.json"),
        "trace_path": display_path(case_dir / "trace.json"),
    }


def case_failure_record(case: dict[str, Any], exc: Exception) -> dict[str, Any]:
    return {
        "id": case["id"],
        "status": "failed",
        "input": case.get("input_display"),
        "error": scrub_text(repr(exc)),
        "expected_focus": case.get("expected_focus", []),
    }


def build_live_report(args: argparse.Namespace, cases: list[dict[str, Any]], records: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [record for record in records if record.get("status") == "completed"]
    failed = [record for record in records if record.get("status") == "failed"]
    total_tokens = sum(int(record.get("total_tokens") or 0) for record in completed)
    return {
        "schema_version": "2026-05-24",
        "generated_at": utc_now(),
        "status": "completed_with_failures" if failed else "completed",
        "live_provider_evidence": True,
        "provider": args.provider,
        "model": args.model or "provider default",
        "manifest": display_path(Path(args.manifest).resolve()),
        "case_count": len(cases),
        "aggregate": {
            "completed": len(completed),
            "failed": len(failed),
            "llm_enabled_results": sum(1 for record in completed if record.get("llm_enabled")),
            "llm_tool_calls": sum(int(record.get("llm_calls") or 0) for record in completed),
            "total_tokens": total_tokens,
            "cases_with_recovery_suggestions": sum(
                1 for record in completed if int(record.get("recovery_suggestions") or 0) > 0
            ),
            "cases_with_applied_controls": sum(1 for record in completed if int(record.get("applied_controls") or 0) > 0),
        },
        "cases": records,
        "boundary": [
            "This report is live provider evidence only because a real provider key was present at runtime.",
            "Inputs are local HTML fixtures, so the matrix isolates LLM planning and review without requiring MinerU CLI/GPU.",
            "API keys are read from environment variables and are not written to artifacts.",
            "Cost is calculated only when provider token usage exists and token-price environment variables are configured.",
        ],
    }


def build_skip_report(args: argparse.Namespace, cases: list[dict[str, Any]], key_env: str) -> dict[str, Any]:
    return {
        "schema_version": "2026-05-24",
        "generated_at": utc_now(),
        "status": "skipped_missing_provider_key",
        "live_provider_evidence": False,
        "provider": args.provider,
        "model": args.model or "provider default",
        "manifest": display_path(Path(args.manifest).resolve()),
        "required_key_env": key_env,
        "case_count": len(cases),
        "aggregate": {
            "completed": 0,
            "failed": 0,
            "llm_enabled_results": 0,
            "llm_tool_calls": 0,
            "total_tokens": 0,
            "cases_with_recovery_suggestions": 0,
            "cases_with_applied_controls": 0,
        },
        "cases": [
            {
                "id": case["id"],
                "status": "not_run",
                "input": case["input_display"],
                "expected_focus": case.get("expected_focus", []),
            }
            for case in cases
        ],
        "boundary": [
            "This is a skip report, not live LLM evidence.",
            f"Set {key_env} and rerun without --write-skip-report to generate live provider artifacts.",
            "No model request was sent and no token usage was produced.",
        ],
    }


def write_matrix_report(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "llm_live_matrix_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "llm_live_matrix_report.md").write_text(render_markdown(report), encoding="utf-8")


def write_case_readme(case_dir: Path, args: argparse.Namespace, record: dict[str, Any]) -> None:
    lines = [
        f"# Live LLM Matrix Case: {record['id']}",
        "",
        f"- Provider: `{args.provider}`",
        f"- Model: `{args.model or 'provider default'}`",
        f"- Input: `{record['input']}`",
        f"- Profile: `{record['profile']}`",
        f"- Quality: `{record['quality_status']}` ({record['quality_score']}/100)",
        f"- LLM enabled: `{record['llm_enabled']}`",
        f"- LLM status: `{record['llm_status']}`",
        f"- LLM calls: `{record['llm_calls']}`",
        f"- LLM total tokens: `{record['total_tokens']}`",
        f"- LLM estimated cost USD: `{record['estimated_cost_usd']}`",
        "",
        "Boundary: this directory is live provider evidence only when generated by "
        "`scripts/run_live_llm_matrix.py` with a real provider key. API keys are read "
        "from environment variables and are not written to artifacts.",
        "",
    ]
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    aggregate = report["aggregate"]
    lines = [
        "# Live LLM Matrix Report",
        "",
        f"- Status: `{report['status']}`",
        f"- Live provider evidence: `{report['live_provider_evidence']}`",
        f"- Provider: `{report['provider']}`",
        f"- Model: `{report['model']}`",
        f"- Manifest: `{report['manifest']}`",
        "",
        "## Aggregate",
        "",
        f"- Completed cases: {aggregate['completed']}",
        f"- Failed cases: {aggregate['failed']}",
        f"- LLM-enabled results: {aggregate['llm_enabled_results']}",
        f"- LLM tool calls: {aggregate['llm_tool_calls']}",
        f"- Total tokens: {aggregate['total_tokens']}",
        f"- Cases with recovery suggestions: {aggregate['cases_with_recovery_suggestions']}",
        f"- Cases with applied controls: {aggregate['cases_with_applied_controls']}",
        "",
        "## Cases",
        "",
        "| Case | Status | Quality | Calls | Tokens | Recovery suggestions | Applied controls |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for record in report["cases"]:
        quality = "-"
        if record.get("quality_status") is not None:
            quality = f"{record.get('quality_status')} ({record.get('quality_score')})"
        lines.append(
            "| {id} | {status} | {quality} | {calls} | {tokens} | {suggestions} | {applied} |".format(
                id=record.get("id"),
                status=record.get("status"),
                quality=quality,
                calls=record.get("llm_calls", 0),
                tokens=record.get("total_tokens", 0),
                suggestions=record.get("recovery_suggestions", 0),
                applied=record.get("applied_controls", 0),
            )
        )
    lines.extend(["", "## Boundary", ""])
    lines.extend(f"- {item}" for item in report["boundary"])
    lines.append("")
    return "\n".join(lines)


def provider_key_env(provider: str) -> str:
    return PROVIDER_KEY_ENVS[provider]


def normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def resolve_project_path(raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def sanitize_tree(path: Path) -> None:
    for item in path.rglob("*"):
        if not item.is_file() or item.suffix.lower() not in {".json", ".jsonl", ".md", ".txt", ".html"}:
            continue
        text = item.read_text(encoding="utf-8", errors="replace")
        item.write_text(scrub_text(text), encoding="utf-8")


def scrub_text(text: str) -> str:
    clean = text.replace(str(PROJECT_ROOT), "<PROJECT_ROOT>")
    clean = clean.replace(str(PROJECT_ROOT).replace("\\", "\\\\"), "<PROJECT_ROOT>")
    home = Path.home()
    clean = clean.replace(str(home), "<USER_HOME>")
    clean = clean.replace(str(home).replace("\\", "\\\\"), "<USER_HOME>")
    for key_env in PROVIDER_KEY_ENVS.values():
        value = os.getenv(key_env)
        if value:
            clean = clean.replace(value, "***")
    return clean


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    main()
