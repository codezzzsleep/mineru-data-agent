from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = PROJECT_ROOT / "submission_artifacts"
SOURCE_REPORT = ARTIFACT_ROOT / "long_document_chunks" / "public_nist_ai_rmf_full_chunked" / "long_document_chunk_report.json"
OUT_DIR = ARTIFACT_ROOT / "long_document_risk"


def main() -> None:
    report = build_report()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "long_document_risk_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (OUT_DIR / "long_document_risk_report.md").write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"out_dir": display_path(OUT_DIR), "risks": len(report["risks"])}, ensure_ascii=False))


def build_report() -> dict[str, Any]:
    source = load_json(SOURCE_REPORT)
    chunks = source.get("chunks", []) if isinstance(source, dict) else []
    issue_counts: Counter[str] = Counter()
    provenance_counts: Counter[str] = Counter()
    quality_counts: Counter[str] = Counter()
    chunk_rows = []
    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue
        issue_counts.update(str(item) for item in chunk.get("issue_codes", []))
        provenance_counts[str(chunk.get("provenance_level") or "unknown")] += 1
        quality_counts[str(chunk.get("quality_status") or "unknown")] += 1
        chunk_rows.append(
            {
                "chunk_id": chunk.get("chunk_id"),
                "page_range": chunk.get("page_range"),
                "status": chunk.get("status"),
                "elapsed_seconds": chunk.get("elapsed_seconds"),
                "quality_status": chunk.get("quality_status"),
                "quality_score": chunk.get("quality_score"),
                "issue_codes": chunk.get("issue_codes", []),
                "retrieval_chunks": chunk.get("retrieval_chunks"),
                "provenance_level": chunk.get("provenance_level"),
                "result_path": chunk.get("result_path"),
            }
        )
    aggregate = source.get("aggregate", {}) if isinstance(source, dict) else {}
    document = source.get("document", {}) if isinstance(source, dict) else {}
    return {
        "schema_version": "2026-05-24",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "scope": "Long-document chunking risk review based on the saved NIST AI RMF online API run.",
        "source_report": display_path(SOURCE_REPORT),
        "document": document,
        "aggregate": {
            "page_count": document.get("page_count"),
            "chunk_size": document.get("chunk_size"),
            "total_chunks": aggregate.get("total_chunks"),
            "completed_chunks": aggregate.get("completed_chunks"),
            "failed_chunks": aggregate.get("failed_chunks"),
            "success_rate": aggregate.get("success_rate"),
            "elapsed_seconds": aggregate.get("elapsed_seconds"),
            "total_retrieval_chunks": aggregate.get("total_retrieval_chunks"),
            "quality_status_counts": dict(sorted(quality_counts.items())),
            "issue_counts": dict(sorted(issue_counts.items())),
            "provenance_level_counts": dict(sorted(provenance_counts.items())),
        },
        "chunks": chunk_rows,
        "risks": [
            {
                "id": "document_level_provenance",
                "current_observation": "All saved chunks completed but reported document-level provenance and `no_page_provenance`.",
                "impact": "Reviewers cannot audit field-level answers to exact pages or bboxes on this online API path.",
                "mitigation": "Use local MinerU CLI for audit-grade PDF runs, or rerun with an API variant that emits page/block provenance.",
            },
            {
                "id": "cross_chunk_context",
                "current_observation": "The online API page limit forces 1-20, 21-40, and 41-48 page ranges.",
                "impact": "References that start in one chunk and resolve in another need a merge/review layer.",
                "mitigation": "Keep chunk manifests, expose page ranges in retrieval metadata, and add cross-chunk entity/table merge tests.",
            },
            {
                "id": "single_long_document_sample",
                "current_observation": "The saved long-document run covers one 48-page public PDF.",
                "impact": "It validates the orchestration path, not long-document accuracy across many formats.",
                "mitigation": "Add 100+ page annual reports and standards with field/table labels in the benchmark set.",
            },
            {
                "id": "no_gpu_cli_long_run",
                "current_observation": "This artifact is an online API chunking run, not local MinerU CLI/GPU throughput.",
                "impact": "GPU pages/second and local artifact cost remain environment-specific.",
                "mitigation": "Run the same script in the HeyWhale MinerU GPU image and record pages/second, GPU hours, and page provenance coverage.",
            },
        ],
        "reviewer_takeaway": [
            "The saved run shows the Agent can split, execute, and aggregate a 48-page public PDF across a 20-page API limit.",
            "It should be read as orchestration evidence, not as a full long-document accuracy benchmark.",
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    aggregate = report["aggregate"]
    lines = [
        "# Long Document Risk Report",
        "",
        report["scope"],
        "",
        "## Saved Run",
        "",
        f"- Source report: `{report['source_report']}`",
        f"- Pages: {aggregate['page_count']}",
        f"- Chunk size: {aggregate['chunk_size']}",
        f"- Chunks: {aggregate['completed_chunks']}/{aggregate['total_chunks']} completed",
        f"- Failed chunks: {aggregate['failed_chunks']}",
        f"- Elapsed seconds: {aggregate['elapsed_seconds']}",
        f"- Retrieval chunks: {aggregate['total_retrieval_chunks']}",
        f"- Quality status counts: `{json.dumps(aggregate['quality_status_counts'], ensure_ascii=False)}`",
        f"- Issue counts: `{json.dumps(aggregate['issue_counts'], ensure_ascii=False)}`",
        f"- Provenance levels: `{json.dumps(aggregate['provenance_level_counts'], ensure_ascii=False)}`",
        "",
        "## Chunks",
        "",
        "| Chunk | Pages | Status | Seconds | Quality | Issues | Retrieval Chunks | Provenance |",
        "| --- | --- | --- | ---: | --- | --- | ---: | --- |",
    ]
    for chunk in report["chunks"]:
        lines.append(
            "| {chunk_id} | {page_range} | {status} | {seconds} | {quality} ({score}) | {issues} | {retrieval} | {provenance} |".format(
                chunk_id=chunk["chunk_id"],
                page_range=chunk["page_range"],
                status=chunk["status"],
                seconds=chunk["elapsed_seconds"],
                quality=chunk["quality_status"],
                score=chunk["quality_score"],
                issues=", ".join(chunk["issue_codes"]) or "-",
                retrieval=chunk["retrieval_chunks"],
                provenance=chunk["provenance_level"],
            )
        )
    lines.extend(["", "## Risks And Mitigations", ""])
    for item in report["risks"]:
        lines.append(f"- `{item['id']}`: {item['current_observation']} Impact: {item['impact']} Mitigation: {item['mitigation']}")
    lines.extend(["", "## Reviewer Takeaway", ""])
    lines.extend(f"- {item}" for item in report["reviewer_takeaway"])
    lines.append("")
    return "\n".join(lines)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


if __name__ == "__main__":
    main()
