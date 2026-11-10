from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .corpus import build_corpus_catalog


STANDARD_PACKAGE_FILES = [
    "result.json",
    "summary.md",
    "trace.json",
    "retrieval/retrieval_chunks.jsonl",
    "document_skill/SKILL.md",
    "document_skill/references/compressed.md",
    "document_skill/references/content.md",
    "document_skill/references/overview.md",
    "document_skill/references/structured.md",
    "document_skill/references/evidence.md",
    "document_skill/references/segments.md",
]


@dataclass(frozen=True)
class SourceRun:
    id: str
    source_file: str
    output_dir: Path
    result_path: Path
    summary_path: Path
    trace_path: Path
    retrieval_chunks_path: Path
    skill_package_dir: Path
    run_id: str
    page_range: str = ""
    quality_status: str = ""
    quality_score: int | None = None


def build_source_document_packages(
    *,
    run_root: Path,
    source_root: Path | None = None,
    output_root: Path | None = None,
) -> dict[str, Any]:
    """Reorganize run/chunk outputs into one package per original source document.

    The parser may split one large scanned source into several page chunks. This
    function keeps those chunk traces as evidence, but exposes a single AI-facing
    document package for the original source file.
    """

    run_root = Path(run_root).expanduser().resolve()
    if not run_root.exists():
        raise FileNotFoundError(f"run_root does not exist: {run_root}")
    source_root = _resolve_source_root(source_root, run_root)
    output_root = Path(output_root).expanduser().resolve() if output_root else _default_output_root(run_root)
    document_root = output_root / source_root.name
    document_root.mkdir(parents=True, exist_ok=True)

    runs = _collect_source_runs(run_root)
    grouped: dict[str, list[SourceRun]] = {}
    for source_run in runs:
        grouped.setdefault(source_run.source_file, []).append(source_run)

    records: list[dict[str, Any]] = []
    for source_file, source_runs in sorted(grouped.items(), key=lambda item: item[0]):
        dest = document_root / _safe_stem(source_file)
        if dest.exists():
            shutil.rmtree(dest)
        if _needs_merge(source_runs):
            records.append(_merge_source_runs(source_file, source_runs, dest, source_root, run_root))
        else:
            records.append(_copy_single_source_run(source_runs[0], dest, source_root))

    catalog = build_corpus_catalog(root=document_root, output_dir=output_root / "corpus_catalog")
    report = {
        "format": "source_document_package_report",
        "version": "2026-06-17",
        "created_at": datetime.now().strftime("%Y%m%d%H%M"),
        "source_run_root": str(run_root),
        "source_folder": str(source_root),
        "output_root": str(output_root),
        "document_root": str(document_root),
        "total_source_documents": len(records),
        "single_document_packages": sum(1 for item in records if item.get("mode") == "single_document_copy"),
        "merged_scanned_packages": sum(1 for item in records if item.get("mode") == "merged_source_runs"),
        "records": records,
        "corpus_catalog": catalog.get("files", {}),
    }
    _write_json(output_root / "source_document_package_report.json", report)
    _write_report_md(output_root / "source_document_package_report.md", report)
    return report


def _resolve_source_root(source_root: Path | None, run_root: Path) -> Path:
    if source_root:
        return Path(source_root).expanduser().resolve()
    run_summary = _read_json(run_root / "run_summary.json")
    raw = run_summary.get("source_folder") if isinstance(run_summary, dict) else None
    if raw:
        path = Path(str(raw)).expanduser().resolve()
        if path.exists():
            return path
    manifest_root = _infer_source_root_from_manifests(run_root)
    if manifest_root:
        return manifest_root
    summary_root = _infer_source_root_from_summary(run_root)
    if summary_root:
        return summary_root
    for result_path in sorted(run_root.rglob("result.json")):
        result = _read_json(result_path)
        input_file = result.get("input_file") if isinstance(result, dict) else None
        if input_file:
            parent = Path(str(input_file)).expanduser().resolve().parent
            if parent.exists():
                return parent
    return run_root


