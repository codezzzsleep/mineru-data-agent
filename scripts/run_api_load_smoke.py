from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from mineru_data_agent.api import app


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "submission_artifacts" / "api_load_smoke"
DEFAULT_INPUT = PROJECT_ROOT / "examples" / "cases" / "case_1_financial_report.html"


def main() -> None:
    args = parse_args()
    out_dir = Path(args.output_dir).resolve()
    runs_dir = out_dir / "request_artifacts"
    if runs_dir.exists():
        shutil.rmtree(runs_dir)
    runs_dir.mkdir(parents=True, exist_ok=True)
    input_path = Path(args.input).resolve()
    payload = input_path.read_bytes()
    os.environ["MINERU_DATA_AGENT_ALLOWED_OUTPUT_BASE"] = str(out_dir)

    started = time.perf_counter()
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [
            executor.submit(run_one, index=index, payload=payload, filename=input_path.name, runs_dir=runs_dir)
            for index in range(args.requests)
        ]
        for future in as_completed(futures):
            results.append(future.result())
    elapsed = time.perf_counter() - started
    results.sort(key=lambda item: item["index"])
    report = build_report(args=args, input_path=input_path, results=results, elapsed=elapsed, out_dir=out_dir)
    threshold_failures = evaluate_thresholds(report, args=args)
    (out_dir / "api_load_smoke_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "api_load_smoke_report.md").write_text(render_markdown(report), encoding="utf-8")
    sanitize_text_tree(out_dir)
    if not args.keep_runs:
        shutil.rmtree(runs_dir, ignore_errors=True)
    print(
        json.dumps(
            {
                "out_dir": display_path(out_dir),
                "success": report["aggregate"]["success"],
                "failed": report["aggregate"]["failed"],
                "threshold_failures": threshold_failures,
            }
        )
    )
    if threshold_failures:
        raise SystemExit("API load smoke threshold failure: " + "; ".join(threshold_failures))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a local in-process API concurrency smoke test.")
    parser.add_argument("--requests", type=int, default=8)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output-dir", default=str(OUT_DIR))
    parser.add_argument("--keep-runs", action="store_true", help="Keep per-request run artifacts under the report dir.")
    parser.add_argument("--min-success-rate", type=float, default=None)
    parser.add_argument("--max-p95-seconds", type=float, default=None)
    parser.add_argument("--min-artifact-complete-rate", type=float, default=None)
    args = parser.parse_args()
    if args.requests < 1:
        raise SystemExit("--requests must be >= 1")
    if args.concurrency < 1:
        raise SystemExit("--concurrency must be >= 1")
    for field in ["min_success_rate", "min_artifact_complete_rate"]:
        value = getattr(args, field)
        if value is not None and not 0 <= value <= 1:
            raise SystemExit(f"--{field.replace('_', '-')} must be between 0 and 1")
    if args.max_p95_seconds is not None and args.max_p95_seconds <= 0:
        raise SystemExit("--max-p95-seconds must be > 0")
    return args


def run_one(*, index: int, payload: bytes, filename: str, runs_dir: Path) -> dict[str, Any]:
    client = TestClient(app)
    output_root = runs_dir / f"request_{index:03d}"
    start = time.perf_counter()
    response = client.post(
        "/v1/parse",
        data={
            "task": "并发 smoke：抽取财报日期、公司名称和合计数字",
            "profile": "financial_report",
            "runner": "cli",
            "output_root": str(output_root),
        },
        files={"file": (filename, payload, "text/html")},
    )
    elapsed = time.perf_counter() - start
    record: dict[str, Any] = {
        "index": index,
        "status_code": response.status_code,
        "elapsed_seconds": round(elapsed, 6),
        "output_root": display_path(output_root),
    }
    try:
        data = response.json()
    except Exception as exc:  # pragma: no cover - defensive reporting only.
        record["error"] = {"error": "invalid_json_response", "message": str(exc)}
        return record
    if response.status_code != 200:
        record["error"] = data.get("detail", data)
        return record
    result_path = Path(data["output_dir"]) / "result.json"
    trace_path = Path(data["trace_path"])
    summary_path = Path(data["summary_path"])
    record.update(
        {
            "run_id": data["run_id"],
            "quality_status": data.get("quality", {}).get("status"),
            "quality_score": data.get("quality", {}).get("score"),
            "field_evidence_count": len(data.get("extracted", {}).get("field_evidence", [])),
            "trace_path": display_path(trace_path),
            "result_path": display_path(result_path),
            "summary_path": display_path(summary_path),
            "trace_exists": trace_path.exists(),
            "result_exists": result_path.exists(),
            "summary_exists": summary_path.exists(),
        }
    )
    return record


def build_report(
    *, args: argparse.Namespace, input_path: Path, results: list[dict[str, Any]], elapsed: float, out_dir: Path
) -> dict[str, Any]:
    latencies = [float(item["elapsed_seconds"]) for item in results]
    successes = [item for item in results if item.get("status_code") == 200]
    failures = [item for item in results if item.get("status_code") != 200]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "scope": "Local in-process FastAPI concurrency smoke test; not an external production load test.",
        "input": display_path(input_path),
        "output_dir": display_path(out_dir),
        "parameters": {"requests": args.requests, "concurrency": args.concurrency},
        "thresholds": {
            "min_success_rate": args.min_success_rate,
            "max_p95_seconds": args.max_p95_seconds,
            "min_artifact_complete_rate": args.min_artifact_complete_rate,
        },
        "aggregate": {
            "requests": len(results),
            "success": len(successes),
            "failed": len(failures),
            "success_rate": len(successes) / len(results) if results else 0.0,
            "total_elapsed_seconds": round(elapsed, 6),
            "throughput_requests_per_second": round(len(results) / elapsed, 6) if elapsed else 0.0,
            "latency_seconds": {
                "min": round(min(latencies), 6) if latencies else 0.0,
                "p50": round(statistics.median(latencies), 6) if latencies else 0.0,
                "p95": round(percentile(latencies, 95), 6) if latencies else 0.0,
                "max": round(max(latencies), 6) if latencies else 0.0,
            },
            "artifact_complete": sum(
                1
                for item in successes
                if item.get("trace_exists") and item.get("result_exists") and item.get("summary_exists")
            ),
            "quality_status_counts": count_by(successes, "quality_status"),
            "field_evidence_min": min((int(item.get("field_evidence_count") or 0) for item in successes), default=0),
        },
        "results": results,
        "boundary": [
            "This uses FastAPI TestClient in-process to verify concurrent request handling and artifact persistence.",
            "It does not replace an external network load test, GPU stress test, or long-document soak test.",
        ],
    }


