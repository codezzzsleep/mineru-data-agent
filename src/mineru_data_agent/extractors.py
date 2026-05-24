from __future__ import annotations

import json
import re
import zipfile
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
TABLE_ROW_RE = re.compile(r"^\s*\|(.+)\|\s*$")
NUMBER_RE = re.compile(r"(?<![0-9A-Za-z./年月日-])[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?%?(?![0-9A-Za-z./年月日-])")
DATE_RE = re.compile(
    r"(?:20\d{2}[-/.年]\d{1,2}[-/.月]\d{1,2}(?:日)?)|"
    r"(?:\d{1,2}[-/.]\d{1,2}[-/.]20\d{2})"
)
RECOMMENDATION_KEYS = ("建议", "处理建议", "整改", "措施", "action", "recommend")
ANOMALY_WORDS = ("异常", "风险", "问题", "复核", "告警", "缺陷", "error", "warning", "risk", "issue")
KEY_VALUE_PREFIX_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)、]|[（(]?\d+[)）])\s*")
KEY_VALUE_DELIMITERS = ("：", ":")
TABLE_KEY_HEADERS = {"key", "field", "name", "字段", "项目", "科目", "条款", "指标"}
TABLE_VALUE_HEADERS = {"value", "amount", "status", "description", "值", "数值", "金额", "状态", "说明", "内容"}
CROSS_PAGE_REFERENCE_RE = re.compile(
    r"(见|参见|详见|参考|如|同|延续|承接)\s*"
    r"(?:第\s*(\d{1,4})\s*页|上文|前述|上述|同上|上一节|下表|上表|附件\s*([A-Za-z0-9一二三四五六七八九十]+))"
)


def read_markdown(path: Path | None) -> str:
    if not path or not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def read_content_list(path: Path | None) -> list[dict[str, Any]]:
    if not path or not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    if isinstance(data, list):
        return data
    return []


def extract_sections(markdown: str) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line_no, line in enumerate(markdown.splitlines(), start=1):
        match = HEADING_RE.match(line)
        if match:
            if current:
                current["text"] = "\n".join(current.pop("_lines")).strip()
                sections.append(current)
            current = {
                "level": len(match.group(1)),
                "title": match.group(2).strip(),
                "line": line_no,
                "source": "heading",
                "_lines": [],
            }
        elif current:
            current["_lines"].append(line)
    if current:
        current["text"] = "\n".join(current.pop("_lines")).strip()
        sections.append(current)
    if not sections and markdown.strip():
        sections.append({"level": 1, "title": "document", "text": markdown.strip(), "source": "fallback"})
    return sections


def extract_markdown_tables(markdown: str) -> list[dict[str, Any]]:
    tables: list[dict[str, Any]] = []
    current: list[str] = []
    start_line = 0
    for index, line in enumerate(markdown.splitlines(), start=1):
        if TABLE_ROW_RE.match(line):
            if not current:
                start_line = index
            current.append(line)
        else:
            if len(current) >= 2:
                tables.append(_parse_table(current, start_line))
            current = []
    if len(current) >= 2:
        tables.append(_parse_table(current, start_line))
    tables.extend(_extract_html_tables_from_markdown(markdown))
    return tables


def _parse_table(lines: list[str], start_line: int) -> dict[str, Any]:
    rows: list[list[str]] = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and all(set(cell) <= {"-", ":", " "} for cell in cells):
            continue
        rows.append(cells)
    normalized_rows, merged_cells = _normalize_table_rows(rows)
    headers = normalized_rows[0] if normalized_rows else []
    body = normalized_rows[1:] if len(normalized_rows) > 1 else []
    raw_body = rows[1:] if len(rows) > 1 else []
    max_width = max((len(row) for row in normalized_rows), default=0)
    header_levels = _infer_header_levels(normalized_rows)
    flattened_headers = _flatten_header_levels(header_levels)
    if flattened_headers:
        headers = flattened_headers
        body = normalized_rows[len(header_levels) :]
    return {
        "start_line": start_line,
        "headers": headers,
        "rows": body,
        "row_count": len(body),
        "column_count": max_width or len(headers),
        "raw_rows": raw_body,
        "header_levels": header_levels,
        "merged_cells": merged_cells,
    }


