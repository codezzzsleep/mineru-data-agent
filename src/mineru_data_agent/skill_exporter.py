from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any, Mapping


def build_document_skill_package(
    *,
    result: Mapping[str, Any] | Any,
    output_dir: Path,
    source_file: Path | None = None,
    understanding: Mapping[str, Any] | None = None,
    full_markdown: str = "",
) -> dict[str, Any]:
    payload = _jsonable_result(result)
    package_dir = Path(output_dir).resolve()
    references_dir = package_dir / "references"
    references_dir.mkdir(parents=True, exist_ok=True)

    source_name = Path(str(payload.get("input_file") or source_file or "document")).name
    u = dict(understanding) if isinstance(understanding, Mapping) else {}
    llm_generated = bool(u.get("name") or u.get("description") or u.get("compressed"))
    skill_name = _clean_skill_name(str(u["name"])) if u.get("name") else _skill_name(payload)
    description = _single_line(str(u["description"])) if u.get("description") else _skill_description(payload, source_name)
    compressed = str(u.get("compressed") or "").strip()
    files: dict[str, str] = {}

    skill_md = package_dir / "SKILL.md"
    overview_md = references_dir / "overview.md"
    structured_md = references_dir / "structured.md"
    tables_md = references_dir / "tables.md"
    evidence_md = references_dir / "evidence.md"
    segments_md = references_dir / "segments.md"
    raw_json = references_dir / "raw_result.json"

    skill_md.write_text(
        _render_skill_md(skill_name, description, payload, has_compressed=bool(compressed), has_content=bool(full_markdown)),
        encoding="utf-8",
    )
    overview_md.write_text(_render_overview(payload), encoding="utf-8")
    structured_md.write_text(_render_structured(payload), encoding="utf-8")
    tables_md.write_text(_render_tables(payload), encoding="utf-8")
    evidence_md.write_text(_render_evidence(payload), encoding="utf-8")
    segments_md.write_text(_render_segments(payload), encoding="utf-8")
    raw_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    files["skill"] = str(skill_md)
    files["overview"] = str(overview_md)
    files["structured"] = str(structured_md)
    files["tables"] = str(tables_md)
    files["evidence"] = str(evidence_md)
    files["segments"] = str(segments_md)
    files["raw_result"] = str(raw_json)

    # Progressive disclosure: name+description by default; compressed (LLM full-doc
    # summary) and content (raw text) loaded only on demand.
    progressive = [
        "references/overview.md",
        "references/structured.md",
        "references/tables.md",
        "references/evidence.md",
        "references/segments.md",
    ]
    if compressed:
        compressed_md = references_dir / "compressed.md"
        compressed_md.write_text(_render_compressed(skill_name, description, compressed, u), encoding="utf-8")
        files["compressed"] = str(compressed_md)
        progressive.insert(0, "references/compressed.md")
    if full_markdown:
        content_md = references_dir / "content.md"
        content_md.write_text(full_markdown, encoding="utf-8")
        files["content"] = str(content_md)
        progressive.append("references/content.md")

    retrieval_path = _copy_retrieval_chunks(payload, references_dir)
    if retrieval_path:
        files["retrieval_chunks"] = str(retrieval_path)

    stats = _package_stats(payload)
    return {
        "format": "document_skill_package",
        "version": "2026-06-17",
        "skill_name": skill_name,
        "description": description,
        "description_source": "llm" if llm_generated else "heuristic",
        "has_compressed_view": bool(compressed),
        "has_full_content": bool(full_markdown),
        "package_dir": str(package_dir),
        "files": files,
        "stats": stats,
        "loading_policy": {
            "default_context": ["name", "description"],
            "progressive_references": progressive,
            "policy": (
                "Only name+description enter the AI context by default. Read compressed.md for an "
                "LLM full-document summary, then content.md for the raw text, only when the task needs it."
            ),
        },
    }


def _jsonable_result(result: Mapping[str, Any] | Any) -> dict[str, Any]:
    if isinstance(result, Mapping):
        return dict(result)
    if hasattr(result, "to_jsonable"):
        data = result.to_jsonable()
        return dict(data) if isinstance(data, Mapping) else {}
    return {}


def _skill_name(payload: Mapping[str, Any]) -> str:
    source = Path(str(payload.get("input_file") or "document")).stem
    run_id = str(payload.get("run_id") or "run")[:12]
    raw = f"document-{source}-{run_id}".lower()
    return _clean_skill_name(raw) or f"document-{run_id}"


def _clean_skill_name(value: str) -> str:
    clean = re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")
    clean = re.sub(r"-{2,}", "-", clean)
    return clean[:64]


def _skill_description(payload: Mapping[str, Any], source_name: str) -> str:
    task = _single_line(str(payload.get("task") or "parsed document"))
    profile = str(payload.get("profile") or "general_document")
    extracted = _as_dict(payload.get("extracted"))
    summary = _as_dict(extracted.get("content_summary"))
    return (
        f"Use this skill for AI follow-up work on {source_name}: task={task}; "
        f"profile={profile}; blocks={summary.get('item_count', 0)}; "
        f"tables={len(_as_list(extracted.get('tables')))}; "
        f"quality={_as_dict(payload.get('quality')).get('status', 'unknown')}."
    )[:800]


