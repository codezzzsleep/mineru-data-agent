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
    headers = rows[0] if rows else []
    body = rows[1:] if len(rows) > 1 else []
    return {
        "start_line": start_line,
        "headers": headers,
        "rows": body,
        "row_count": len(body),
        "column_count": len(headers),
    }


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
    header_row_index: int | None = None
    for tr in soup.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        row = [_normalize_inline_text(cell.get_text(" ", strip=True)) for cell in cells]
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
    }


def extract_key_value_candidates(markdown: str) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    for line in markdown.splitlines():
        clean = line.strip().strip("-*")
        if not clean or len(clean) > 220:
            continue
        if "：" in clean:
            key, value = clean.split("：", 1)
        elif ":" in clean:
            key, value = clean.split(":", 1)
        else:
            continue
        key = key.strip()
        value = value.strip()
        if 1 <= len(key) <= 40 and value:
            candidates.append({"key": key, "value": value})
    return candidates[:200]


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


def build_extracted_view(markdown: str, content_list: list[dict[str, Any]]) -> dict[str, Any]:
    key_values = extract_key_value_candidates(markdown)
    sections = extract_sections(markdown)
    return {
        "content_summary": summarize_content_blocks(content_list),
        "sections": sections,
        "tables": extract_markdown_tables(markdown),
        "key_values": key_values,
        "key_value_map": extract_key_value_map(key_values),
        "numeric_facts": extract_numeric_facts(markdown),
        "semantic_signals": extract_semantic_signals(markdown, key_values),
        "structure_quality": {
            "heading_section_count": sum(1 for item in sections if item.get("source") == "heading"),
            "fallback_section_count": sum(1 for item in sections if item.get("source") == "fallback"),
        },
        "markdown_preview": markdown[:2000],
    }