def _normalize_table_rows(rows: list[list[str]]) -> tuple[list[list[str]], list[dict[str, Any]]]:
    if not rows:
        return [], []
    width = max(len(row) for row in rows)
    padded = [row + [""] * (width - len(row)) for row in rows]
    normalized = [list(row) for row in padded]
    merged_cells: list[dict[str, Any]] = []
    for row_index in range(2, len(normalized)):
        for column_index, value in enumerate(normalized[row_index]):
            if value:
                continue
            inherited = normalized[row_index - 1][column_index]
            if not inherited:
                continue
            normalized[row_index][column_index] = inherited
            merged_cells.append(
                {
                    "row_index": row_index,
                    "column_index": column_index,
                    "value": inherited,
                    "inferred_from": "above",
                }
            )
    return normalized, merged_cells


def _infer_header_levels(rows: list[list[str]]) -> list[list[str]]:
    if not rows:
        return []
    header_levels = [rows[0]]
    if len(rows) < 3:
        return header_levels
    second = rows[1]
    data_after_second = rows[2:]
    if _looks_like_header_row(second, data_after_second):
        header_levels.append(second)
    return header_levels


def _looks_like_header_row(row: list[str], later_rows: list[list[str]]) -> bool:
    if not row or not later_rows:
        return False
    non_empty = [cell for cell in row if cell]
    if not non_empty:
        return False
    numeric_cells = sum(1 for cell in non_empty if NUMBER_RE.search(cell))
    if numeric_cells:
        return False
    later_numeric = sum(1 for later in later_rows for cell in later if NUMBER_RE.search(cell))
    return later_numeric >= max(1, len(later_rows))


def _flatten_header_levels(header_levels: list[list[str]]) -> list[str]:
    if len(header_levels) <= 1:
        return header_levels[0] if header_levels else []
    width = max(len(row) for row in header_levels)
    flattened: list[str] = []
    for column_index in range(width):
        parts: list[str] = []
        for row in header_levels:
            value = row[column_index] if column_index < len(row) else ""
            if value and value not in parts:
                parts.append(value)
        flattened.append(" / ".join(parts))
    return flattened


def _extract_html_tables_from_markdown(markdown: str) -> list[dict[str, Any]]:
    tables: list[dict[str, Any]] = []
    for match in re.finditer(r"<table\b.*?</table>", markdown, flags=re.IGNORECASE | re.DOTALL):
        parsed = _parse_html_table_snippet(match.group(0), markdown[: match.start()].count("\n") + 1)
        if parsed["headers"] or parsed["rows"]:
            tables.append(parsed)
    return tables


def _parse_html_table_snippet(html: str, start_line: int) -> dict[str, Any]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    rows: list[list[str]] = []
    merged_cells: list[dict[str, Any]] = []
    rowspans: dict[int, dict[str, Any]] = {}
    header_row_index: int | None = None
    for row_index, tr in enumerate(soup.find_all("tr")):
        cells = tr.find_all(["th", "td"])
        row: list[str] = []
        column_index = 0
        for cell in cells:
            while column_index in rowspans:
                span = rowspans[column_index]
                row.append(str(span["text"]))
                span["remaining"] = int(span["remaining"]) - 1
                merged_cells.append(
                    {
                        "row_index": row_index,
                        "column_index": column_index,
                        "value": span["text"],
                        "inferred_from": "rowspan",
                    }
                )
                if span["remaining"] <= 0:
                    del rowspans[column_index]
                column_index += 1
            text = _normalize_inline_text(cell.get_text(" ", strip=True))
            colspan = _safe_positive_int(cell.get("colspan"), default=1)
            rowspan = _safe_positive_int(cell.get("rowspan"), default=1)
            for offset in range(colspan):
                row.append(text)
                if offset:
                    merged_cells.append(
                        {
                            "row_index": row_index,
                            "column_index": column_index,
                            "value": text,
                            "inferred_from": "colspan",
                        }
                    )
                if rowspan > 1:
                    rowspans[column_index] = {"text": text, "remaining": rowspan - 1}
                column_index += 1
        while column_index in rowspans:
            span = rowspans[column_index]
            row.append(str(span["text"]))
            span["remaining"] = int(span["remaining"]) - 1
            merged_cells.append(
                {
                    "row_index": row_index,
                    "column_index": column_index,
                    "value": span["text"],
                    "inferred_from": "rowspan",
                }
            )
            if span["remaining"] <= 0:
                del rowspans[column_index]
            column_index += 1
        if not any(row):
            continue
        if header_row_index is None and tr.find("th"):
            header_row_index = len(rows)
        rows.append(row)
    if not rows:
        return {"start_line": start_line, "headers": [], "rows": [], "row_count": 0, "column_count": 0}
    width = max(len(row) for row in rows)
    padded_rows = [row + [""] * (width - len(row)) for row in rows]
    if header_row_index is None:
        header_row_index = 0
    headers = padded_rows[header_row_index]
    body = padded_rows[:header_row_index] + padded_rows[header_row_index + 1 :]
    return {
        "start_line": start_line,
        "headers": headers,
        "rows": body,
        "row_count": len(body),
        "column_count": len(headers),
        "source": "html_table",
        "raw_rows": rows,
        "header_levels": [headers],
        "merged_cells": merged_cells,
    }


