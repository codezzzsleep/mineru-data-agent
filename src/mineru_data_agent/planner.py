from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any


PROFILE_CHOICES = {
    "financial_report",
    "standard_or_contract",
    "workflow_or_diagram",
    "low_quality_ocr",
    "general_document",
}


@dataclass
class AdaptivePlanningDecision:
    profile: str
    task_intents: list[str]
    target_schema: dict[str, str]
    post_processors: list[str]
    verification_focus: list[str]
    quality_thresholds: dict[str, Any]
    recovery_strategy: list[dict[str, Any]]
    rationale: list[str] = field(default_factory=list)

    def to_jsonable(self) -> dict[str, Any]:
        return asdict(self)


def infer_profile(task: str, filename: str) -> str:
    text = f"{task} {filename}".lower()
    if any(word in text for word in ["财报", "报表", "资产", "负债", "利润", "cash", "finance", "table"]):
        return "financial_report"
    if any(word in text for word in ["规范", "标准", "条款", "合同", "standard", "clause"]):
        return "standard_or_contract"
    if any(word in text for word in ["流程", "工艺", "工程图", "图纸", "flow", "diagram"]):
        return "workflow_or_diagram"
    if any(word in text for word in ["扫描", "拍照", "模糊", "低质量", "ocr", "scan"]):
        return "low_quality_ocr"
    return "general_document"


def analyze_requirement(
    task: str,
    profile: str,
    *,
    input_metadata: dict[str, Any] | None = None,
    llm_preplan: dict[str, Any] | None = None,
) -> AdaptivePlanningDecision:
    """Build a task-specific execution plan from the natural-language request.

    This is intentionally deterministic so that the submission remains
    reproducible without an API key. When an LLM preplan exists, its schema and
    validation focus are merged into the same decision object rather than kept
    as a loose suggestion.
    """

    text = task.lower()
    metadata = input_metadata or {}
    intents = _infer_intents(text)
    schema = _default_schema(profile)
    schema.update(_schema_from_intents(intents))
    post_processors = _post_processors(profile, intents)
    verification = _verification_focus(profile, intents)
    thresholds = _quality_thresholds(profile, intents, metadata)
    recovery = _recovery_strategy(profile, intents, metadata)
    rationale = _rationale(profile, intents, metadata)

    if llm_preplan and llm_preplan.get("status") == "completed":
        llm_schema = llm_preplan.get("target_schema")
        if isinstance(llm_schema, dict):
            for key, value in llm_schema.items():
                clean_key = str(key).strip()
                if clean_key:
                    schema.setdefault(clean_key, str(value).strip() or "LLM-requested field")
        llm_focus = llm_preplan.get("verification_focus")
        if isinstance(llm_focus, list):
            for item in llm_focus:
                clean = str(item).strip()
                if clean and clean not in verification:
                    verification.append(clean)
        llm_policy = llm_preplan.get("recovery_policy")
        if isinstance(llm_policy, list):
            for item in llm_policy:
                clean = str(item).strip()
                if clean:
                    recovery.append({"action": "llm_suggested_review", "trigger": clean, "priority": "advisory"})
        rationale.append("LLM preplan target schema and verification focus were merged into the adaptive decision.")

    return AdaptivePlanningDecision(
        profile=profile if profile in PROFILE_CHOICES else "general_document",
        task_intents=intents,
        target_schema=schema,
        post_processors=post_processors,
        verification_focus=verification,
        quality_thresholds=thresholds,
        recovery_strategy=recovery,
        rationale=rationale,
    )


