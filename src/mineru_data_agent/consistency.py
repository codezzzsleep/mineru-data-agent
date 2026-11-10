from __future__ import annotations

import re
from collections import Counter
from typing import Any


def build_fine_grained_escalation_plan(
    *,
    extracted: dict[str, Any],
    quality: dict[str, Any],
    input_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    summary = extracted.get("content_summary", {}) if isinstance(extracted, dict) else {}
    pages = _pages_from_extracted(extracted)
    issue_codes = [str(item.get("code", "")) for item in quality.get("issues", []) if isinstance(item, dict)]
    has_tables = bool(extracted.get("tables"))
    page_count = int((input_metadata or {}).get("page_count") or summary.get("page_count") or len(pages) or 0)
    text_layer = (input_metadata or {}).get("has_text_layer")
    actions: list[dict[str, Any]] = []

    if "short_text" in issue_codes or "empty_markdown" in issue_codes or text_layer is False:
        target_pages = _bounded_pages(pages, page_count, max_pages=20)
        actions.append(
            {
                "action": "ocr_pipeline_retry",
                "reason": "text is missing/short or PDF has no extractable text layer",
                "parser": "precise-api",
                "backend": "pipeline",
                "method": "ocr",
                "pages": target_pages,
            }
        )
    if has_tables or "weak_structured_signal" in issue_codes or "numeric_total_mismatch" in issue_codes:
        target_pages = _bounded_pages(_table_pages(extracted) or pages, page_count, max_pages=5)
        actions.append(
            {
                "action": "vlm_region_or_page_retry",
                "reason": "tables/layout/numeric anomalies need high-fidelity visual review",
                "parser": "precise-api",
                "backend": "vlm-transformers",
                "method": "auto",
                "pages": target_pages,
            }
        )
    if "no_page_provenance" in issue_codes or "weak_page_provenance" in issue_codes:
        actions.append(
            {
                "action": "page_provenance_retry",
                "reason": "page-level provenance is weak or absent",
                "parser": "precise-api",
                "backend": "pipeline",
                "method": "auto",
                "pages": _bounded_pages(pages, page_count, max_pages=20),
            }
        )

    return {
        "mode": "page_level_escalation_plan",
        "page_count": page_count,
        "source_pages": pages,
        "actions": actions,
        "status": "needs_escalation" if actions else "no_escalation_needed",
        "policy": (
            "Use low-cost text/OCR paths first. Escalate only suspect pages or regions to VLM; "
            "do not run whole-document VLM unless the page-level plan still fails."
        ),
    }


def compare_parser_outputs(outputs: list[dict[str, Any]], *, mismatch_threshold: float = 0.45) -> dict[str, Any]:
    normalized = [
        {
            "name": str(item.get("name") or item.get("parser") or f"parser_{idx}"),
            "role": str(item.get("role") or item.get("parser") or "").lower(),
            "text": str(item.get("text") or ""),
        }
        for idx, item in enumerate(outputs)
        if str(item.get("text") or "").strip()
    ]
    pairs: list[dict[str, Any]] = []
    hallucination_risks: list[dict[str, Any]] = []
    for index, left in enumerate(normalized):
        for right in normalized[index + 1 :]:
            similarity = _token_similarity(left["text"], right["text"])
            mismatch = round(1.0 - similarity, 4)
            pair = {
                "left": left["name"],
                "right": right["name"],
                "similarity": round(similarity, 4),
                "mismatch": mismatch,
                "status": "mismatch" if mismatch >= mismatch_threshold else "match",
            }
            pairs.append(pair)
            if pair["status"] == "mismatch":
                vlm_side = _vlm_side(left, right)
                if vlm_side:
                    hallucination_risks.append(
                        {
                            "parser": vlm_side["name"],
                            "compared_with": right["name"] if vlm_side is left else left["name"],
                            "reason": "VLM output diverges from text/OCR parser output; mark as hallucination risk until verified.",
                            "mismatch": mismatch,
                        }
                    )
    return {
        "mode": "multi_parser_consistency",
        "parser_count": len(normalized),
        "pairs": pairs,
        "status": "needs_review" if hallucination_risks else "pass" if pairs else "insufficient_inputs",
        "hallucination_risks": hallucination_risks,
        "policy": "When VLM disagrees with text-layer or OCR output, do not trust VLM by default; require OCR/text evidence.",
    }


def compare_current_parse_with_candidate(
    *,
    current_markdown: str,
    candidate_markdown: str,
    current_parser: str,
    candidate_parser: str,
) -> dict[str, Any]:
    return compare_parser_outputs(
        [
            {"name": current_parser, "role": current_parser, "text": current_markdown},
            {"name": candidate_parser, "role": candidate_parser, "text": candidate_markdown},
        ]
    )


def _pages_from_extracted(extracted: dict[str, Any]) -> list[int]:
    summary = extracted.get("content_summary", {}) if isinstance(extracted, dict) else {}
    pages = summary.get("page_indices")
    if isinstance(pages, list):
        clean = []
        for page in pages:
            try:
                clean.append(int(page) + 1)
            except (TypeError, ValueError):
                continue
        if clean:
            return sorted(set(clean))
    return []


def _table_pages(extracted: dict[str, Any]) -> list[int]:
    pages: list[int] = []
    for table in extracted.get("tables", []) if isinstance(extracted, dict) else []:
        if not isinstance(table, dict):
            continue
        page = table.get("page_no") or table.get("page")
        if page is None:
            continue
        try:
            pages.append(int(page))
        except (TypeError, ValueError):
            continue
    return sorted(set(pages))


def _bounded_pages(pages: list[int], page_count: int, *, max_pages: int) -> list[int]:
    if pages:
        return sorted(set(page for page in pages if page > 0))[:max_pages]
    if page_count <= 0:
        return []
    return list(range(1, min(page_count, max_pages) + 1))


def _token_similarity(left: str, right: str) -> float:
    left_tokens = Counter(_tokens(left))
    right_tokens = Counter(_tokens(right))
    if not left_tokens or not right_tokens:
        return 0.0
    overlap = sum((left_tokens & right_tokens).values())
    total = sum((left_tokens | right_tokens).values())
    return overlap / max(total, 1)


def _tokens(text: str) -> list[str]:
    return [token.lower() for token in re.findall(r"[\w\u4e00-\u9fff]+", text) if token.strip()]


def _vlm_side(left: dict[str, str], right: dict[str, str]) -> dict[str, str] | None:
    left_is_vlm = "vlm" in left["role"].lower() or "vlm" in left["name"].lower()
    right_is_vlm = "vlm" in right["role"].lower() or "vlm" in right["name"].lower()
    if left_is_vlm and not right_is_vlm:
        return left
    if right_is_vlm and not left_is_vlm:
        return right
    return None