def _safe_positive_int(value: Any, *, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def extract_key_value_candidates(markdown: str, tables: list[dict[str, Any]] | None = None) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    lines = markdown.splitlines()
    for index, line in enumerate(lines):
        clean = _normalize_key_value_line(line)
        if not clean or len(clean) > 220:
            continue
        split = _split_key_value(clean)
        if split is None:
            continue
        key, value = split
        if not value:
            value = _collect_multiline_value(lines, index)
        _append_key_value(candidates, seen, key, value)

    for table in tables or []:
        for key, value in _extract_table_key_values(table):
            _append_key_value(candidates, seen, key, value)

    for key, value in _extract_heading_following_paragraph_values(lines):
        _append_key_value(candidates, seen, key, value)
    return candidates[:250]


def _normalize_key_value_line(line: str) -> str:
    clean = KEY_VALUE_PREFIX_RE.sub("", line.strip())
    return clean.strip().strip("-*").strip()


def _split_key_value(clean: str) -> tuple[str, str] | None:
    for delimiter in KEY_VALUE_DELIMITERS:
        if delimiter not in clean:
            continue
        key, value = clean.split(delimiter, 1)
        key = _normalize_inline_text(key)
        value = _normalize_inline_text(value)
        if 1 <= len(key) <= 60 and _looks_like_key(key):
            return key, value
    return None


def _looks_like_key(key: str) -> bool:
    if NUMBER_RE.fullmatch(key):
        return False
    if key.startswith(("http://", "https://")):
        return False
    return bool(re.search(r"[\w\u4e00-\u9fff]", key))


def _collect_multiline_value(lines: list[str], index: int) -> str:
    parts: list[str] = []
    for next_line in lines[index + 1 : index + 4]:
        clean = _normalize_key_value_line(next_line)
        if not clean:
            if parts:
                break
            continue
        if clean.startswith("#") or TABLE_ROW_RE.match(clean) or _split_key_value(clean):
            break
        parts.append(clean)
    return _normalize_inline_text(" ".join(parts))


def _append_key_value(
    candidates: list[dict[str, str]],
    seen: set[tuple[str, str]],
    key: str,
    value: str,
) -> None:
    key = _normalize_inline_text(key)
    value = _normalize_inline_text(value)
    if not (1 <= len(key) <= 60 and value and len(value) <= 500):
        return
    marker = (key, value)
    if marker in seen:
        return
    seen.add(marker)
    candidates.append({"key": key, "value": value})


def _extract_table_key_values(table: dict[str, Any]) -> list[tuple[str, str]]:
    headers = [str(item).strip() for item in table.get("headers", []) if str(item).strip()]
    rows = table.get("rows", [])
    if not isinstance(rows, list):
        return []
    if not _table_looks_like_key_value(headers, table):
        return []
    pairs: list[tuple[str, str]] = []
    for row in rows:
        if not isinstance(row, list) or len(row) < 2:
            continue
        key = str(row[0]).strip()
        value = " | ".join(str(cell).strip() for cell in row[1:] if str(cell).strip())
        if key and value:
            pairs.append((key, value))
    return pairs


def _table_looks_like_key_value(headers: list[str], table: dict[str, Any]) -> bool:
    column_count = int(table.get("column_count") or len(headers) or 0)
    if column_count != 2:
        return False
    lowered = {header.lower() for header in headers}
    if lowered & TABLE_KEY_HEADERS or lowered & TABLE_VALUE_HEADERS:
        return True
    return len(headers) == 2 and not any(NUMBER_RE.search(header) for header in headers)


def _extract_heading_following_paragraph_values(lines: list[str]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for index, line in enumerate(lines[:-1]):
        heading = HEADING_RE.match(line.strip())
        if not heading:
            continue
        key = _normalize_inline_text(heading.group(2))
        if not (1 <= len(key) <= 60):
            continue
        for next_line in lines[index + 1 : index + 4]:
            value = _normalize_key_value_line(next_line)
            if not value:
                continue
            if value.startswith("#") or TABLE_ROW_RE.match(value) or _split_key_value(value):
                break
            if len(value) <= 180:
                pairs.append((key, value))
            break
    return pairs


def extract_key_value_map(candidates: list[dict[str, str]]) -> dict[str, str | list[str]]:
    mapped: dict[str, str | list[str]] = {}
    for item in candidates:
        key = item["key"]
        value = item["value"]
        if key not in mapped:
            mapped[key] = value
            continue
        existing = mapped[key]
        if isinstance(existing, list):
            if value not in existing:
                existing.append(value)
        elif existing != value:
            mapped[key] = [existing, value]
    return mapped


def extract_field_evidence(markdown: str, key_values: list[dict[str, str]], content_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    lines = markdown.splitlines()
    for index, item in enumerate(key_values):
        key = item["key"]
        value = item["value"]
        line_no = _find_markdown_line(lines, key, value)
        block = _find_content_block(content_list, key, value)
        provenance = _field_provenance(line_no=line_no, block=block)
        confidence, reason = _field_confidence(line_no=line_no, block=block, value=value)
        evidence.append(
            {
                "key": key,
                "value": value,
                "confidence": confidence,
                "confidence_reason": reason,
                "evidence_text": _field_evidence_text(lines, line_no, block, key, value),
                "provenance": provenance,
                "candidate_index": index,
            }
        )
    return evidence


def build_field_evidence_map(field_evidence: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    mapped: dict[str, list[dict[str, Any]]] = {}
    for item in field_evidence:
        key = str(item.get("key", ""))
        if not key:
            continue
        mapped.setdefault(key, []).append(
            {
                "value": item.get("value"),
                "confidence": item.get("confidence"),
                "provenance": item.get("provenance"),
                "evidence_text": item.get("evidence_text"),
            }
        )
    return mapped


def extract_numeric_facts(markdown: str) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    for line_no, line in enumerate(markdown.splitlines(), start=1):
        clean = _normalize_inline_text(re.sub(r"<[^>]+>", " ", line))
        numbers = NUMBER_RE.findall(clean)
        if numbers:
            facts.append({"line": line_no, "text": clean[:300], "numbers": numbers})
    return facts[:500]


def extract_semantic_signals(markdown: str, key_values: list[dict[str, str]]) -> dict[str, Any]:
    dates = _unique_keep_order(DATE_RE.findall(markdown))
    recommendations: list[dict[str, str]] = []
    anomaly_lines: list[dict[str, Any]] = []

    for item in key_values:
        key = item["key"].lower()
        if any(token in key for token in RECOMMENDATION_KEYS):
            recommendations.append({"source": "key_value", "text": f"{item['key']}: {item['value']}"})

    for line_no, line in enumerate(markdown.splitlines(), start=1):
        clean = line.strip()
        if not clean:
            continue
        lowered = clean.lower()
        if any(token in lowered for token in ANOMALY_WORDS):
            anomaly_lines.append({"line": line_no, "text": clean[:300]})
        if any(token in lowered for token in RECOMMENDATION_KEYS) and not any(
            entry["text"] == clean for entry in recommendations
        ):
            recommendations.append({"source": "line", "text": clean[:300]})

    return {
        "dates": dates[:50],
        "recommendations": recommendations[:50],
        "anomaly_lines": anomaly_lines[:50],
        "field_coverage": {
            "has_date": bool(dates),
            "has_recommendation": bool(recommendations),
            "has_anomaly_signal": bool(anomaly_lines),
        },
    }


def extract_cross_page_references(
    sections: list[dict[str, Any]],
    content_list: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    references: list[dict[str, Any]] = []
    for section in sections:
        text = _normalize_inline_text(str(section.get("text", "")))
        if not text:
            continue
        source_page = _infer_section_page(section, content_list)
        for match in CROSS_PAGE_REFERENCE_RE.finditer(text):
            target_page = int(match.group(2)) if match.group(2) else None
            references.append(
                {
                    "source_title": section.get("title"),
                    "source_line": section.get("line"),
                    "source_page": source_page,
                    "reference_text": match.group(0),
                    "target_page": target_page,
                    "target_hint": match.group(3) or _reference_hint(match.group(0)),
                    "relation": _reference_relation(match.group(0)),
                    "confidence": 0.78 if target_page else 0.56,
                }
            )
    return references[:100]


def _infer_section_page(section: dict[str, Any], content_list: list[dict[str, Any]]) -> int | None:
    title = _normalize_inline_text(str(section.get("title", "")))
    body = _normalize_inline_text(str(section.get("text", "")))
    snippets = [text for text in (title, body[:80]) if text and text != "document"]
    for block in content_list:
        page_idx = block.get("page_idx")
        if page_idx is None:
            continue
        block_text = _normalize_inline_text(str(block.get("text", "")))
        if any(snippet and snippet in block_text for snippet in snippets):
            return int(page_idx) + 1
    return None


def _reference_hint(text: str) -> str | None:
    for token in ("上文", "前述", "上述", "同上", "上一节", "下表", "上表"):
        if token in text:
            return token
    return None


def _reference_relation(text: str) -> str:
    if "下表" in text or "上表" in text:
        return "table_reference"
    if "附件" in text:
        return "attachment_reference"
    if "第" in text and "页" in text:
        return "page_reference"
    return "context_reference"


def summarize_content_blocks(content_list: list[dict[str, Any]]) -> dict[str, Any]:
    pages = sorted({item.get("page_idx") for item in content_list if item.get("page_idx") is not None})
    type_counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    chars = 0
    for item in content_list:
        item_type = str(item.get("type", "unknown"))
        type_counts[item_type] = type_counts.get(item_type, 0) + 1
        source = str(item.get("source", "native"))
        source_counts[source] = source_counts.get(source, 0) + 1
        chars += len(str(item.get("text", "")))
    return {
        "item_count": len(content_list),
        "page_indices": pages,
        "page_count": len(pages),
        "provenance_level": "page" if pages else ("document" if content_list else "none"),
        "type_counts": type_counts,
        "source_counts": source_counts,
        "text_characters": chars,
    }


class _TextHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.links: list[dict[str, str]] = []
        self._href: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"p", "div", "section", "article", "br", "tr", "h1", "h2", "h3"}:
            self.parts.append("\n")
        if tag == "a":
            self._href = dict(attrs).get("href")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"p", "div", "section", "article", "tr", "h1", "h2", "h3"}:
            self.parts.append("\n")
        if tag == "a":
            self._href = None

    def handle_data(self, data: str) -> None:
        text = unescape(data).strip()
        if not text:
            return
        self.parts.append(text + " ")
        if self._href:
            self.links.append({"text": text, "href": self._href})


def extract_html(path: Path) -> tuple[str, list[dict[str, Any]]]:
    html = path.read_text(encoding="utf-8", errors="replace")
    try:
        return _extract_html_with_structure(html)
    except ImportError:
        pass

    parser = _TextHTMLParser()
    parser.feed(html)
    text = re.sub(r"\n{3,}", "\n\n", "".join(parser.parts)).strip()
    content = [
        {
            "type": "text",
            "text": paragraph.strip(),
            "source": "html",
        }
        for paragraph in re.split(r"\n{2,}", text)
        if paragraph.strip()
    ]
    return text, content


def extract_docx(path: Path) -> tuple[str, list[dict[str, Any]]]:
    with zipfile.ZipFile(path) as archive:
        document_xml = archive.read("word/document.xml")
    root = ET.fromstring(document_xml)
    lines: list[str] = []
    content: list[dict[str, Any]] = []
    block_index = 0
    body = root.find(f"{W_NS}body")
    if body is None:
        return "", []
    for child in body:
        if child.tag == f"{W_NS}p":
            text = _docx_paragraph_text(child)
            if not text:
                continue
            style = _docx_paragraph_style(child)
            level = _docx_heading_level(style)
            if level:
                line = f"{'#' * level} {text}"
                lines.append(line)
                content.append(
                    {
                        "type": "heading",
                        "text": line,
                        "title": text,
                        "level": level,
                        "source": "docx",
                        "block_idx": block_index,
                    }
                )
            else:
                lines.append(text)
                content.append({"type": "text", "text": text, "source": "docx", "block_idx": block_index})
            block_index += 1
        elif child.tag == f"{W_NS}tbl":
            rows = _docx_table_rows(child)
            table_markdown, table_meta = _rows_to_markdown(rows)
            if table_markdown:
                lines.append(table_markdown)
                block = {"type": "table", "text": table_markdown, "source": "docx", "block_idx": block_index}
                block.update(table_meta)
                content.append(block)
                block_index += 1
    return "\n\n".join(lines).strip(), content


def extract_pptx(path: Path) -> tuple[str, list[dict[str, Any]]]:
    lines: list[str] = []
    content: list[dict[str, Any]] = []
    with zipfile.ZipFile(path) as archive:
        slide_names = sorted(
            (name for name in archive.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)),
            key=lambda item: int(re.search(r"slide(\d+)\.xml", item).group(1)),  # type: ignore[union-attr]
        )
        for slide_index, slide_name in enumerate(slide_names):
            root = ET.fromstring(archive.read(slide_name))
            slide_no = slide_index + 1
            title = f"Slide {slide_no}"
            lines.append(f"# {title}")
            content.append(
                {
                    "type": "heading",
                    "text": f"# {title}",
                    "title": title,
                    "level": 1,
                    "source": "pptx",
                    "page_idx": slide_index,
                    "block_idx": len(content),
                }
            )
            tables = list(root.iter(f"{A_NS}tbl"))
            table_text_fragments = {_normalize_inline_text(text) for table in tables for text in _all_xml_text(table)}
            text_items = [
                item
                for item in _pptx_text_runs(root)
                if item and _normalize_inline_text(item) not in table_text_fragments
            ]
            if text_items:
                text = "\n".join(text_items)
                lines.append(text)
                content.append(
                    {
                        "type": "text",
                        "text": text,
                        "source": "pptx",
                        "page_idx": slide_index,
                        "block_idx": len(content),
                    }
                )
            for table in tables:
                rows = _pptx_table_rows(table)
                table_markdown, table_meta = _rows_to_markdown(rows)
                if table_markdown:
                    lines.append(table_markdown)
                    block = {
                        "type": "table",
                        "text": table_markdown,
                        "source": "pptx",
                        "page_idx": slide_index,
                        "block_idx": len(content),
                    }
                    block.update(table_meta)
                    content.append(block)
    return "\n\n".join(lines).strip(), content


W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A_NS = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


def _docx_paragraph_text(paragraph: ET.Element) -> str:
    return _normalize_inline_text("".join(node.text or "" for node in paragraph.iter(f"{W_NS}t")))


def _docx_paragraph_style(paragraph: ET.Element) -> str:
    style = paragraph.find(f"{W_NS}pPr/{W_NS}pStyle")
    if style is None:
        return ""
    return str(style.attrib.get(f"{W_NS}val", "") or style.attrib.get("val", ""))


def _docx_heading_level(style: str) -> int | None:
    normalized = style.lower().replace(" ", "")
    if normalized == "title":
        return 1
    match = re.search(r"heading(\d+)", normalized)
    if match:
        return max(1, min(6, int(match.group(1))))
    return None


def _docx_table_rows(table: ET.Element) -> list[list[str]]:
    rows: list[list[str]] = []
    for tr in table.findall(f"{W_NS}tr"):
        row = [_normalize_inline_text(" ".join(_all_xml_text(cell))) for cell in tr.findall(f"{W_NS}tc")]
        if any(row):
            rows.append(row)
    return rows


def _pptx_text_runs(root: ET.Element) -> list[str]:
    runs: list[str] = []
    for paragraph in root.iter(f"{A_NS}p"):
        text = _normalize_inline_text("".join(node.text or "" for node in paragraph.iter(f"{A_NS}t")))
        if text:
            runs.append(text)
    return runs


def _pptx_table_rows(table: ET.Element) -> list[list[str]]:
    rows: list[list[str]] = []
    for tr in table.findall(f"{A_NS}tr"):
        row = [_normalize_inline_text(" ".join(_all_xml_text(cell))) for cell in tr.findall(f"{A_NS}tc")]
        if any(row):
            rows.append(row)
    return rows


def _all_xml_text(element: ET.Element) -> list[str]:
    return [node.text or "" for node in element.iter() if node.text]


def _extract_html_with_structure(html: str) -> tuple[str, list[dict[str, Any]]]:
    from bs4 import BeautifulSoup
    from bs4.element import NavigableString, Tag

    soup = BeautifulSoup(html, "html.parser")
    for noisy in soup(["script", "style", "noscript"]):
        noisy.decompose()

    lines: list[str] = []
    content: list[dict[str, Any]] = []

    def push(line: str, block_type: str = "text", extra: dict[str, Any] | None = None) -> None:
        if block_type == "table":
            clean = "\n".join(
                normalized
                for raw_line in line.splitlines()
                if (normalized := _normalize_inline_text(raw_line))
            )
        else:
            clean = _normalize_inline_text(line)
        if not clean:
            return
        if lines and lines[-1] == clean:
            return
        lines.append(clean)
        block: dict[str, Any] = {"type": block_type, "text": clean, "source": "html"}
        if extra:
            block.update(extra)
        content.append(block)

    def walk(node: Any) -> None:
        if isinstance(node, NavigableString):
            return
        if not isinstance(node, Tag):
            return
        name = (node.name or "").lower()
        if name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            level = int(name[1])
            title = node.get_text(" ", strip=True)
            push(f"{'#' * level} {title}", "heading", {"level": level, "title": title})
            return
        if name == "table":
            table_markdown, table_meta = _html_table_to_markdown(node)
            if table_markdown:
                push(table_markdown, "table", table_meta)
            return
        if name in {"p", "blockquote", "figcaption"}:
            push(node.get_text(" ", strip=True))
            return
        if name == "li":
            push(f"- {node.get_text(' ', strip=True)}", "list_item")
            return
        if name in {"br", "hr"}:
            return
        for child in node.children:
            walk(child)

    root = soup.body or soup
    for child in root.children:
        walk(child)

    markdown = "\n\n".join(lines).strip()
    return markdown, content


def _html_table_to_markdown(table: Any) -> tuple[str, dict[str, Any]]:
    rows: list[list[str]] = []
    header_row_index: int | None = None
    for tr in table.find_all("tr"):
        cells = tr.find_all(["th", "td"], recursive=False) or tr.find_all(["th", "td"])
        row = [_normalize_inline_text(cell.get_text(" ", strip=True)) for cell in cells]
        if not any(row):
            continue
        if header_row_index is None and tr.find("th"):
            header_row_index = len(rows)
        rows.append(row)
    if not rows:
        return "", {"headers": [], "rows": [], "row_count": 0, "column_count": 0}

    width = max(len(row) for row in rows)
    padded_rows = [row + [""] * (width - len(row)) for row in rows]
    if header_row_index is None:
        header_row_index = 0
    headers = padded_rows[header_row_index]
    body = padded_rows[:header_row_index] + padded_rows[header_row_index + 1 :]
    return _rows_to_markdown([headers, *body])


def _rows_to_markdown(rows: list[list[str]]) -> tuple[str, dict[str, Any]]:
    if not rows:
        return "", {"headers": [], "rows": [], "row_count": 0, "column_count": 0}
    width = max(len(row) for row in rows)
    padded_rows = [row + [""] * (width - len(row)) for row in rows]
    headers = padded_rows[0]
    body = padded_rows[1:]
    markdown_rows = [
        "| " + " | ".join(_escape_markdown_cell(cell) for cell in headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    markdown_rows.extend("| " + " | ".join(_escape_markdown_cell(cell) for cell in row) + " |" for row in body)
    return (
        "\n".join(markdown_rows),
        {
            "headers": headers,
            "rows": body,
            "row_count": len(body),
            "column_count": len(headers),
        },
    )


def _normalize_inline_text(text: str) -> str:
    return re.sub(r"\s+", " ", unescape(text)).strip()


def _escape_markdown_cell(text: str) -> str:
    return text.replace("|", "\\|").strip()


def _unique_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def _find_markdown_line(lines: list[str], key: str, value: str) -> int | None:
    for line_no, line in enumerate(lines, start=1):
        if key in line and value in line:
            return line_no
    return None


def _find_content_block(content_list: list[dict[str, Any]], key: str, value: str) -> dict[str, Any] | None:
    for item in content_list:
        text = str(item.get("text", ""))
        if key in text and value in text:
            return item
    for item in content_list:
        text = str(item.get("text", ""))
        if key in text or value in text:
            return item
    return None


def _field_provenance(line_no: int | None, block: dict[str, Any] | None) -> dict[str, Any]:
    provenance: dict[str, Any] = {"line": line_no, "level": "markdown_line" if line_no else "unknown"}
    if block:
        source = block.get("source")
        if source is not None:
            provenance["source"] = source
        block_idx = block.get("block_idx")
        if block_idx is not None:
            provenance["block_idx"] = block_idx
        page_idx = block.get("page_idx")
        if page_idx is not None:
            provenance["page_idx"] = page_idx
            provenance["page_no"] = int(page_idx) + 1 if isinstance(page_idx, int) else page_idx
            provenance["level"] = "page"
        elif source:
            provenance["level"] = "document"
        bbox = block.get("bbox") or block.get("box") or block.get("poly")
        if bbox is not None:
            provenance["bbox"] = bbox
    return provenance


def _field_confidence(line_no: int | None, block: dict[str, Any] | None, value: str) -> tuple[float, str]:
    if block and block.get("page_idx") is not None:
        return 0.95, "exact key/value match in page-level content block"
    if block:
        return 0.86, "exact key/value match in document-level content block"
    if line_no is not None and len(value) >= 2:
        return 0.72, "key/value found in markdown line without block provenance"
    return 0.45, "low evidence density; downstream review recommended"


def _field_evidence_text(
    lines: list[str], line_no: int | None, block: dict[str, Any] | None, key: str, value: str
) -> str:
    if block:
        text = _normalize_inline_text(str(block.get("text", "")))
        if text:
            return text[:300]
    if line_no is not None and 1 <= line_no <= len(lines):
        return _normalize_inline_text(lines[line_no - 1])[:300]
    return f"{key}: {value}"[:300]


def build_extracted_view(markdown: str, content_list: list[dict[str, Any]]) -> dict[str, Any]:
    tables = extract_markdown_tables(markdown)
    key_values = extract_key_value_candidates(markdown, tables)
    sections = extract_sections(markdown)
    field_evidence = extract_field_evidence(markdown, key_values, content_list)
    return {
        "content_summary": summarize_content_blocks(content_list),
        "sections": sections,
        "tables": tables,
        "key_values": key_values,
        "key_value_map": extract_key_value_map(key_values),
        "field_evidence": field_evidence,
        "field_evidence_map": build_field_evidence_map(field_evidence),
        "numeric_facts": extract_numeric_facts(markdown),
        "semantic_signals": extract_semantic_signals(markdown, key_values),
        "cross_page_references": extract_cross_page_references(sections, content_list),
        "structure_quality": {
            "heading_section_count": sum(1 for item in sections if item.get("source") == "heading"),
            "fallback_section_count": sum(1 for item in sections if item.get("source") == "fallback"),
        },
        "markdown_preview": markdown[:2000],
    }