def build_plan(task: str, profile: str, decision: AdaptivePlanningDecision | dict[str, Any] | None = None) -> list[str]:
    if decision is None:
        decision = analyze_requirement(task, profile)
    if isinstance(decision, AdaptivePlanningDecision):
        decision_payload = decision.to_jsonable()
    else:
        decision_payload = decision

    common = [
        "Inspect input type, document metadata, and natural-language task objective",
        "Infer task intents and generate a target extraction schema",
        "Choose MinerU/native parsing path and record execution rationale",
        "Normalize content blocks with page-level or document-level provenance",
        "Build markdown, section, key-value, table, numeric, and field-evidence views",
        "Run task-specific post-processing and quality checks",
        "Select recovery action from issue codes, retry history, and task priorities",
        "Produce traceable result, summary, retrieval chunks, and audit logs",
    ]
    profile_steps = {
        "financial_report": [
            "Prioritize dense table extraction and numeric consistency checks",
            "Compute trend/comparison candidates when the task asks for growth, decline, max/min, or year-over-year change",
            "Flag subtotal/total rows and suspicious numeric cells",
        ],
        "standard_or_contract": [
            "Prioritize section hierarchy, clause-like paragraphs, parties, obligations, and dates",
            "Preserve source page or document heading evidence for each clause",
        ],
        "workflow_or_diagram": [
            "Prioritize figure/image references, ordered procedural statements, actors, inputs, and outputs",
            "Flag pages that need visual model follow-up",
        ],
        "low_quality_ocr": [
            "Prioritize OCR confidence proxies, mojibake/noise checks, and sparse-text detection",
            "Plan OCR/VLM fallback before accepting low-evidence outputs",
        ],
    }
    dynamic_steps = [
        f"Apply task intent `{intent}` with schema-aware extraction and verification"
        for intent in decision_payload.get("task_intents", [])
    ]
    return common + profile_steps.get(profile, []) + dynamic_steps


def build_task_result(extracted: dict[str, Any], decision: AdaptivePlanningDecision | dict[str, Any]) -> dict[str, Any]:
    payload = decision.to_jsonable() if isinstance(decision, AdaptivePlanningDecision) else decision
    intents = payload.get("task_intents", []) if isinstance(payload.get("task_intents"), list) else []
    result: dict[str, Any] = {
        "task_intents": intents,
        "target_schema": payload.get("target_schema", {}),
        "post_processors": payload.get("post_processors", []),
        "verification_focus": payload.get("verification_focus", []),
        "answers": {},
    }

    if any(intent in intents for intent in ["comparison", "ranking", "growth_analysis", "aggregation"]):
        comparisons = _financial_comparisons(extracted)
        result["answers"]["comparisons"] = comparisons
        if comparisons:
            fastest = max(comparisons, key=lambda item: item.get("percent_change", item.get("delta", 0)))
            result["answers"]["top_growth_candidate"] = fastest
    if "anomaly_detection" in intents:
        semantic = extracted.get("semantic_signals", {}) if isinstance(extracted, dict) else {}
        result["answers"]["anomaly_candidates"] = semantic.get("anomaly_lines", []) if isinstance(semantic, dict) else []
    if "entity_resolution" in intents:
        result["answers"]["entity_candidates"] = _entity_candidates(extracted)
    if "evidence_trace" in intents:
        result["answers"]["field_evidence"] = extracted.get("field_evidence", [])[:20]
    if "summarization" in intents:
        sections = extracted.get("sections", []) if isinstance(extracted.get("sections"), list) else []
        result["answers"]["section_titles"] = [item.get("title") for item in sections[:20] if isinstance(item, dict)]
    return result


