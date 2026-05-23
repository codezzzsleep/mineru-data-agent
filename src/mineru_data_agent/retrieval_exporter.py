from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .extractors import extract_markdown_tables, extract_sections


NOISE_TYPES = {
    "page_header",
    "page_footer",
    "page_number",
    "header",
    "footer",
    "page_aside_text",
    "aside_text",
}
TEXT_TYPES = {"text", "paragraph", "list", "list_item", "page_footnote", "title"}
HEADING_TYPES = {"title", "heading"}
TABLE_TYPES = {"table"}
FIGURE_TYPES = {"image", "figure"}
FORMULA_TYPES = {"equation_interline", "equation_inline", "formula"}
LOW_VALUE_SECTION_RE = re.compile(
    r"^\s*(contents|table of contents|list of figures|list of tables|revision history|document history|change history)\s*$",
    re.IGNORECASE,
)


@dataclass
class RetrievalChunk:
    chunk_id: str
    page_no: int
    content_type: str
    section_title: str
    chunk_text: str
    image_path: str = ""
    pages: list[int] = field(default_factory=list)

    def to_jsonable(self) -> dict[str, Any]:
        return asdict(self)


def build_retrieval_export(
    *,
    markdown: str,
    content_list: list[Any],
    output_dir: Path,
    doc_id: str,
    source_file: Path,
) -> dict[str, Any]:
    """Write retrieval-ready chunks derived from this agent run."""

    output_dir.mkdir(parents=True, exist_ok=True)
    chunks, quality_report = build_retrieval_chunks(markdown=markdown, content_list=content_list, doc_id=doc_id)

    chunks_path = output_dir / "retrieval_chunks.jsonl"
    manifest_path = output_dir / "retrieval_manifest.json"
    quality_path = output_dir / "retrieval_quality.json"

    chunks_path.write_text(
        "".join(json.dumps(chunk.to_jsonable(), ensure_ascii=False) + "\n" for chunk in chunks),
        encoding="utf-8",
    )
    stats = _chunk_stats(chunks)
    manifest = {
        "doc_id": doc_id,
        "source_file": str(source_file),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "output_files": {
            "chunks_jsonl": str(chunks_path),
            "manifest": str(manifest_path),
            "quality_report": str(quality_path),
        },
        "schema": ["chunk_id", "page_no", "pages", "content_type", "section_title", "chunk_text", "image_path"],
        "chunking_policy": {
            "source_priority": ["content_list", "markdown"],
            "skip_noise_blocks": sorted(NOISE_TYPES),
            "skip_low_value_sections": True,
            "merge_short_text": "same-page only",
            "target_chunk_chars": "1200-3600",
        },
        "stats": stats,
    }
    quality_report["summary"] = {
        "total_skipped_blocks": len(quality_report["skipped_blocks"]),
        "total_parse_errors": len(quality_report["parse_errors"]),
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    quality_path.write_text(json.dumps(quality_report, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "chunks_path": str(chunks_path),
        "manifest_path": str(manifest_path),
        "quality_report_path": str(quality_path),
        "stats": stats,
    }


def build_retrieval_chunks(*, markdown: str, content_list: list[Any], doc_id: str) -> tuple[list[RetrievalChunk], dict[str, Any]]:
    error_report: dict[str, Any] = {"skipped_blocks": [], "parse_errors": []}
    blocks = list(_iter_content_blocks(content_list, error_report))
    if blocks:
        return _chunks_from_blocks(blocks, doc_id, error_report), error_report
    return _chunks_from_markdown(markdown, doc_id, error_report), error_report


def _iter_content_blocks(content_list: list[Any], error_report: dict[str, Any]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for index, item in enumerate(content_list):
        if isinstance(item, list):
            for block_index, block in enumerate(item):
                if isinstance(block, dict):
                    normalized = dict(block)
                    normalized.setdefault("page_idx", index)
                    normalized.setdefault("block_idx", block_index)
                    blocks.append(normalized)
                else:
                    error_report["parse_errors"].append({"index": index, "reason": "non-dict block in page"})
        elif isinstance(item, dict):
            normalized = dict(item)
            normalized.setdefault("block_idx", index)
            blocks.append(normalized)
        else:
            error_report["parse_errors"].append({"index": index, "reason": "unsupported content item"})
    return blocks


def _chunks_from_blocks(
    blocks: list[dict[str, Any]],
    doc_id: str,
    error_report: dict[str, Any],
) -> list[RetrievalChunk]:
    chunks: list[RetrievalChunk] = []
    text_buffer: list[dict[str, Any]] = []
    section_title = "document"
    skip_section = False

    def flush_text() -> None:
        nonlocal text_buffer
        if not text_buffer:
            return
        merged = "\n".join(item["text"] for item in text_buffer if item["text"]).strip()
        pages = sorted({int(item["page_no"]) for item in text_buffer})
        page_no = pages[0]
        title = text_buffer[0]["section_title"]
        text_buffer = []
        for part in _split_long_text(merged):
            if part.strip():
                chunks.append(_make_chunk(doc_id, chunks, page_no, "text", title, part, pages=pages))

    for block in blocks:
        raw_type = str(block.get("type", "unknown"))
        page_no = _page_no(block)
        block_id = f"p{page_no}_b{block.get('block_idx', len(chunks))}"

        if raw_type in NOISE_TYPES:
            error_report["skipped_blocks"].append({"block_id": block_id, "type": raw_type, "reason": "noise"})
            continue

        text = _extract_block_text(block).strip()
        if raw_type in HEADING_TYPES or _looks_like_markdown_heading(text):
            flush_text()
            section_title = _clean_section_title(_strip_heading_marks(text))
            skip_section = bool(LOW_VALUE_SECTION_RE.match(section_title))
            if skip_section:
                error_report["skipped_blocks"].append(
                    {"block_id": block_id, "type": raw_type, "reason": "low_value_section", "section_title": section_title}
                )
            continue

        if skip_section:
            error_report["skipped_blocks"].append(
                {"block_id": block_id, "type": raw_type, "reason": "inside_low_value_section", "section_title": section_title}
            )
            continue

        content_type = _map_content_type(raw_type)
        if content_type == "text":
            if not text:
                error_report["skipped_blocks"].append({"block_id": block_id, "type": raw_type, "reason": "empty_text"})
                continue
            if text_buffer and page_no != text_buffer[-1]["page_no"]:
                flush_text()
            text_buffer.append({"text": text, "page_no": page_no, "section_title": section_title})
            if _estimate_tokens("\n".join(item["text"] for item in text_buffer)) >= 650:
                flush_text()
            continue

        flush_text()
        if content_type == "table":
            table_text = _extract_table_text(block) or text
            if table_text.strip():
                for part in _split_long_text(table_text):
                    chunks.append(_make_chunk(doc_id, chunks, page_no, "table", section_title, part))
            else:
                error_report["skipped_blocks"].append({"block_id": block_id, "type": raw_type, "reason": "empty_table"})
        elif content_type == "figure":
            image_path = _extract_image_path(block)
            figure_text = text or _caption_text(block)
            if figure_text.strip() or image_path:
                chunks.append(_make_chunk(doc_id, chunks, page_no, "figure", section_title, figure_text or "Figure image", image_path))
            else:
                error_report["skipped_blocks"].append({"block_id": block_id, "type": raw_type, "reason": "weak_figure"})
        elif content_type == "formula":
            if text:
                chunks.append(_make_chunk(doc_id, chunks, page_no, "formula", section_title, text))
            else:
                error_report["skipped_blocks"].append({"block_id": block_id, "type": raw_type, "reason": "empty_formula"})
        else:
            error_report["skipped_blocks"].append({"block_id": block_id, "type": raw_type, "reason": "unsupported"})

    flush_text()
    return chunks


def _chunks_from_markdown(markdown: str, doc_id: str, error_report: dict[str, Any]) -> list[RetrievalChunk]:
    chunks: list[RetrievalChunk] = []
    for section_index, section in enumerate(extract_sections(markdown), start=1):
        section_title = _clean_section_title(section.get("title", "document"))
        if LOW_VALUE_SECTION_RE.match(section_title):
            error_report["skipped_blocks"].append(
                {"block_id": f"section_{section_index}", "type": "section", "reason": "low_value_section"}
            )
            continue
        for part in _split_long_text(section.get("text", "")):
            if part.strip():
                chunks.append(_make_chunk(doc_id, chunks, 1, "text", section_title, part))

    for table in extract_markdown_tables(markdown):
        table_text = _table_dict_to_text(table)
        if table_text.strip():
            chunks.append(_make_chunk(doc_id, chunks, 1, "table", "document", table_text))
    return chunks


def _make_chunk(
    doc_id: str,
    chunks: list[RetrievalChunk],
    page_no: int,
    content_type: str,
    section_title: str,
    chunk_text: str,
    image_path: str = "",
    pages: list[int] | None = None,
) -> RetrievalChunk:
    sequence = len(chunks) + 1
    chunk_pages = sorted({int(page) for page in (pages or [page_no]) if int(page) >= 1})
    return RetrievalChunk(
        chunk_id=f"{_slug_doc_id(doc_id)}:p{page_no}:{content_type}:{sequence}",
        page_no=page_no,
        pages=chunk_pages or [page_no],
        content_type=content_type,
        section_title=_clean_section_title(section_title),
        chunk_text=_clean_text(chunk_text),
        image_path=image_path,
    )


def _map_content_type(raw_type: str) -> str:
    if raw_type in TEXT_TYPES:
        return "text"
    if raw_type in TABLE_TYPES:
        return "table"
    if raw_type in FIGURE_TYPES:
        return "figure"
    if raw_type in FORMULA_TYPES:
        return "formula"
    return "unsupported"


def _extract_block_text(block: dict[str, Any]) -> str:
    if block.get("text"):
        return str(block.get("text", ""))
    content = block.get("content")
    if isinstance(content, str):
        return content
    if not isinstance(content, dict):
        return ""

    keys = [
        "paragraph_content",
        "list_items",
        "title_content",
        "page_footnote_content",
        "page_header_content",
        "page_footer_content",
        "page_number_content",
        "page_aside_text_content",
        "image_caption",
        "image_footnote",
        "table_caption",
        "table_footnote",
    ]
    texts: list[str] = []
    for key in keys:
        texts.extend(_extract_text_fragments(content.get(key)))
    if content.get("math_content"):
        texts.append(str(content["math_content"]))
    return "\n".join(text for text in texts if text)


def _extract_text_fragments(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        fragments: list[str] = []
        for item in value:
            if isinstance(item, dict):
                if item.get("content"):
                    fragments.append(str(item["content"]))
                if item.get("item_content"):
                    fragments.extend(_extract_text_fragments(item["item_content"]))
            elif isinstance(item, str):
                fragments.append(item)
        return fragments
    return []


def _extract_table_text(block: dict[str, Any]) -> str:
    content = block.get("content")
    if not isinstance(content, dict):
        return _extract_block_text(block)
    caption = " ".join(_extract_text_fragments(content.get("table_caption"))).strip()
    footnote = " ".join(_extract_text_fragments(content.get("table_footnote"))).strip()
    html = str(content.get("html", "") or "")
    rows: list[list[str]] = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", html, flags=re.IGNORECASE | re.DOTALL):
        cells = [
            _clean_text(re.sub(r"<[^>]+>", "", cell))
            for cell in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, flags=re.IGNORECASE | re.DOTALL)
        ]
        if any(cells):
            rows.append(cells)
    parts: list[str] = []
    if caption:
        parts.append(f"Table: {caption}")
    if rows:
        parts.append("Columns: " + " | ".join(rows[0]))
        for index, row in enumerate(rows[1:], start=1):
            parts.append(f"Row {index}: " + " | ".join(row))
    if footnote:
        parts.append(f"Note: {footnote}")
    return "\n".join(parts)


def _table_dict_to_text(table: dict[str, Any]) -> str:
    parts = []
    headers = table.get("headers") or []
    if headers:
        parts.append("Columns: " + " | ".join(headers))
    for index, row in enumerate(table.get("rows") or [], start=1):
        parts.append(f"Row {index}: " + " | ".join(row))
    return "\n".join(parts)


def _extract_image_path(block: dict[str, Any]) -> str:
    if block.get("image_path"):
        return str(block["image_path"])
    content = block.get("content")
    if isinstance(content, dict):
        source = content.get("image_source")
        if isinstance(source, dict) and source.get("path"):
            return str(source["path"])
    return ""


def _caption_text(block: dict[str, Any]) -> str:
    content = block.get("content")
    if not isinstance(content, dict):
        return ""
    return " ".join(_extract_text_fragments(content.get("image_caption"))).strip()


def _page_no(block: dict[str, Any]) -> int:
    for key in ("page_no", "page"):
        value = block.get(key)
        if isinstance(value, int):
            return max(value, 1)
    page_idx = block.get("page_idx")
    if isinstance(page_idx, int):
        return page_idx + 1
    return 1


def _split_long_text(text: str, hard_cap_tokens: int = 900) -> list[str]:
    text = _clean_text(text)
    if _estimate_tokens(text) <= hard_cap_tokens:
        return [text] if text else []

    parts: list[str] = []
    current: list[str] = []
    current_tokens = 0
    for paragraph in re.split(r"\n{2,}", text):
        tokens = _estimate_tokens(paragraph)
        if current and current_tokens + tokens > hard_cap_tokens:
            parts.append("\n\n".join(current))
            current = []
            current_tokens = 0
        if tokens > hard_cap_tokens:
            sentences = re.split(r"(?<=[.!?。！？])\s+", paragraph)
            for sentence in sentences:
                sentence_tokens = _estimate_tokens(sentence)
                if current and current_tokens + sentence_tokens > hard_cap_tokens:
                    parts.append("\n\n".join(current))
                    current = []
                    current_tokens = 0
                current.append(sentence)
                current_tokens += sentence_tokens
        else:
            current.append(paragraph)
            current_tokens += tokens
    if current:
        parts.append("\n\n".join(current))
    return [part for part in parts if part.strip()]


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _looks_like_markdown_heading(text: str) -> bool:
    stripped = text.strip()
    return "\n" not in stripped and bool(re.match(r"^#{1,6}\s+\S+", stripped))


def _strip_heading_marks(text: str) -> str:
    return re.sub(r"^#{1,6}\s+", "", text.strip())


def _clean_section_title(title: str) -> str:
    clean = re.sub(r"\s+", " ", (title or "").strip())
    return clean or "document"


def _clean_text(text: str) -> str:
    clean = re.sub(r"\r\n?", "\n", text or "")
    clean = re.sub(r"[ \t]+", " ", clean)
    clean = re.sub(r"\n{3,}", "\n\n", clean)
    return clean.strip()


def _slug_doc_id(doc_id: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z_.:-]+", "_", doc_id).strip("_")
    return slug or "document"


def _chunk_stats(chunks: list[RetrievalChunk]) -> dict[str, Any]:
    by_type: dict[str, int] = {}
    for chunk in chunks:
        by_type[chunk.content_type] = by_type.get(chunk.content_type, 0) + 1
    pages = sorted({page for chunk in chunks for page in (chunk.pages or [chunk.page_no])})
    return {
        "total_chunks": len(chunks),
        "by_type": by_type,
        "pages": pages,
    }