def _infer_source_root_from_manifests(run_root: Path) -> Path | None:
    candidates: dict[Path, int] = {}
    for manifest_path in sorted(run_root.glob("batch_manifest*.json")):
        manifest = _read_json(manifest_path)
        tasks = manifest.get("tasks") if isinstance(manifest, dict) else None
        if not isinstance(tasks, list):
            continue
        for task in tasks:
            if not isinstance(task, dict) or not task.get("input"):
                continue
            path = Path(str(task["input"])).expanduser()
            if path.exists() and run_root not in path.resolve().parents:
                parent = path.resolve().parent
                candidates[parent] = candidates.get(parent, 0) + 1
    return _best_candidate(candidates)


def _infer_source_root_from_summary(run_root: Path) -> Path | None:
    summary = _read_json(run_root / "run_summary.json")
    items = summary.get("items") if isinstance(summary, dict) else None
    if not isinstance(items, list):
        return None
    source_names = [
        _normalize_source_file(str(item.get("source")))
        for item in items
        if isinstance(item, dict) and item.get("source")
    ]
    candidates: dict[Path, int] = {}
    for base in [run_root.parent.parent, Path.cwd()]:
        if not base.exists():
            continue
        for child in base.iterdir():
            if not child.is_dir() or child in {run_root, run_root.parent}:
                continue
            score = sum(1 for name in source_names if (child / name).exists())
            if score:
                child = child.resolve()
                candidates[child] = max(candidates.get(child, 0), score)
    return _best_candidate(candidates)


def _best_candidate(candidates: dict[Path, int]) -> Path | None:
    if not candidates:
        return None
    return sorted(candidates.items(), key=lambda item: (-item[1], len(str(item[0])), str(item[0])))[0][0]


