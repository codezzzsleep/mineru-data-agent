from __future__ import annotations

import math
import re
from typing import Any

from .models import QualityIssue


MOJIBAKE_RE = re.compile(r"(?:�|����|锟斤拷|Ã.|Â.)")


def build_quality_report(markdown: str, extracted: dict[str, Any], profile: str, task: str = "") -> dict[str, Any]:
    issues: list[QualityIssue] = []
    issues.extend(_check_text_integrity(markdown, extracted, profile))
    issues.extend(_check_page_coverage(extracted))
    issues.extend(_check_profile_expectations(extracted, profile))
    issues.extend(_check_task_expected_fields(extracted, task))
    issues.extend(_check_structure_strength(markdown, extracted))
    issues.extend(_check_numeric_tables(extracted))

    blocking = sum(1 for issue in issues if issue.level == "error")
    warnings = sum(1 for issue in issues if issue.level == "warning")
    info = sum(1 for issue in issues if issue.level == "info")
    score = max(0, 100 - blocking * 30 - warnings * 8)
    if blocking:
        status = "needs_review"
    elif warnings:
        status = "pass_with_warnings"
    else:
        status = "pass"
    return {
        "score": score,
        "status": status,
        "issue_count": len(issues),
        "issue_counts": {"error": blocking, "warning": warnings, "info": info},
        "issues": [issue.__dict__ for issue in issues],
    }


def _check_text_integrity(markdown: str, extracted: dict[str, Any], profile: str) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    if not markdown.strip():
        issues.append(QualityIssue("empty_markdown", "error", "No markdown text was extracted."))
        return issues
    matches = MOJIBAKE_RE.findall(markdown)
    if matches:
        ratio = len(matches) / max(1, len(markdown))
        level = "error" if ratio > 0.02 else "warning"
        issues.append(
            QualityIssue(
                "possible_mojibake",
                level,
                "Extracted text contains encoding-noise patterns.",
                {"pattern_count": len(matches), "ratio": round(ratio, 4)},
            )
        )
    if len(markdown) < 200 and _should_warn_short_text(markdown, extracted, profile):
        issues.append(
            QualityIssue(
                "short_text",
                "warning",
                "Extracted text is very short; the input may need OCR/VLM fallback.",
                {"characters": len(markdown)},
            )
        )
    return issues


def _should_warn_short_text(markdown: str, extracted: dict[str, Any], profile: str) -> bool:
    summary = extracted.get("content_summary", {}) if isinstance(extracted, dict) else {}
    provenance_level = str(summary.get("provenance_level") or "none")
    source_counts = summary.get("source_counts", {})
    native_document_sources = {"html", "docx", "pptx"}
    is_native_document = (
        provenance_level == "document"
        and isinstance(source_counts, dict)
        and any(int(source_counts.get(source) or 0) > 0 for source in native_document_sources)
    )
    if is_native_document and profile == "general_document" and markdown.strip():
        return False
    if is_native_document and len(markdown.strip()) >= 80:
        return False
    return True


def _check_page_coverage(extracted: dict[str, Any]) -> list[QualityIssue]:
    summary = extracted.get("content_summary", {})
    page_count = int(summary.get("page_count") or 0)
    item_count = int(summary.get("item_count") or 0)
    provenance_level = str(summary.get("provenance_level") or "none")
    source_counts = summary.get("source_counts", {})
    if item_count == 0:
        return [QualityIssue("no_content_blocks", "warning", "No content blocks were found.")]
    if page_count == 0:
        if provenance_level == "document" and isinstance(source_counts, dict) and any(
            source_counts.get(source) for source in ("html", "docx")
        ):
            return [
                QualityIssue(
                    "document_level_provenance",
                    "info",
                    "Native document input has document-level provenance rather than page-level provenance.",
                    {"page_count": page_count, "item_count": item_count, "source_counts": source_counts},
                )
            ]
        return [
            QualityIssue(
                "no_page_provenance",
                "warning",
                "Content blocks were extracted, but no page-level provenance is available.",
                {"page_count": page_count, "item_count": item_count},
            )
        ]
    if page_count <= 1 and item_count > 30:
        return [
            QualityIssue(
                "weak_page_provenance",
                "warning",
                "Most extracted blocks lack page-level provenance.",
                {"page_count": page_count, "item_count": item_count},
            )
        ]
    return []


def _check_profile_expectations(extracted: dict[str, Any], profile: str) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    tables = extracted.get("tables", [])
    numeric_facts = extracted.get("numeric_facts", [])
    sections = extracted.get("sections", [])
    if profile == "financial_report" and not (tables or len(numeric_facts) >= 10):
        issues.append(
            QualityIssue(
                "financial_signal_missing",
                "warning",
                "Financial profile was selected, but few tables or numeric facts were found.",
            )
        )
    if profile == "standard_or_contract" and len(sections) < 2:
        issues.append(
            QualityIssue(
                "weak_clause_structure",
                "warning",
                "Standard/contract profile expects clearer section hierarchy.",
            )
        )
    return issues