def _render_skill_md(
    skill_name: str,
    description: str,
    payload: Mapping[str, Any],
    *,
    has_compressed: bool = False,
    has_content: bool = False,
) -> str:
    loading_guide = [
        "- Load `references/overview.md` first for task, quality, and artifact orientation.",
        "- Load `references/structured.md` when fields, sections, and task-specific answers are needed.",
        "- Load `references/tables.md` when financial or tabular evidence is needed.",
        "- Load `references/evidence.md` before making claims that require provenance or quality context.",
        "- Load `references/segments.md` for retrieval chunks and block-level context.",
    ]
    if has_compressed:
        loading_guide.insert(1, "- Load `references/compressed.md` for a compact full-document understanding before reading raw content.")
    if has_content:
        loading_guide.append("- Load `references/content.md` only when the original full text is required.")
    return "\n".join(
        [
            "---",
            f"name: {skill_name}",
            f"description: {description}",
            "---",
            "",
            "# Document Skill Package",
            "",
            "This package is generated by MinerU Data Agent for downstream AI workflows.",
            "",
            "## Loading Guide",
            "",
            *loading_guide,
            "",
            "## Source",
            "",
            f"- Run ID: `{payload.get('run_id', '')}`",
            f"- Input: `{payload.get('input_file', '')}`",
            f"- Result schema: `{payload.get('schema_version', '')}`",
        ]
    ).strip() + "\n"


def _render_compressed(
    skill_name: str,
    description: str,
    compressed: str,
    understanding: Mapping[str, Any],
) -> str:
    lines = [
        "# Compressed Document View",
        "",
        f"- Skill: `{skill_name}`",
        f"- Description: {description}",
        "",
        "## Summary",
        "",
        compressed,
    ]
    topics = _as_list(understanding.get("topics"))
    entities = _as_list(understanding.get("entities"))
    if topics:
        lines.extend(["", "## Topics", ""])
        lines.extend(f"- {item}" for item in topics[:50])
    if entities:
        lines.extend(["", "## Entities", ""])
        lines.extend(f"- {item}" for item in entities[:80])
    return "\n".join(lines).strip() + "\n"


def _render_overview(payload: Mapping[str, Any]) -> str:
    extracted = _as_dict(payload.get("extracted"))
    summary = _as_dict(extracted.get("content_summary"))
    quality = _as_dict(payload.get("quality"))
    routing = _as_dict(_as_dict(payload.get("execution_control")).get("workflow_routing"))
    lines = [
        "# Overview",
        "",
        f"- Run ID: `{payload.get('run_id', '')}`",
        f"- Task: {payload.get('task', '')}",
        f"- Profile: `{payload.get('profile', '')}`",
        f"- Input: `{payload.get('input_file', '')}`",
        f"- Quality: `{quality.get('status', 'unknown')}` score={quality.get('score', '')}",
        f"- Blocks: {summary.get('item_count', 0)}",
        f"- Pages: {summary.get('page_count', 0)}",
        f"- Sections: {len(_as_list(extracted.get('sections')))}",
        f"- Tables: {len(_as_list(extracted.get('tables')))}",
        f"- Key-values: {len(_as_list(extracted.get('key_values')))}",
        f"- Retrieval chunks: {_as_dict(_as_dict(payload.get('retrieval_export')).get('stats')).get('total_chunks', 0)}",
        "",
        "## Workflow Routing",
        "",
    ]
    if routing:
        lines.extend(
            [
                f"- Requested runner: `{routing.get('requested_runner', '')}`",
                f"- Selected runner: `{routing.get('selected_runner', '')}`",
                f"- Selected tool: `{routing.get('selected_tool', '')}`",
                f"- Route mode: `{routing.get('route_mode', '')}`",
                f"- Status: `{routing.get('status', '')}`",
            ]
        )
        for reason in _as_list(routing.get("reasons"))[:6]:
            lines.append(f"- Reason: {reason}")
    else:
        lines.append("- Routing metadata was not recorded for this run.")
    return "\n".join(lines).strip() + "\n"


def _render_structured(payload: Mapping[str, Any]) -> str:
    extracted = _as_dict(payload.get("extracted"))
    task_result = _as_dict(extracted.get("task_result"))
    lines = ["# Structured Data", ""]
    answers = _as_dict(task_result.get("answers"))
    if answers:
        lines.extend(["## Task Answers", "", "```json", json.dumps(answers, ensure_ascii=False, indent=2), "```", ""])
    key_values = _as_list(extracted.get("key_values"))
    if key_values:
        lines.extend(["## Key Values", ""])
        for item in key_values[:80]:
            if isinstance(item, Mapping):
                lines.append(f"- **{item.get('key', '')}**: {item.get('value', '')}")
        lines.append("")
    sections = _as_list(extracted.get("sections"))
    if sections:
        lines.extend(["## Sections", ""])
        for item in sections[:40]:
            if isinstance(item, Mapping):
                title = _single_line(str(item.get("title") or "section"))
                text = _single_line(str(item.get("text") or ""))[:500]
                lines.append(f"- `{item.get('level', 1)}` {title}: {text}")
    if len(lines) <= 2:
        lines.append("No structured fields were extracted.")
    return "\n".join(lines).strip() + "\n"