def _infer_intents(text: str) -> list[str]:
    rules = [
        ("comparison", ["相比", "同比", "环比", "compare", "versus", "vs", "than", "变化"]),
        ("ranking", ["最快", "最高", "最低", "top", "rank", "largest", "smallest", "max", "min"]),
        ("growth_analysis", ["增长", "下降", "增速", "growth", "increase", "decrease", "decline"]),
        ("aggregation", ["合计", "总计", "小计", "sum", "total", "subtotal", "aggregate"]),
        ("anomaly_detection", ["异常", "风险", "告警", "矛盾", "mismatch", "risk", "anomaly", "warning"]),
        ("entity_resolution", ["指代", "主体", "公司", "甲方", "乙方", "entity", "party", "reference"]),
        ("cross_page_reasoning", ["跨页", "全局", "前后文", "cross-page", "global", "multi-page"]),
        ("evidence_trace", ["证据", "来源", "页码", "bbox", "trace", "evidence", "provenance"]),
        ("summarization", ["总结", "摘要", "概括", "summary", "summarize"]),
    ]
    intents = [name for name, tokens in rules if any(token in text for token in tokens)]
    if not intents:
        intents.append("structured_extraction")
    if "ranking" in intents and "growth_analysis" in intents and "comparison" not in intents:
        intents.append("comparison")
    return intents


def _default_schema(profile: str) -> dict[str, str]:
    schemas = {
        "financial_report": {
            "company_name": "reporting company or organization",
            "report_period": "reporting period/date",
            "line_item": "financial statement row name",
            "current_value": "current period value",
            "previous_value": "comparison period value",
            "unit": "currency or unit scale",
            "evidence": "source text/table evidence",
        },
        "standard_or_contract": {
            "document_title": "standard or contract title",
            "parties": "contract parties or responsible organizations",
            "clause_id": "clause or section identifier",
            "obligation": "requirement or obligation text",
            "effective_date": "date evidence",
            "evidence": "source clause evidence",
        },
        "workflow_or_diagram": {
            "process_name": "workflow or diagram name",
            "step": "ordered process step",
            "actor": "responsible actor/system",
            "input_output": "input or output artifact",
            "risk": "workflow risk or exception",
            "evidence": "source text/image evidence",
        },
        "low_quality_ocr": {
            "recognized_text": "OCR text candidate",
            "noise_signal": "blur/mojibake/sparse-text signal",
            "critical_field": "field that must be reviewed",
            "recovery_action": "retry or fallback recommendation",
            "evidence": "source evidence",
        },
    }
    return dict(schemas.get(profile, {"title": "document title", "key_fact": "important extracted fact", "evidence": "source evidence"}))


def _schema_from_intents(intents: list[str]) -> dict[str, str]:
    schema: dict[str, str] = {}
    if any(intent in intents for intent in ["comparison", "growth_analysis"]):
        schema.update(
            {
                "comparison_base": "baseline period or value",
                "comparison_current": "current period or value",
                "delta": "current minus baseline",
                "percent_change": "relative change when computable",
            }
        )
    if "ranking" in intents:
        schema["rank"] = "ranking order or selected max/min item"
    if "anomaly_detection" in intents:
        schema["risk_reason"] = "why the item should be reviewed"
    if "cross_page_reasoning" in intents:
        schema["page_span"] = "pages or chunks involved in the answer"
    return schema


def _post_processors(profile: str, intents: list[str]) -> list[str]:
    processors = ["field_evidence_builder"]
    if profile == "financial_report":
        processors.extend(["numeric_fact_extractor", "table_total_validator"])
    if any(intent in intents for intent in ["comparison", "growth_analysis", "ranking"]):
        processors.append("trend_and_ranking_analyzer")
    if "anomaly_detection" in intents:
        processors.append("anomaly_signal_collector")
    if "entity_resolution" in intents:
        processors.append("entity_alias_collector")
    if "evidence_trace" in intents:
        processors.append("evidence_trace_export")
    return processors


def _verification_focus(profile: str, intents: list[str]) -> list[str]:
    focus = ["schema_fields_have_evidence", "quality_issues_are_not_hidden"]
    if profile == "financial_report":
        focus.extend(["numeric_tokens_preserved", "subtotal_total_consistency"])
    if "comparison" in intents or "growth_analysis" in intents:
        focus.append("comparison_values_have_same_unit")
    if "cross_page_reasoning" in intents:
        focus.append("page_or_chunk_span_is_recorded")
    if "anomaly_detection" in intents:
        focus.append("risk_findings_link_to_source_text")
    return focus