def _check_task_expected_fields(extracted: dict[str, Any], task: str) -> list[QualityIssue]:
    if not task:
        return []
    text = task.lower()
    signals = extracted.get("semantic_signals", {})
    coverage = signals.get("field_coverage", {})
    issues: list[QualityIssue] = []
    if any(token in text for token in ["日期", "时间", "date"]) and not coverage.get("has_date"):
        issues.append(
            QualityIssue(
                "expected_date_missing",
                "warning",
                "Task asks for a date/time field, but no date-like value was extracted.",
            )
        )
    if any(token in text for token in ["建议", "整改", "措施", "action", "recommend"]) and not coverage.get(
        "has_recommendation"
    ):
        issues.append(
            QualityIssue(
                "expected_recommendation_missing",
                "warning",
                "Task asks for recommendations/actions, but no recommendation-like text was extracted.",
            )
        )
    if any(token in text for token in ["异常", "风险", "问题", "告警", "risk", "issue"]) and not coverage.get(
        "has_anomaly_signal"
    ):
        issues.append(
            QualityIssue(
                "expected_anomaly_signal_missing",
                "warning",
                "Task asks for anomalies/risks, but no anomaly-like evidence was extracted.",
            )
        )
    return issues


def _check_structure_strength(markdown: str, extracted: dict[str, Any]) -> list[QualityIssue]:
    structure = extracted.get("structure_quality", {})
    heading_count = int(structure.get("heading_section_count") or 0)
    key_value_count = len(extracted.get("key_values", []))
    table_count = len(extracted.get("tables", []))
    if len(markdown) >= 500 and heading_count == 0 and key_value_count == 0 and table_count == 0:
        return [
            QualityIssue(
                "weak_structured_signal",
                "warning",
                "Text was extracted, but no headings, key-value fields, or tables were detected.",
            )
        ]
    return []


def _check_numeric_tables(extracted: dict[str, Any]) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    for table_index, table in enumerate(extracted.get("tables", [])):
        rows = table.get("rows", [])
        if not rows:
            continue
        for item in _check_total_rows(rows):
            code = item.pop("code")
            level = item.pop("level")
            message = item.pop("message")
            issues.append(QualityIssue(code, level, message, {"table_index": table_index, **item}))
    return issues[:20]


TOTAL_ROW_TOKENS = ("合计", "总计", "小计", "total", "subtotal")


def _check_total_rows(rows: list[list[str]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for row_index, row in enumerate(rows):
        if not _is_total_row(row):
            continue
        comparison = _compare_total_row(rows, row_index, row)
        if comparison["mismatches"]:
            results.append(
                {
                    "code": "numeric_total_mismatch",
                    "level": "warning",
                    "message": "A total/subtotal row does not match the sum of comparable numeric rows.",
                    "row_index": row_index,
                    "row_preview": row[:8],
                    **comparison,
                }
            )
        elif comparison["verified"]:
            results.append(
                {
                    "code": "numeric_total_verified",
                    "level": "info",
                    "message": "A total/subtotal row matched the sum of comparable numeric rows.",
                    "row_index": row_index,
                    "row_preview": row[:8],
                    **comparison,
                }
            )
        else:
            numeric_values = [_to_number(cell) for cell in row]
            numeric_values = [value for value in numeric_values if value is not None]
            if numeric_values:
                results.append(
                    {
                        "code": "numeric_total_needs_review",
                        "level": "warning",
                        "message": "A total/subtotal row was found, but there were not enough comparable numeric rows.",
                        "row_index": row_index,
                        "row_preview": row[:8],
                        "numeric_values": numeric_values[:8],
                        **comparison,
                    }
                )
    return results


def _is_total_row(row: list[str]) -> bool:
    joined = " ".join(row).lower()
    return any(token in joined for token in TOTAL_ROW_TOKENS)


def _compare_total_row(rows: list[list[str]], row_index: int, row: list[str]) -> dict[str, Any]:
    verified: list[dict[str, Any]] = []
    mismatches: list[dict[str, Any]] = []
    previous_rows = [item for item in rows[:row_index] if not _is_total_row(item)]
    for column_index, cell in enumerate(row):
        expected = _to_number(cell)
        if expected is None:
            continue
        values = []
        for previous in previous_rows:
            if column_index >= len(previous):
                continue
            value = _to_number(previous[column_index])
            if value is not None:
                values.append(value)
        if len(values) < 2:
            continue
        actual = sum(values)
        delta = actual - expected
        tolerance = _numeric_total_tolerance(expected)
        record = {
            "column_index": column_index,
            "expected_total": expected,
            "computed_total": round(actual, 4),
            "delta": round(delta, 4),
            "source_value_count": len(values),
        }
        if abs(delta) <= tolerance:
            verified.append(record)
        else:
            mismatches.append(record)
    return {"verified": verified, "mismatches": mismatches}


def _numeric_total_tolerance(expected: float) -> float:
    return max(0.01, min(1.0, abs(expected) * 0.000001))


def _to_number(text: str) -> float | None:
    if "%" in text:
        return None
    cleaned = text.replace(",", "").strip()
    negative = cleaned.startswith("(") and cleaned.endswith(")")
    if negative:
        cleaned = cleaned[1:-1].strip()
    cleaned = re.sub(r"^[￥¥$]", "", cleaned)
    cleaned = re.sub(r"(?:人民币|元|万元|亿元|万|亿)$", "", cleaned).strip()
    if not re.fullmatch(r"[-+]?\d+(?:\.\d+)?", cleaned):
        return None
    value = float(cleaned)
    if negative:
        value = -value
    if math.isfinite(value):
        return value
    return None