def _render_tables(payload: Mapping[str, Any]) -> str:
    tables = _as_list(_as_dict(payload.get("extracted")).get("tables"))
    lines = ["# Tables", ""]
    if not tables:
        lines.append("No tables were extracted.")
        return "\n".join(lines).strip() + "\n"
    for index, table in enumerate(tables[:20], start=1):
        if not isinstance(table, Mapping):
            continue
        headers = [str(item) for item in _as_list(table.get("headers"))]
        rows = _as_list(table.get("rows"))
        lines.extend([f"## Table {index}", "", f"- Rows: {table.get('row_count', len(rows))}", f"- Columns: {table.get('column_count', len(headers))}", ""])
        if headers:
            lines.append("| " + " | ".join(_escape_cell(item) for item in headers) + " |")
            lines.append("| " + " | ".join("---" for _ in headers) + " |")
            for row in rows[:20]:
                row_values = [str(item) for item in _as_list(row)]
                row_values = row_values + [""] * max(0, len(headers) - len(row_values))
                lines.append("| " + " | ".join(_escape_cell(item) for item in row_values[: len(headers)]) + " |")
        else:
            lines.extend(["```json", json.dumps(table, ensure_ascii=False, indent=2)[:4000], "```"])
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _render_evidence(payload: Mapping[str, Any]) -> str:
    extracted = _as_dict(payload.get("extracted"))
    quality = _as_dict(payload.get("quality"))
    recovery = _as_dict(payload.get("recovery_decision"))
    evidence = _as_list(extracted.get("field_evidence"))
    issues = _as_list(quality.get("issues"))
    lines = ["# Evidence And Quality", ""]
    lines.extend(["## Quality", "", f"- Status: `{quality.get('status', 'unknown')}`", f"- Score: {quality.get('score', '')}", ""])
    if issues:
        lines.extend(["## Issues", ""])
        for issue in issues[:80]:
            if isinstance(issue, Mapping):
                lines.append(f"- [{issue.get('level', '')}] `{issue.get('code', '')}`: {issue.get('message', '')}")
        lines.append("")
    if evidence:
        lines.extend(["## Field Evidence", ""])
        for item in evidence[:80]:
            if isinstance(item, Mapping):
                provenance = _as_dict(item.get("provenance"))
                lines.append(
                    f"- **{item.get('key', '')}** confidence={item.get('confidence', '')} "
                    f"page={provenance.get('page_no', '')} line={provenance.get('line', '')}: "
                    f"{_single_line(str(item.get('evidence_text', '')))[:400]}"
                )
        lines.append("")
    lines.extend(["## Recovery", "", f"- Decision: `{recovery.get('decision', 'unknown')}`", f"- Selected attempt: `{recovery.get('selected_attempt', 'initial')}`"])
    for attempt in _as_list(recovery.get("attempts"))[:20]:
        if isinstance(attempt, Mapping):
            lines.append(f"- Attempt `{attempt.get('name', '')}`: {attempt.get('quality_status', '')} score={attempt.get('score', '')}")
    return "\n".join(lines).strip() + "\n"


def _render_segments(payload: Mapping[str, Any]) -> str:
    retrieval = _as_dict(payload.get("retrieval_export"))
    stats = _as_dict(retrieval.get("stats"))
    lines = [
        "# Segments",
        "",
        f"- Chunks path: `{retrieval.get('chunks_path', '')}`",
        f"- Manifest path: `{retrieval.get('manifest_path', '')}`",
        f"- Total chunks: {stats.get('total_chunks', 0)}",
        f"- Types: {json.dumps(stats.get('by_type', {}), ensure_ascii=False)}",
        f"- Pages: {json.dumps(stats.get('pages', []), ensure_ascii=False)}",
        "",
        "The package keeps chunk references separate so an AI client can load only the relevant context for a follow-up task.",
    ]
    return "\n".join(lines).strip() + "\n"


def _copy_retrieval_chunks(payload: Mapping[str, Any], references_dir: Path) -> Path | None:
    chunks_path = _as_dict(payload.get("retrieval_export")).get("chunks_path")
    if not chunks_path:
        return None
    source = Path(str(chunks_path))
    if not source.exists():
        return None
    target = references_dir / "retrieval_chunks.jsonl"
    shutil.copy2(source, target)
    return target


def _package_stats(payload: Mapping[str, Any]) -> dict[str, Any]:
    extracted = _as_dict(payload.get("extracted"))
    return {
        "sections": len(_as_list(extracted.get("sections"))),
        "tables": len(_as_list(extracted.get("tables"))),
        "key_values": len(_as_list(extracted.get("key_values"))),
        "field_evidence": len(_as_list(extracted.get("field_evidence"))),
        "retrieval_chunks": _as_dict(_as_dict(payload.get("retrieval_export")).get("stats")).get("total_chunks", 0),
    }


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _single_line(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _escape_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
