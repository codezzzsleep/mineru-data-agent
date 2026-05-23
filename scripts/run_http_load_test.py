from __future__ import annotations

import argparse
import json
import mimetypes
import shutil
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "submission_artifacts" / "http_load_test"
DEFAULT_INPUT = PROJECT_ROOT / "examples" / "cases" / "case_1_financial_report.html"


def main() -> None:
    args = parse_args()
    out_dir = Path(args.output_dir).resolve()
    request_artifacts = out_dir / "request_artifacts"
    if request_artifacts.exists():
        shutil.rmtree(request_artifacts)
    request_artifacts.mkdir(parents=True, exist_ok=True)
    input_path = Path(args.input).resolve()
    payload = input_path.read_bytes()
    health = check_health(args.base_url, args.timeout)

    started = time.perf_counter()
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [
            executor.submit(
                run_one,
                args=args,
                index=index,
                input_path=input_path,
                payload=payload,
                request_artifacts=request_artifacts,
            )
            for index in range(args.requests)
        ]
        for future in as_completed(futures):
            results.append(future.result())
    elapsed = time.perf_counter() - started
    results.sort(key=lambda item: item["index"])

    report = build_report(
        args=args,
        health=health,
        input_path=input_path,
        results=results,
        elapsed=elapsed,
        out_dir=out_dir,
    )
    (out_dir / "http_load_test_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "http_load_test_report.md").write_text(render_markdown(report), encoding="utf-8")
    sanitize_text_tree(out_dir)
    if not args.keep_artifacts:
        shutil.rmtree(request_artifacts, ignore_errors=True)
    print(
        json.dumps(
            {
                "out_dir": display_path(out_dir),
                "success": report["aggregate"]["success"],
                "failed": report["aggregate"]["failed"],
                "success_rate": report["aggregate"]["success_rate"],
            },
            ensure_ascii=False,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a live HTTP API load smoke against a running MinerU Data Agent API.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--requests", type=int, default=12)
    parser.add_argument("--concurrency", type=int, default=6)
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output-dir", default=str(OUT_DIR))
    parser.add_argument("--endpoint", choices=("parse", "jobs", "mixed"), default="mixed")
    parser.add_argument("--runner", default="cli")
    parser.add_argument("--profile", default="financial_report")
    parser.add_argument("--task", default="HTTP 压测：抽取财报日期、公司名称、合计数字和可验证证据")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--poll-interval", type=float, default=0.25)
    parser.add_argument("--job-timeout", type=float, default=120.0)
    parser.add_argument("--keep-artifacts", action="store_true")
    parser.add_argument(
        "--no-output-root",
        action="store_true",
        help="Do not send output_root. Use this when the API runs in a container with a different filesystem.",
    )
    args = parser.parse_args()
    if args.requests < 1:
        raise SystemExit("--requests must be >= 1")
    if args.concurrency < 1:
        raise SystemExit("--concurrency must be >= 1")
    if args.timeout <= 0:
        raise SystemExit("--timeout must be > 0")
    if args.job_timeout <= 0:
        raise SystemExit("--job-timeout must be > 0")
    return args


def check_health(base_url: str, timeout: float) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        response = httpx.get(f"{base_url.rstrip('/')}/health", timeout=timeout)
        elapsed = time.perf_counter() - started
        return {
            "status_code": response.status_code,
            "elapsed_seconds": round(elapsed, 6),
            "json": response.json() if response.headers.get("content-type", "").startswith("application/json") else None,
        }
    except Exception as exc:
        return {"status_code": None, "elapsed_seconds": round(time.perf_counter() - started, 6), "error": str(exc)}


def run_one(
    *,
    args: argparse.Namespace,
    index: int,
    input_path: Path,
    payload: bytes,
    request_artifacts: Path,
) -> dict[str, Any]:
    endpoint = choose_endpoint(args.endpoint, index)
    output_root = request_artifacts / f"request_{index:03d}"
    output_root.mkdir(parents=True, exist_ok=True)
    data = {
        "task": args.task,
        "profile": args.profile,
        "runner": args.runner,
    }
    if not args.no_output_root:
        data["output_root"] = str(output_root)
    mime_type = mimetypes.guess_type(input_path.name)[0] or "application/octet-stream"
    started = time.perf_counter()
    record: dict[str, Any] = {
        "index": index,
        "endpoint": endpoint,
        "output_root": display_path(output_root),
    }
    try:
        with httpx.Client(base_url=args.base_url, timeout=args.timeout) as client:
            if endpoint == "parse":
                response = client.post(
                    "/v1/parse",
                    data=data,
                    files={"file": (input_path.name, payload, mime_type)},
                )
                record.update(handle_parse_response(response))
            else:
                response = client.post(
                    "/v1/jobs",
                    data=data,
                    files={"file": (input_path.name, payload, mime_type)},
                )
                record.update(handle_job_response(client, response, args=args))
    except Exception as exc:
        record["status_code"] = None
        record["error"] = {"error": "request_exception", "message": str(exc)}
    record["elapsed_seconds"] = round(time.perf_counter() - started, 6)
    enrich_record_with_artifact_checks(record)
    return record


def choose_endpoint(mode: str, index: int) -> str:
    if mode == "mixed":
        return "parse" if index % 2 == 0 else "jobs"
    return mode


def handle_parse_response(response: httpx.Response) -> dict[str, Any]:
    record: dict[str, Any] = {"status_code": response.status_code}
    payload = parse_json_response(response)
    if response.status_code != 200:
        record["error"] = payload
        return record
    record.update(summarize_result(payload))
    return record


def handle_job_response(client: httpx.Client, response: httpx.Response, *, args: argparse.Namespace) -> dict[str, Any]:
    record: dict[str, Any] = {"status_code": response.status_code}
    payload = parse_json_response(response)
    if response.status_code != 202:
        record["error"] = payload
        return record
    job_id = payload.get("job_id")
    record["job_id"] = job_id
    record["initial_job_status"] = payload.get("status")
    deadline = time.perf_counter() + args.job_timeout
    polls = 0
    last_payload: dict[str, Any] = {}
    while time.perf_counter() < deadline:
        polls += 1
        poll_response = client.get(f"/v1/jobs/{job_id}")
        last_payload = parse_json_response(poll_response)
        status = last_payload.get("status")
        if status in {"completed", "failed"}:
            record["final_job_status"] = status
            record["polls"] = polls
            record["job_status_code"] = poll_response.status_code
            if status == "completed":
                record.update(summarize_result(last_payload.get("result", {})))
            else:
                record["error"] = last_payload.get("error", last_payload)
            return record
        time.sleep(args.poll_interval)
    record["final_job_status"] = "timeout"
    record["polls"] = polls
    record["error"] = {"error": "job_timeout", "last_status": last_payload.get("status")}
    return record


def parse_json_response(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except Exception as exc:
        return {"error": "invalid_json_response", "message": str(exc), "text_tail": response.text[-500:]}
    return payload if isinstance(payload, dict) else {"payload": payload}


def summarize_result(result: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {"error": {"error": "missing_result_payload"}}
    output_dir = result.get("output_dir")
    result_path = str(Path(output_dir) / "result.json") if output_dir else None
    return {
        "run_id": result.get("run_id"),
        "quality_status": result.get("quality", {}).get("status") if isinstance(result.get("quality"), dict) else None,
        "quality_score": result.get("quality", {}).get("score") if isinstance(result.get("quality"), dict) else None,
        "field_evidence_count": len(result.get("extracted", {}).get("field_evidence", []))
        if isinstance(result.get("extracted"), dict)
        else 0,
        "recovery_executed": bool(result.get("recovery_decision", {}).get("executed"))
        if isinstance(result.get("recovery_decision"), dict)
        else False,
        "trace_path": result.get("trace_path"),
        "result_path": result_path,
        "summary_path": result.get("summary_path"),
    }


def enrich_record_with_artifact_checks(record: dict[str, Any]) -> None:
    for key in ("trace_path", "result_path", "summary_path"):
        value = record.get(key)
        if not value:
            record[f"{key}_exists"] = False
            continue
        path = Path(str(value).replace("<PROJECT_ROOT>", str(PROJECT_ROOT)))
        record[f"{key}_exists"] = path.exists()


def build_report(
    *,
    args: argparse.Namespace,
    health: dict[str, Any],
    input_path: Path,
    results: list[dict[str, Any]],
    elapsed: float,
    out_dir: Path,
) -> dict[str, Any]:
    latencies = [float(item["elapsed_seconds"]) for item in results]
    successes = [item for item in results if request_succeeded(item)]
    failures = [item for item in results if not request_succeeded(item)]
    return {
        "schema_version": "2026-05-24",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "scope": "Live HTTP load smoke against a running FastAPI server over TCP loopback.",
        "base_url": args.base_url,
        "health": health,
        "input": display_path(input_path),
        "output_dir": display_path(out_dir),
        "parameters": {
            "requests": args.requests,
            "concurrency": args.concurrency,
            "endpoint": args.endpoint,
            "runner": args.runner,
            "profile": args.profile,
            "send_output_root": not args.no_output_root,
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
            "complete_artifact_sets": sum(
                1
                for item in successes
                if item.get("trace_path_exists") and item.get("result_path_exists") and item.get("summary_path_exists")
            ),
            "endpoint_counts": count_by(results, "endpoint"),
            "quality_status_counts": count_by(successes, "quality_status"),
            "minimum_field_evidence_count": min(
                (int(item.get("field_evidence_count") or 0) for item in successes),
                default=0,
            ),
        },
        "results": results,
        "boundary": [
            "This is a real HTTP loopback smoke test, stronger than in-process TestClient evidence.",
            "It is still not a public internet deployment, GPU saturation test, or long-running production soak test.",
            "The committed run uses small HTML input to keep CI and reviewer reproduction inexpensive.",
        ],
    }


def request_succeeded(item: dict[str, Any]) -> bool:
    if item.get("endpoint") == "jobs":
        return item.get("status_code") == 202 and item.get("final_job_status") == "completed"
    return item.get("status_code") == 200


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
    return dict(sorted(counts.items()))


def render_markdown(report: dict[str, Any]) -> str:
    aggregate = report["aggregate"]
    lines = [
        "# HTTP Load Smoke Report",
        "",
        report["scope"],
        "",
        "## Aggregate",
        "",
        f"- Base URL: `{report['base_url']}`",
        f"- Health: `{json.dumps(report['health'], ensure_ascii=False)}`",
        f"- Requests: {aggregate['requests']}",
        f"- Success: {aggregate['success']}",
        f"- Failed: {aggregate['failed']}",
        f"- Success rate: {aggregate['success_rate']:.1%}",
        f"- Total elapsed seconds: {aggregate['total_elapsed_seconds']}",
        f"- Throughput requests/second: {aggregate['throughput_requests_per_second']}",
        f"- Latency seconds: `{json.dumps(aggregate['latency_seconds'], ensure_ascii=False)}`",
        f"- Complete artifact sets: {aggregate['complete_artifact_sets']}/{aggregate['success']}",
        f"- Endpoint counts: `{json.dumps(aggregate['endpoint_counts'], ensure_ascii=False)}`",
        f"- Quality status counts: `{json.dumps(aggregate['quality_status_counts'], ensure_ascii=False)}`",
        f"- Minimum field evidence count: {aggregate['minimum_field_evidence_count']}",
        "",
        "## Requests",
        "",
        "| # | Endpoint | Status | Job | Seconds | Quality | Evidence | Artifacts |",
        "| ---: | --- | ---: | --- | ---: | --- | ---: | --- |",
    ]
    for item in report["results"]:
        artifact_status = "{}/{}/{}".format(
            "trace" if item.get("trace_path_exists") else "-",
            "result" if item.get("result_path_exists") else "-",
            "summary" if item.get("summary_path_exists") else "-",
        )
        lines.append(
            "| {index} | {endpoint} | {status} | {job} | {seconds} | {quality} | {evidence} | {artifacts} |".format(
                index=item["index"],
                endpoint=item.get("endpoint"),
                status=item.get("status_code", "-"),
                job=item.get("final_job_status", "-"),
                seconds=item.get("elapsed_seconds"),
                quality=item.get("quality_status", "-"),
                evidence=item.get("field_evidence_count", 0),
                artifacts=artifact_status,
            )
        )
    lines.extend(["", "## Boundary", ""])
    lines.extend(f"- {item}" for item in report["boundary"])
    lines.append("")
    return "\n".join(lines)


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


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


if __name__ == "__main__":
    main()
