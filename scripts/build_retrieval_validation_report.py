from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = PROJECT_ROOT / "submission_artifacts"
OUT_DIR = ARTIFACT_ROOT / "retrieval_validation"
LABELS_PATH = PROJECT_ROOT / "examples" / "evaluation" / "labels.json"


def main() -> None:
    report = build_report()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "retrieval_validation_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (OUT_DIR / "retrieval_validation_report.md").write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"out_dir": display_path(OUT_DIR), "chunk_files": report["aggregate"]["chunk_files"]}, ensure_ascii=False))


def build_report() -> dict[str, Any]:
    chunk_paths = [path for path in sorted(ARTIFACT_ROOT.rglob("retrieval_chunks.jsonl")) if "request_artifacts" not in path.parts]
    rows = [summarize_chunk_file(path) for path in chunk_paths]
    label_checks = run_label_query_checks()
    total_chunks = sum(row["chunks"] for row in rows)
    schema_errors = sum(row["schema_error_count"] for row in rows)
    duplicate_chunks = sum(row["duplicate_text_count"] for row in rows)
    return {
        "schema_version": "2026-05-24",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "scope": "Retrieval chunk format and lightweight lexical query validation over saved artifacts.",
        "aggregate": {
            "chunk_files": len(rows),
            "total_chunks": total_chunks,
            "schema_error_count": schema_errors,
            "duplicate_text_count": duplicate_chunks,
            "duplicate_text_rate": duplicate_chunks / total_chunks if total_chunks else 0.0,
            "empty_text_chunks": sum(row["empty_text_chunks"] for row in rows),
            "label_query_checks": label_checks["aggregate"],
        },
        "chunk_files": rows,
        "label_query_checks": label_checks["cases"],
        "notes": [
            "This is a schema, de-duplication, density, and lexical top-k smoke test.",
            "It does not run an embedding model and should not be presented as a vector database benchmark.",
            "A production retrieval benchmark should add a fixed embedding model, query set, and human relevance labels.",
        ],
    }


def summarize_chunk_file(path: Path) -> dict[str, Any]:
    chunks = []
    schema_errors = []
    text_hash_counts: Counter[str] = Counter()
    type_counts: Counter[str] = Counter()
    empty_text_chunks = 0
    char_counts = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            schema_errors.append({"line": line_no, "error": f"json_decode: {exc.msg}"})
            continue
        errors = validate_chunk(item, line_no)
        schema_errors.extend(errors)
        text = str(item.get("chunk_text") or "")
        if not text.strip():
            empty_text_chunks += 1
        normalized = normalize(text)
        if normalized:
            text_hash_counts[normalized] += 1
        content_type = str(item.get("content_type") or "missing")
        type_counts[content_type] += 1
        char_counts.append(len(text))
        chunks.append(item)
    duplicate_text_count = sum(count - 1 for count in text_hash_counts.values() if count > 1)
    return {
        "path": display_path(path),
        "chunks": len(chunks),
        "schema_error_count": len(schema_errors),
        "schema_errors": schema_errors[:20],
        "duplicate_text_count": duplicate_text_count,
        "empty_text_chunks": empty_text_chunks,
        "content_type_counts": dict(sorted(type_counts.items())),
        "avg_chunk_chars": round(sum(char_counts) / len(char_counts), 1) if char_counts else 0.0,
        "min_chunk_chars": min(char_counts) if char_counts else 0,
        "max_chunk_chars": max(char_counts) if char_counts else 0,
    }


def validate_chunk(item: Any, line_no: int) -> list[dict[str, Any]]:
    errors = []
    if not isinstance(item, dict):
        return [{"line": line_no, "error": "chunk is not an object"}]
    required = ["chunk_id", "page_no", "pages", "content_type", "section_title", "chunk_text", "image_path"]
    for key in required:
        if key not in item:
            errors.append({"line": line_no, "error": f"missing:{key}"})
    if "pages" in item and not isinstance(item["pages"], list):
        errors.append({"line": line_no, "error": "pages_not_list"})
    if "page_no" in item and not isinstance(item["page_no"], int):
        errors.append({"line": line_no, "error": "page_no_not_int"})
    if "chunk_text" in item and not isinstance(item["chunk_text"], str):
        errors.append({"line": line_no, "error": "chunk_text_not_string"})
    return errors