def evaluate_thresholds(report: dict[str, Any], *, args: argparse.Namespace) -> list[str]:
    aggregate = report["aggregate"]
    failures: list[str] = []
    success_rate = float(aggregate.get("success_rate") or 0.0)
    p95 = float((aggregate.get("latency_seconds") or {}).get("p95") or 0.0)
    success_count = int(aggregate.get("success") or 0)
    artifact_complete = int(aggregate.get("artifact_complete") or 0)
    artifact_complete_rate = artifact_complete / success_count if success_count else 0.0
    if args.min_success_rate is not None and success_rate < args.min_success_rate:
        failures.append(f"success_rate {success_rate:.4f} < {args.min_success_rate:.4f}")
    if args.max_p95_seconds is not None and p95 > args.max_p95_seconds:
        failures.append(f"p95_seconds {p95:.4f} > {args.max_p95_seconds:.4f}")
    if args.min_artifact_complete_rate is not None and artifact_complete_rate < args.min_artifact_complete_rate:
        failures.append(
            f"artifact_complete_rate {artifact_complete_rate:.4f} < {args.min_artifact_complete_rate:.4f}"
        )
    report["threshold_result"] = {
        "passed": not failures,
        "failures": failures,
        "artifact_complete_rate": round(artifact_complete_rate, 6),
    }
    return failures


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * (pct / 100)
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    if lower == upper:
        return ordered[lower]
    fraction = index - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def count_by(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item.get(key, "unknown"))
        counts[value] = counts.get(value, 0) + 1
    return counts


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def sanitize_text_tree(path: Path) -> None:
    replacements = {
        str(PROJECT_ROOT): "<PROJECT_ROOT>",
        str(PROJECT_ROOT).replace("\\", "\\\\"): "<PROJECT_ROOT>",
    }
    text_suffixes = {".json", ".jsonl", ".md", ".txt", ".html"}
    for item in path.rglob("*"):
        if not item.is_file() or item.suffix.lower() not in text_suffixes:
            continue
        text = item.read_text(encoding="utf-8", errors="replace")
        clean = text
        for source, replacement in replacements.items():
            clean = clean.replace(source, replacement)
        if clean != text:
            item.write_text(clean, encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    aggregate = report["aggregate"]
    rows = [
        "# API Load Smoke Report",
        "",
        report["scope"],
        "",
        "## Aggregate",
        "",
        f"- Requests: {aggregate['requests']}",
        f"- Success: {aggregate['success']}",
        f"- Failed: {aggregate['failed']}",
        f"- Success rate: {aggregate['success_rate']:.1%}",
        f"- Total elapsed seconds: {aggregate['total_elapsed_seconds']}",
        f"- Throughput requests/second: {aggregate['throughput_requests_per_second']}",
        f"- Latency seconds: `{json.dumps(aggregate['latency_seconds'], ensure_ascii=False)}`",
        f"- Complete artifact sets: {aggregate['artifact_complete']}/{aggregate['success']}",
        f"- Quality status counts: `{json.dumps(aggregate['quality_status_counts'], ensure_ascii=False)}`",
        f"- Minimum field evidence count: {aggregate['field_evidence_min']}",
        f"- Threshold result: `{json.dumps(report.get('threshold_result', {}), ensure_ascii=False)}`",
        "",
        "## Requests",
        "",
        "| # | Status | Seconds | Quality | Field Evidence | Trace |",
        "| ---: | ---: | ---: | --- | ---: | --- |",
    ]
    for item in report["results"]:
        rows.append(
            "| {index} | {status_code} | {elapsed} | {quality} | {field_evidence} | {trace} |".format(
                index=item["index"],
                status_code=item["status_code"],
                elapsed=item["elapsed_seconds"],
                quality=item.get("quality_status", "-"),
                field_evidence=item.get("field_evidence_count", 0),
                trace="yes" if item.get("trace_exists") else "no",
            )
        )
    rows.extend(["", "## Boundary", ""])
    rows.extend(f"- {item}" for item in report["boundary"])
    rows.append("")
    return "\n".join(rows)


if __name__ == "__main__":
    main()