def _default_output_root(run_root: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d%H%M")
    root = run_root.parent / timestamp
    if not root.exists():
        return root
    suffix = 2
    while (run_root.parent / f"{timestamp}_{suffix}").exists():
        suffix += 1
    return run_root.parent / f"{timestamp}_{suffix}"


def _collect_source_runs(run_root: Path) -> list[SourceRun]:
    summary = _read_json(run_root / "run_summary.json")
    if not isinstance(summary, dict) or not isinstance(summary.get("items"), list):
        summary = _read_json(run_root / "batch_report.json")
    scan_plan = _read_json(run_root / "scan_chunk_plan.json")
    scan_chunks = scan_plan.get("chunks", []) if isinstance(scan_plan, dict) else []
    scan_by_id = {
        str(item.get("id")): item
        for item in scan_chunks
        if isinstance(item, dict)
    }
    if isinstance(summary, dict) and isinstance(summary.get("items"), list):
        collected = []
        for item in summary["items"]:
            if isinstance(item, dict) and item.get("status", "completed") == "completed":
                source_run = _source_run_from_summary_item(item, scan_by_id=scan_by_id, run_root=run_root)
                if source_run:
                    collected.append(source_run)
        if collected:
            return collected

    collected = []
    for result_path in sorted(run_root.rglob("result.json")):
        if "document_skill" in result_path.parts:
            continue
        source_run = _source_run_from_result_path(result_path)
        if source_run:
            collected.append(source_run)
    return collected


def _source_run_from_summary_item(
    item: dict[str, Any],
    *,
    scan_by_id: dict[str, dict[str, Any]],
    run_root: Path,
) -> SourceRun | None:
    output_dir = _resolve_existing_path(item.get("output_dir"), base=run_root)
    result_path = _resolve_existing_path(item.get("result_path"), base=run_root) or (output_dir / "result.json" if output_dir else None)
    if not output_dir or not result_path or not result_path.exists():
        return None
    result = _read_json(result_path)
    if not isinstance(result, dict):
        return None
    plan = scan_by_id.get(str(item.get("id")), {})
    source_file = str(plan.get("source_file") or item.get("source_file") or item.get("original_source") or item.get("source") or _infer_source_file(result))
    page_range = str(plan.get("page_range") or item.get("page_range") or _infer_page_range(result))
    return _build_source_run(
        id=str(item.get("id") or result.get("run_id") or output_dir.name),
        source_file=_normalize_source_file(source_file),
        page_range=page_range,
        output_dir=output_dir,
        result=result,
        result_path=result_path,
        summary_path=_resolve_existing_path(item.get("summary_path"), base=run_root) or output_dir / "summary.md",
        trace_path=output_dir / "trace.json",
        retrieval_chunks_path=_resolve_existing_path(item.get("retrieval_chunks_path"), base=run_root),
        skill_package_dir=_resolve_existing_path(item.get("skill_package_dir"), base=run_root),
        quality_status=str(item.get("quality_status") or ""),
        quality_score=_int_or_none(item.get("quality_score")),
    )


def _source_run_from_result_path(result_path: Path) -> SourceRun | None:
    result = _read_json(result_path)
    if not isinstance(result, dict):
        return None
    output_dir = result_path.parent
    return _build_source_run(
        id=str(result.get("run_id") or output_dir.name),
        source_file=_normalize_source_file(_infer_source_file(result)),
        page_range=_infer_page_range(result),
        output_dir=output_dir,
        result=result,
        result_path=result_path,
        summary_path=output_dir / "summary.md",
        trace_path=output_dir / "trace.json",
        retrieval_chunks_path=None,
        skill_package_dir=None,
        quality_status=str((result.get("quality") or {}).get("status") or ""),
        quality_score=_int_or_none((result.get("quality") or {}).get("score")),
    )


def _build_source_run(
    *,
    id: str,
    source_file: str,
    page_range: str,
    output_dir: Path,
    result: dict[str, Any],
    result_path: Path,
    summary_path: Path,
    trace_path: Path,
    retrieval_chunks_path: Path | None,
    skill_package_dir: Path | None,
    quality_status: str,
    quality_score: int | None,
) -> SourceRun:
    retrieval = result.get("retrieval_export") if isinstance(result.get("retrieval_export"), dict) else {}
    skill = result.get("skill_package") if isinstance(result.get("skill_package"), dict) else {}
    return SourceRun(
        id=id,
        source_file=source_file,
        page_range=page_range,
        output_dir=output_dir,
        result_path=result_path,
        summary_path=summary_path,
        trace_path=trace_path,
        retrieval_chunks_path=retrieval_chunks_path or Path(str(retrieval.get("chunks_path") or output_dir / "retrieval" / "retrieval_chunks.jsonl")),
        skill_package_dir=skill_package_dir or Path(str(skill.get("package_dir") or output_dir / "document_skill")),
        run_id=str(result.get("run_id") or output_dir.name),
        quality_status=quality_status,
        quality_score=quality_score,
    )


def _needs_merge(source_runs: list[SourceRun]) -> bool:
    return len(source_runs) > 1 or any(item.page_range for item in source_runs)


def _copy_single_source_run(source_run: SourceRun, dest: Path, source_root: Path) -> dict[str, Any]:
    dest.mkdir(parents=True, exist_ok=True)
    for name in ["result.json", "summary.md", "trace.json"]:
        src = source_run.output_dir / name
        if src.exists():
            shutil.copy2(src, dest / name)
    for name in ["retrieval", "document_skill"]:
        src = source_run.output_dir / name
        if src.exists():
            shutil.copytree(src, dest / name)
    _rewrite_paths_under(dest, str(source_run.output_dir), str(dest))
    result_path = dest / "result.json"
    if result_path.exists():
        result = _read_json(result_path)
        if isinstance(result, dict):
            result.update(
                {
                    "package_type": "source_document",
                    "source_document_name": source_run.source_file,
                    "source_document_folder": source_root.name,
                    "output_dir": str(dest),
                    "summary_path": str(dest / "summary.md"),
                    "trace_path": str(dest / "trace.json"),
                }
            )
            if isinstance(result.get("retrieval_export"), dict):
                result["retrieval_export"].update(
                    {
                        "chunks_path": str(dest / "retrieval" / "retrieval_chunks.jsonl"),
                        "manifest_path": str(dest / "retrieval" / "retrieval_manifest.json"),
                        "quality_report_path": str(dest / "retrieval" / "retrieval_quality.json"),
                    }
                )
            _write_json(result_path, result)
    return _record(source_run.source_file, dest, source_run.run_id, "single_document_copy", [source_run])


def _merge_source_runs(source_file: str, source_runs: list[SourceRun], dest: Path, source_root: Path, run_root: Path) -> dict[str, Any]:
    dest.mkdir(parents=True, exist_ok=True)
    source_runs = sorted(source_runs, key=lambda item: _page_start(item.page_range))
    results = [_read_json(item.result_path) for item in source_runs]
    results = [item for item in results if isinstance(item, dict)]
    quality = _aggregate_quality(results)
    retrieval_stats = _merge_retrieval_chunks(source_runs, dest / "retrieval" / "retrieval_chunks.jsonl")
    references_dir = dest / "document_skill" / "references"
    references_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(dest / "retrieval" / "retrieval_chunks.jsonl", references_dir / "retrieval_chunks.jsonl")
    _write_json(dest / "retrieval" / "retrieval_manifest.json", {"source_file": source_file, "stats": retrieval_stats, "source_runs": [_run_ref(item) for item in source_runs]})
    _write_json(dest / "retrieval" / "retrieval_quality.json", {"source_file": source_file, "quality": quality, "stats": retrieval_stats})

    description = _merged_description(source_runs, source_file)
    run_id = hashlib.sha1(source_file.encode("utf-8")).hexdigest()[:12]
    package_dir = dest / "document_skill"
    result = {
        "schema_version": "mineru-data-agent.source-document-package.v1",
        "package_type": "source_document",
        "run_id": run_id,
        "source_document_name": source_file,
        "source_document_folder": source_root.name,
        "input_file": str(source_root / source_file),
        "output_dir": str(dest),
        "task": "Merge run/chunk outputs into one source-document AI package.",
        "profile": _dominant_profile(results),
        "quality": quality,
        "retrieval_export": {
            "chunks_path": str(dest / "retrieval" / "retrieval_chunks.jsonl"),
            "manifest_path": str(dest / "retrieval" / "retrieval_manifest.json"),
            "quality_report_path": str(dest / "retrieval" / "retrieval_quality.json"),
            "stats": retrieval_stats,
        },
        "skill_package": {
            "package_dir": str(package_dir),
            "files": {
                "skill": str(package_dir / "SKILL.md"),
                "overview": str(references_dir / "overview.md"),
                "compressed": str(references_dir / "compressed.md"),
                "content": str(references_dir / "content.md"),
                "structured": str(references_dir / "structured.md"),
                "evidence": str(references_dir / "evidence.md"),
                "segments": str(references_dir / "segments.md"),
                "raw_result": str(references_dir / "raw_result.json"),
                "retrieval_chunks": str(references_dir / "retrieval_chunks.jsonl"),
            },
        },
        "source_runs": [_run_ref(item) for item in source_runs],
        "source_run_root": str(run_root),
    }
    _write_json(dest / "result.json", result)
    _write_json(references_dir / "raw_result.json", result)
    _write_text(dest / "summary.md", _render_merged_summary(source_file, source_root, description, quality, retrieval_stats, source_runs))
    _write_json(
        dest / "trace.json",
        {
            "format": "source_document_merge_trace",
            "source_run_root": str(run_root),
            "source_file": source_file,
            "output_dir": str(dest),
            "operation": "merge_runs_to_one_source_document_package",
            "source_runs": [_run_ref(item) for item in source_runs],
        },
    )
    _write_text(package_dir / "SKILL.md", _render_skill_md(source_file, source_root, description, run_id, source_runs))
    _write_text(references_dir / "overview.md", _render_overview(source_file, source_root, description, quality, retrieval_stats, source_runs))
    _write_text(references_dir / "compressed.md", _combine_references(source_runs, "compressed.md", "Compressed Document View", include_descriptions=True))
    _write_text(references_dir / "content.md", _combine_references(source_runs, "content.md", "Full Content"))
    _write_text(references_dir / "structured.md", _combine_references(source_runs, "structured.md", "Structured Data"))
    _write_text(references_dir / "evidence.md", _combine_references(source_runs, "evidence.md", "Evidence"))
    _write_text(references_dir / "segments.md", _combine_references(source_runs, "segments.md", "Segments") + "\n## Merged Retrieval\n\n- `../../retrieval/retrieval_chunks.jsonl`\n- `references/retrieval_chunks.jsonl`\n")
    tables = _combine_references(source_runs, "tables.md", "Tables")
    if tables.strip():
        _write_text(references_dir / "tables.md", tables)
    return _record(source_file, dest, run_id, "merged_source_runs", source_runs, quality=quality, retrieval_stats=retrieval_stats)


def _merge_retrieval_chunks(source_runs: list[SourceRun], target: Path) -> dict[str, Any]:
    target.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    pages: set[int] = set()
    by_type: dict[str, int] = {}
    with target.open("w", encoding="utf-8") as out:
        for source_run in source_runs:
            start = _page_start(source_run.page_range)
            if not source_run.retrieval_chunks_path.exists():
                continue
            for line in source_run.retrieval_chunks_path.read_text(encoding="utf-8", errors="replace").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                if isinstance(row.get("page_no"), int):
                    row["local_page_no"] = row["page_no"]
                    row["page_no"] = row["page_no"] + start - 1
                    pages.add(row["page_no"])
                if isinstance(row.get("pages"), list):
                    row["local_pages"] = row["pages"]
                    row["pages"] = [page + start - 1 for page in row["pages"] if isinstance(page, int)]
                    pages.update(row["pages"])
                old_id = str(row.get("chunk_id") or total + 1)
                row["chunk_id"] = f"{Path(source_run.source_file).stem}:{source_run.page_range or 'full'}:{old_id}"
                row["source_run_id"] = source_run.run_id
                row["source_chunk_id"] = source_run.id
                row["source_page_range"] = source_run.page_range
                row["original_source_file"] = source_run.source_file
                content_type = str(row.get("content_type") or "unknown")
                by_type[content_type] = by_type.get(content_type, 0) + 1
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
                total += 1
    return {"total_chunks": total, "by_type": by_type, "pages": sorted(pages)}


def _combine_references(source_runs: list[SourceRun], filename: str, title: str, *, include_descriptions: bool = False) -> str:
    lines = [f"# {title}", ""]
    for source_run in source_runs:
        lines.extend([f"## {source_run.id} pages {source_run.page_range or 'full'}", ""])
        if include_descriptions:
            frontmatter = _read_frontmatter(source_run.skill_package_dir / "SKILL.md")
            description = frontmatter.get("description", "")
            if description:
                lines.extend([f"- Description: {description}", ""])
        text = _read_text(source_run.skill_package_dir / "references" / filename).strip()
        lines.extend([text or "_No content recorded for this source run._", ""])
    return "\n".join(lines).strip() + "\n"


def _render_merged_summary(
    source_file: str,
    source_root: Path,
    description: str,
    quality: dict[str, Any],
    retrieval_stats: dict[str, Any],
    source_runs: list[SourceRun],
) -> str:
    rows = "\n".join(
        f"| {item.id} | {item.page_range or 'full'} | `{item.run_id}` | {item.quality_status} | {item.quality_score or ''} |"
        for item in source_runs
    )
    return f"""# {Path(source_file).stem}

- Source folder: `{source_root.name}`
- Source file: `{source_file}`
- Package type: source document package
- Source runs: {len(source_runs)}
- Quality: `{quality.get('status')}` score={quality.get('score')} avg={quality.get('average_score')}
- Retrieval chunks: {retrieval_stats.get('total_chunks')}
- Document skill: `document_skill/SKILL.md`

## Description

{description}

## Source Run Map

| Run | Pages | Run ID | Quality | Score |
|---|---:|---|---|---:|
{rows}

## Loading Guide

Read `document_skill/SKILL.md` first. Use `document_skill/references/compressed.md` for compact full-document understanding, and load `content.md` or `retrieval/retrieval_chunks.jsonl` only when exact evidence is needed.
"""


def _render_skill_md(source_file: str, source_root: Path, description: str, run_id: str, source_runs: list[SourceRun]) -> str:
    name = _slug(Path(source_file).stem)
    return f"""---
name: {name}
description: {description}
---

# Document Skill Package

This package is generated by MinerU Data Agent for downstream AI workflows.

## Loading Guide

- Load `references/overview.md` first for task, quality, and artifact orientation.
- Load `references/compressed.md` for a compact full-document understanding before reading raw content.
- Load `references/structured.md` when fields, sections, and task-specific answers are needed.
- Load `references/evidence.md` before making claims that require provenance or quality context.
- Load `references/segments.md` for retrieval chunks and block-level context.
- Load `references/content.md` only when the original full text is required.

## Source

- Source folder: `{source_root.name}`
- Input: `{source_file}`
- Package run ID: `{run_id}`
- Source runs: {len(source_runs)}
- Result schema: `mineru-data-agent.source-document-package.v1`
"""


def _render_overview(
    source_file: str,
    source_root: Path,
    description: str,
    quality: dict[str, Any],
    retrieval_stats: dict[str, Any],
    source_runs: list[SourceRun],
) -> str:
    lines = [
        "# Overview",
        "",
        f"- Source folder: `{source_root.name}`",
        f"- Input: `{source_file}`",
        f"- Quality: `{quality.get('status', 'unknown')}` score={quality.get('score', '')}",
        f"- Source runs: {len(source_runs)}",
        f"- Retrieval chunks: {retrieval_stats.get('total_chunks', 0)}",
        "",
        "## Description",
        "",
        description,
        "",
        "## Source Run Map",
        "",
        "| Run | Pages | Run ID | Retrieval chunks | Quality |",
        "|---|---:|---|---:|---|",
    ]
    for source_run in source_runs:
        lines.append(
            f"| {source_run.id} | {source_run.page_range or 'full'} | `{source_run.run_id}` | "
            f"{_line_count(source_run.retrieval_chunks_path)} | {source_run.quality_status} |"
        )
    return "\n".join(lines).strip() + "\n"


def _record(
    source_file: str,
    dest: Path,
    run_id: str,
    mode: str,
    source_runs: list[SourceRun],
    *,
    quality: dict[str, Any] | None = None,
    retrieval_stats: dict[str, Any] | None = None,
) -> dict[str, Any]:
    missing = [name for name in STANDARD_PACKAGE_FILES if not (dest / name).exists()]
    return {
        "source": source_file,
        "output_dir": str(dest),
        "run_id": run_id,
        "mode": mode,
        "source_run_count": len(source_runs),
        "quality_status": (quality or {}).get("status") or source_runs[0].quality_status,
        "quality_score": (quality or {}).get("score") or source_runs[0].quality_score,
        "retrieval_chunks": (retrieval_stats or {}).get("total_chunks"),
        "missing_standard_files": missing,
    }


def _infer_source_file(result: dict[str, Any]) -> str:
    input_file = Path(str(result.get("input_file") or "document"))
    match = _chunk_name_match(input_file.name)
    if match:
        return f"{match.group('stem')}{input_file.suffix}"
    return input_file.name


def _infer_page_range(result: dict[str, Any]) -> str:
    input_file = Path(str(result.get("input_file") or ""))
    match = _chunk_name_match(input_file.name)
    if not match:
        return ""
    return f"{int(match.group('start'))}-{int(match.group('end'))}"


def _chunk_name_match(name: str) -> re.Match[str] | None:
    return re.match(r"(?P<stem>.+)__pages_(?P<start>\d+)-(?P<end>\d+)(?P<suffix>\.[^.]+)$", name)


def _normalize_source_file(value: str) -> str:
    name = Path(value).name
    match = _chunk_name_match(name)
    if match:
        return f"{match.group('stem')}{match.group('suffix')}"
    return name


def _safe_stem(source_file: str) -> str:
    stem = Path(source_file).stem
    cleaned = re.sub(r'[<>:"/\\|?*]+', "_", stem).strip()
    return cleaned or hashlib.sha1(source_file.encode("utf-8")).hexdigest()[:12]


def _slug(text: str) -> str:
    raw = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", text).strip("-").lower()
    return raw[:80] or hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def _page_start(page_range: str) -> int:
    match = re.match(r"\s*(\d+)\s*-", page_range or "")
    return int(match.group(1)) if match else 1


def _aggregate_quality(results: list[dict[str, Any]]) -> dict[str, Any]:
    qualities = [item.get("quality") or {} for item in results]
    if not qualities:
        return {"status": "unknown", "score": 0, "average_score": 0, "issue_count": 0, "issues": []}
    issues = []
    for result in results:
        for issue in (result.get("quality") or {}).get("issues") or []:
            enriched = dict(issue)
            enriched.setdefault("source_run_id", result.get("run_id"))
            issues.append(enriched)
    scores = [_int_or_none(item.get("score")) or 0 for item in qualities]
    worst = max(qualities, key=lambda item: _status_rank(str(item.get("status") or "unknown")))
    return {
        "status": worst.get("status") or "unknown",
        "score": min(scores) if scores else 0,
        "average_score": round(sum(scores) / len(scores), 2) if scores else 0,
        "issue_count": len(issues),
        "issues": issues,
    }


def _status_rank(status: str) -> int:
    return {"pass": 0, "pass_with_warnings": 1, "needs_review": 2, "failed": 3, "error": 3}.get(status, 2)


def _dominant_profile(results: list[dict[str, Any]]) -> str:
    counts: dict[str, int] = {}
    for result in results:
        profile = str(result.get("profile") or "")
        if profile:
            counts[profile] = counts.get(profile, 0) + 1
    if not counts:
        return "auto"
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def _merged_description(source_runs: list[SourceRun], source_file: str) -> str:
    descriptions = []
    for source_run in source_runs:
        frontmatter = _read_frontmatter(source_run.skill_package_dir / "SKILL.md")
        description = frontmatter.get("description", "").strip()
        if description and description not in descriptions:
            descriptions.append(description)
    return "; ".join(descriptions)[:800] or f"Source document package for {source_file}."


def _run_ref(source_run: SourceRun) -> dict[str, Any]:
    return {
        "id": source_run.id,
        "run_id": source_run.run_id,
        "source_file": source_run.source_file,
        "page_range": source_run.page_range,
        "output_dir": str(source_run.output_dir),
        "result_path": str(source_run.result_path),
        "summary_path": str(source_run.summary_path),
        "trace_path": str(source_run.trace_path),
        "retrieval_chunks_path": str(source_run.retrieval_chunks_path),
        "skill_package_dir": str(source_run.skill_package_dir),
        "quality_status": source_run.quality_status,
        "quality_score": source_run.quality_score,
    }


def _read_frontmatter(path: Path) -> dict[str, str]:
    text = _read_text(path, limit=4000)
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    data: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip()
    return data


def _read_json(path: Path) -> Any:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return {}


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_text(path: Path, *, limit: int | None = None) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[:limit] if limit is not None else text


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_report_md(path: Path, report: dict[str, Any]) -> None:
    rows = "\n".join(f"- `{Path(item['output_dir']).name}`: {item['mode']}" for item in report.get("records", []))
    _write_text(
        path,
        "# Source Document Package Report\n\n"
        f"- Output root: `{report.get('output_root')}`\n"
        f"- Document root: `{report.get('document_root')}`\n"
        f"- Source documents: {report.get('total_source_documents')}\n"
        f"- Single document packages: {report.get('single_document_packages')}\n"
        f"- Merged packages: {report.get('merged_scanned_packages')}\n"
        f"- Corpus catalog: `{(report.get('corpus_catalog') or {}).get('catalog_json', '')}`\n\n"
        "## Packages\n\n"
        f"{rows}\n",
    )


def _resolve_existing_path(value: Any, *, base: Path) -> Path | None:
    if not value:
        return None
    path = Path(str(value)).expanduser()
    if not path.is_absolute():
        path = base / path
    path = path.resolve()
    return path if path.exists() else path


def _rewrite_paths_under(dest: Path, old: str, new: str) -> None:
    for file in dest.rglob("*"):
        if not file.is_file() or file.suffix.lower() not in {".json", ".jsonl", ".md"}:
            continue
        text = file.read_text(encoding="utf-8", errors="replace")
        file.write_text(text.replace(old, new), encoding="utf-8")


def _line_count(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for _ in path.open("r", encoding="utf-8", errors="replace"))


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