def run_label_query_checks() -> dict[str, Any]:
    labels = load_json(LABELS_PATH)
    raw_cases = labels.get("cases", []) if isinstance(labels, dict) else []
    cases = []
    total = 0
    hits = 0
    for raw_case in raw_cases:
        if not isinstance(raw_case, dict):
            continue
        result_path = resolve_path(raw_case.get("result_path"))
        result = load_json(result_path)
        retrieval = result.get("retrieval_export", {}) if isinstance(result, dict) else {}
        chunks_path = resolve_path(retrieval.get("chunks_path")) if isinstance(retrieval, dict) else None
        chunks = load_chunks(chunks_path) if chunks_path else []
        queries = label_queries(raw_case)
        checks = []
        for query in queries:
            total += 1
            top = lexical_top_k(query, chunks, k=3)
            hit = any(normalize(query) in normalize(item.get("chunk_text", "")) for item in top)
            hits += int(hit)
            checks.append(
                {
                    "query": query,
                    "hit_top3": hit,
                    "top_chunk_ids": [item.get("chunk_id") for item in top],
                    "top_scores": [item.get("_score") for item in top],
                }
            )
        cases.append(
            {
                "id": raw_case.get("id"),
                "queries": len(queries),
                "hits_top3": sum(1 for item in checks if item["hit_top3"]),
                "checks": checks[:12],
            }
        )
    return {
        "aggregate": {
            "queries": total,
            "hits_top3": hits,
            "hit_rate_top3": hits / total if total else 1.0,
        },
        "cases": cases,
    }


def label_queries(raw_case: dict[str, Any]) -> list[str]:
    queries = []
    for item in raw_case.get("expected_text_contains", []) if isinstance(raw_case.get("expected_text_contains"), list) else []:
        text = str(item).strip()
        if text:
            queries.append(text)
    for item in raw_case.get("expected_numeric_evidence", []) if isinstance(raw_case.get("expected_numeric_evidence"), list) else []:
        if isinstance(item, dict) and item.get("text_contains"):
            queries.append(str(item["text_contains"]))
    for value in raw_case.get("expected_fields", {}).values() if isinstance(raw_case.get("expected_fields"), dict) else []:
        if isinstance(value, dict):
            value = value.get("contains") or value.get("equals")
        text = str(value).strip()
        if text and len(text) >= 3:
            queries.append(text)
    seen = set()
    unique = []
    for query in queries:
        key = normalize(query)
        if key and key not in seen:
            seen.add(key)
            unique.append(query)
    return unique[:20]


def lexical_top_k(query: str, chunks: list[dict[str, Any]], *, k: int) -> list[dict[str, Any]]:
    q_tokens = set(tokenize(query))
    ranked = []
    for chunk in chunks:
        text = str(chunk.get("chunk_text") or "")
        tokens = set(tokenize(text))
        score = len(q_tokens & tokens)
        if normalize(query) in normalize(text):
            score += 100
        copy = dict(chunk)
        copy["_score"] = score
        ranked.append(copy)
    return sorted(ranked, key=lambda item: item["_score"], reverse=True)[:k]


def tokenize(text: str) -> list[str]:
    normalized = normalize(text)
    return [token for token in normalized.replace("|", " ").split() if token]


def load_chunks(path: Path) -> list[dict[str, Any]]:
    chunks = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                item = json.loads(line)
                if isinstance(item, dict):
                    chunks.append(item)
    except Exception:
        return []
    return chunks


def render_markdown(report: dict[str, Any]) -> str:
    aggregate = report["aggregate"]
    query_aggregate = aggregate["label_query_checks"]
    lines = [
        "# Retrieval Validation Report",
        "",
        report["scope"],
        "",
        "## Aggregate",
        "",
        f"- Chunk files: {aggregate['chunk_files']}",
        f"- Total chunks: {aggregate['total_chunks']}",
        f"- Schema errors: {aggregate['schema_error_count']}",
        f"- Empty text chunks: {aggregate['empty_text_chunks']}",
        f"- Duplicate text chunks: {aggregate['duplicate_text_count']} ({aggregate['duplicate_text_rate']:.2%})",
        f"- Label lexical top-3 hit rate: {query_aggregate['hit_rate_top3']:.2%} ({query_aggregate['hits_top3']}/{query_aggregate['queries']})",
        "",
        "## Chunk Files",
        "",
        "| Chunks | Errors | Duplicates | Empty | Avg Chars | Types | Path |",
        "| ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for row in report["chunk_files"]:
        lines.append(
            "| {chunks} | {errors} | {dupes} | {empty} | {avg} | `{types}` | `{path}` |".format(
                chunks=row["chunks"],
                errors=row["schema_error_count"],
                dupes=row["duplicate_text_count"],
                empty=row["empty_text_chunks"],
                avg=row["avg_chunk_chars"],
                types=json.dumps(row["content_type_counts"], ensure_ascii=False),
                path=row["path"],
            )
        )
    lines.extend(["", "## Label Query Smoke", "", "| Case | Queries | Top-3 Hits |", "| --- | ---: | ---: |"])
    for row in report["label_query_checks"]:
        lines.append(f"| {row['id']} | {row['queries']} | {row['hits_top3']} |")
    lines.extend(["", "## Notes", ""])
    lines.extend(f"- {item}" for item in report["notes"])
    lines.append("")
    return "\n".join(lines)


def resolve_path(value: Any) -> Path | None:
    if not value:
        return None
    raw = str(value).replace("<PROJECT_ROOT>", str(PROJECT_ROOT))
    path = Path(raw)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def load_json(path: Path | None) -> Any:
    if path is None:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def normalize(text: Any) -> str:
    return " ".join(str(text).lower().strip().split())


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


if __name__ == "__main__":
    main()