def _quality_thresholds(profile: str, intents: list[str], metadata: dict[str, Any]) -> dict[str, Any]:
    base_score = 80
    if profile == "financial_report":
        base_score = 90
    if any(intent in intents for intent in ["comparison", "growth_analysis", "ranking"]):
        base_score = max(base_score, 92)
    if "evidence_trace" in intents or "cross_page_reasoning" in intents:
        base_score = max(base_score, 88)
    return {
        "min_quality_score": base_score,
        "require_tables": profile == "financial_report" or "aggregation" in intents,
        "require_numeric_facts": profile == "financial_report" or any(
            intent in intents for intent in ["comparison", "growth_analysis", "aggregation"]
        ),
        "prefer_page_provenance": metadata.get("suffix") not in {".html", ".htm", ".docx", ".pptx"},
    }


def _recovery_strategy(profile: str, intents: list[str], metadata: dict[str, Any]) -> list[dict[str, Any]]:
    suffix = str(metadata.get("suffix") or "").lower()
    strategy: list[dict[str, Any]] = []
    if suffix not in {".html", ".htm", ".docx", ".pptx"}:
        strategy.append(
            {
                "action": "cli_fallback",
                "trigger": "online_api_missing_page_provenance",
                "priority": "high" if "evidence_trace" in intents or "cross_page_reasoning" in intents else "normal",
            }
        )
        strategy.append(
            {
                "action": "ocr_retry",
                "trigger": "empty_or_sparse_text_or_ocr_quality_issue",
                "priority": "high" if profile == "low_quality_ocr" else "normal",
            }
        )
    strategy.append({"action": "text_cleanup", "trigger": "mojibake_or_encoding_noise", "priority": "normal"})
    if profile == "financial_report" or "aggregation" in intents:
        strategy.append({"action": "manual_numeric_review", "trigger": "total_or_subtotal_mismatch", "priority": "high"})
    return strategy


def _rationale(profile: str, intents: list[str], metadata: dict[str, Any]) -> list[str]:
    suffix = metadata.get("suffix") or "unknown"
    return [
        f"profile={profile} selected from task/file signals",
        f"input suffix={suffix}",
        f"task intents={', '.join(intents)}",
        "schema and recovery priorities are derived before parsing and saved for audit",
    ]


def _financial_comparisons(extracted: dict[str, Any]) -> list[dict[str, Any]]:
    tables = extracted.get("tables", []) if isinstance(extracted.get("tables"), list) else []
    comparisons: list[dict[str, Any]] = []
    for table_index, table in enumerate(tables):
        if not isinstance(table, dict):
            continue
        headers = table.get("headers", [])
        rows = table.get("rows", [])
        for row_index, row in enumerate(rows if isinstance(rows, list) else []):
            if not isinstance(row, list) or len(row) < 3:
                continue
            values = [_parse_number(cell) for cell in row[1:]]
            numeric_values = [value for value in values if value is not None]
            if len(numeric_values) < 2:
                continue
            current = numeric_values[0]
            baseline = numeric_values[1]
            delta = current - baseline
            percent_change = round(delta / baseline * 100, 4) if baseline else None
            comparisons.append(
                {
                    "label": str(row[0]),
                    "current_value": current,
                    "baseline_value": baseline,
                    "delta": round(delta, 4),
                    "percent_change": percent_change,
                    "table_index": table_index,
                    "row_index": row_index,
                    "headers": headers,
                }
            )
    return comparisons[:100]


def _entity_candidates(extracted: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for item in extracted.get("key_values", []) if isinstance(extracted.get("key_values"), list) else []:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key", ""))
        if any(token in key.lower() for token in ["公司", "甲方", "乙方", "party", "company", "issuer"]):
            candidates.append({"key": key, "value": item.get("value")})
    return candidates[:50]


def _parse_number(value: Any) -> float | None:
    text = str(value)
    match = re.search(r"[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", ""))
    except ValueError:
        return None
