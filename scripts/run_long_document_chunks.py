from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from time import perf_counter
from typing import Any

from mineru_data_agent.agent import AgentRunError, MinerUDataAgent
from mineru_data_agent.mineru_client import MinerUAgentAPIRunner


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "examples" / "public_real_documents" / "files" / "nist_ai_rmf_1_0.pdf"
RUN_ROOT = PROJECT_ROOT / "runs" / "long_document_chunks"
DEST_ROOT = PROJECT_ROOT / "submission_artifacts" / "long_document_chunks"


class PageRangeAgentAPIRunner:
    def __init__(self, runner: MinerUAgentAPIRunner, page_range: str) -> None:
        self.runner = runner
        self.page_range = page_range

    def parse(self, input_path: Path, output_dir: Path, **kwargs: Any):
        start_page, end_page = _parse_page_range(self.page_range)
        return self.runner.parse(input_path, output_dir, start_page=start_page, end_page=end_page, **kwargs)


def main() -> None:
    args = parse_args()
    input_path = Path(args.input).resolve()
    if not input_path.exists():
        raise SystemExit(f"input does not exist: {input_path}")

    page_count = args.page_count or count_pdf_pages(input_path)
    if page_count <= 0:
        raise SystemExit("could not determine PDF page count; pass --page-count")

    case_dir = Path(args.output_dir).resolve() / args.case_id
    if case_dir.exists():
        shutil.rmtree(case_dir)
    (case_dir / "chunks").mkdir(parents=True, exist_ok=True)
    shutil.copy2(input_path, case_dir / f"input{input_path.suffix.lower()}")

    started = perf_counter()
    chunk_results: list[dict[str, Any]] = []
    for start_page in range(1, page_count + 1, args.chunk_size):
        end_page = min(start_page + args.chunk_size - 1, page_count)
        page_range = f"{start_page}-{end_page}"
        chunk_id = f"p{start_page:03d}_{end_page:03d}"
        run_root = Path(args.run_root).resolve() / args.case_id / chunk_id
        runner = PageRangeAgentAPIRunner(
            MinerUAgentAPIRunner(
                timeout_seconds=args.api_timeout,
                poll_interval_seconds=args.api_poll_interval,
                max_retries=args.api_max_retries,
            ),
            page_range,
        )
        agent = MinerUDataAgent(runner)
        chunk_started = perf_counter()
        try:
            result = agent.run(
                input_path,
                run_root,
                task=f"{args.task} Page range: {page_range}.",
                profile=args.profile,
                method=args.method,
                lang=args.lang,
            )
        except AgentRunError as exc:
            elapsed = round(perf_counter() - chunk_started, 3)
            chunk_record = {
                "chunk_id": chunk_id,
                "page_range": page_range,
                "status": "failed",
                "elapsed_seconds": elapsed,
                "error": str(exc)[-1000:],
                "trace_path": _display_path(Path(exc.trace_path)),
            }
            (case_dir / "chunks" / chunk_id).mkdir(parents=True, exist_ok=True)
            (case_dir / "chunks" / chunk_id / "error.json").write_text(
                json.dumps(_sanitize_paths(chunk_record), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            chunk_results.append(chunk_record)
            if not args.continue_on_error:
                break
            continue

        elapsed = round(perf_counter() - chunk_started, 3)
        chunk_dir = case_dir / "chunks" / chunk_id
        if chunk_dir.exists():
            shutil.rmtree(chunk_dir)
        shutil.copytree(Path(result.output_dir), chunk_dir)
        sanitize_tree(chunk_dir)
        chunk_results.append(
            {
                "chunk_id": chunk_id,
                "page_range": page_range,
                "status": "completed",
                "run_id": result.run_id,
                "elapsed_seconds": elapsed,
                "quality_status": result.quality.get("status"),
                "quality_score": result.quality.get("score"),
                "issue_codes": [
                    item.get("code")
                    for item in result.quality.get("issues", [])
                    if isinstance(item, dict) and item.get("code")
                ],
                "retrieval_chunks": result.retrieval_export.get("stats", {}).get("total_chunks"),
                "provenance_level": result.extracted.get("content_summary", {}).get("provenance_level"),
                "result_path": _display_path(chunk_dir / "result.json"),
                "trace_path": _display_path(chunk_dir / "trace.json"),
                "summary_path": _display_path(chunk_dir / "summary.md"),
            }
        )

    report = build_report(
        args=args,
        input_path=input_path,
        page_count=page_count,
        elapsed_seconds=round(perf_counter() - started, 3),
        chunks=chunk_results,
    )
    (case_dir / "long_document_chunk_report.json").write_text(
        json.dumps(_sanitize_paths(report), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (case_dir / "long_document_chunk_report.md").write_text(render_markdown(report), encoding="utf-8")
    (case_dir / "README.md").write_text(render_readme(report), encoding="utf-8")
    sanitize_tree(case_dir)
    print(json.dumps({"case_dir": _display_path(case_dir), "summary": report["aggregate"]}, ensure_ascii=False, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a long PDF through the MinerU Agent API in page-range chunks.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--case-id", default="public_nist_ai_rmf_full_chunked")
    parser.add_argument("--output-dir", default=str(DEST_ROOT))
    parser.add_argument("--run-root", default=str(RUN_ROOT))
    parser.add_argument("--profile", default="standard_or_contract")
    parser.add_argument("--method", default="auto")
    parser.add_argument("--lang", default="en")
    parser.add_argument("--chunk-size", type=int, default=20)
    parser.add_argument("--page-count", type=int, default=None)
    parser.add_argument("--api-timeout", type=int, default=900)
    parser.add_argument("--api-poll-interval", type=float, default=3.0)
    parser.add_argument("--api-max-retries", type=int, default=2)
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument(
        "--task",
        default=(
            "Parse the full public NIST AI RMF 1.0 PDF with long-document chunk orchestration; "
            "extract publication identity, framework functions, section structure, quality issues, trace, "
            "and retrieval chunks."
        ),
    )
    return parser.parse_args()


def count_pdf_pages(path: Path) -> int:
    data = path.read_bytes()
    return len(re.findall(rb"/Type\s*/Page\b", data))


def _parse_page_range(value: str) -> tuple[int, int]:
    left, right = value.split("-", 1)
    return int(left), int(right)


def build_report(
    *,
    args: argparse.Namespace,
    input_path: Path,
    page_count: int,
    elapsed_seconds: float,
    chunks: list[dict[str, Any]],
) -> dict[str, Any]:
    completed = [item for item in chunks if item.get("status") == "completed"]
    failed = [item for item in chunks if item.get("status") != "completed"]
    return {
        "schema_version": "2026-05-24",
        "document": {
            "input_file": _display_path(input_path),
            "case_id": args.case_id,
            "page_count": page_count,
            "chunk_size": args.chunk_size,
        },
        "aggregate": {
            "total_chunks": len(chunks),
            "completed_chunks": len(completed),
            "failed_chunks": len(failed),
            "success_rate": round(len(completed) / len(chunks), 4) if chunks else 0.0,
            "elapsed_seconds": elapsed_seconds,
            "total_retrieval_chunks": sum(int(item.get("retrieval_chunks") or 0) for item in completed),
            "quality_status_counts": _counts(item.get("quality_status") for item in completed),
            "provenance_level_counts": _counts(item.get("provenance_level") for item in completed),
        },
        "chunks": chunks,
        "boundary": (
            "This is a real online MinerU Agent API long-document chunking smoke. "
            "The API enforces a 20-page maximum per call, so the Data Agent splits page ranges and records each "
            "chunk's artifacts. It is not a local MinerU CLI/GPU benchmark or public internet production load test."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    aggregate = report["aggregate"]
    document = report["document"]
    lines = [
        "# Long Document Chunked API Smoke",
        "",
        "This report shows how the Data Agent handles a public long PDF when the MinerU online Agent API enforces a 20-page per-call limit.",
        "",
        "## Aggregate",
        "",
        f"- Input: `{document['input_file']}`",
        f"- Page count: {document['page_count']}",
        f"- Chunk size: {document['chunk_size']}",
        f"- Chunks completed: {aggregate['completed_chunks']}/{aggregate['total_chunks']}",
        f"- Success rate: {aggregate['success_rate'] * 100:.1f}%",
        f"- Elapsed seconds: {aggregate['elapsed_seconds']}",
        f"- Total retrieval chunks: {aggregate['total_retrieval_chunks']}",
        f"- Quality status counts: `{json.dumps(aggregate['quality_status_counts'], ensure_ascii=False)}`",
        f"- Provenance level counts: `{json.dumps(aggregate['provenance_level_counts'], ensure_ascii=False)}`",
        "",
        "## Chunks",
        "",
        "| Chunk | Pages | Status | Quality | Provenance | Retrieval Chunks | Seconds |",
        "| --- | --- | --- | --- | --- | ---: | ---: |",
    ]
    for item in report["chunks"]:
        lines.append(
            "| {chunk} | {pages} | {status} | {quality} ({score}) | {provenance} | {retrieval} | {seconds} |".format(
                chunk=item.get("chunk_id"),
                pages=item.get("page_range"),
                status=item.get("status"),
                quality=item.get("quality_status", "-"),
                score=item.get("quality_score", "-"),
                provenance=item.get("provenance_level", "-"),
                retrieval=item.get("retrieval_chunks", 0),
                seconds=item.get("elapsed_seconds"),
            )
        )
    lines.extend(["", "## Boundary", "", f"- {report['boundary']}"])
    return "\n".join(lines).strip() + "\n"


def render_readme(report: dict[str, Any]) -> str:
    aggregate = report["aggregate"]
    document = report["document"]
    return "\n".join(
        [
            "# Long Document Chunked Evidence",
            "",
            f"- Case: `{document['case_id']}`",
            f"- Input: `{document['input_file']}`",
            f"- Page count: {document['page_count']}",
            f"- Chunks completed: {aggregate['completed_chunks']}/{aggregate['total_chunks']}",
            f"- Success rate: {aggregate['success_rate'] * 100:.1f}%",
            "",
            "See `long_document_chunk_report.md` for the per-chunk evidence table.",
            "",
            f"Boundary: {report['boundary']}",
            "",
        ]
    )


def sanitize_tree(path: Path) -> None:
    for item in path.rglob("*"):
        if not item.is_file() or item.suffix.lower() not in {".json", ".jsonl", ".md", ".txt"}:
            continue
        text = item.read_text(encoding="utf-8", errors="replace")
        item.write_text(_sanitize_paths(text), encoding="utf-8")


def _sanitize_paths(value: Any) -> Any:
    if isinstance(value, str):
        clean = value.replace(str(PROJECT_ROOT), "<PROJECT_ROOT>")
        clean = clean.replace(str(PROJECT_ROOT).replace("\\", "\\\\"), "<PROJECT_ROOT>")
        return clean
    if isinstance(value, list):
        return [_sanitize_paths(item) for item in value]
    if isinstance(value, dict):
        return {key: _sanitize_paths(item) for key, item in value.items()}
    return value


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _counts(values: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


if __name__ == "__main__":
    main()
