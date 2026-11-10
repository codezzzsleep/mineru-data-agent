from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .extractors import probe_pdf_layout_complexity, probe_pdf_text_layer


NATIVE_SUFFIXES = {".html", ".htm", ".docx", ".pptx"}
HTML_SUFFIXES = {".html", ".htm"}
PDF_IMAGE_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".jp2", ".webp", ".gif", ".bmp"}
LIGHT_API_MAX_BYTES = 10 * 1024 * 1024
PRECISE_API_MAX_BYTES = 200 * 1024 * 1024
LIGHT_API_MAX_PAGES = 20
PRECISE_API_MAX_PAGES = 200
PRECISE_MODEL_VERSIONS = {"pipeline", "vlm", "MinerU-HTML"}
RUNNER_CHOICES = {"auto", "native", "cli", "agent-api", "precise-api"}


@dataclass
class WorkflowRoutingDecision:
    requested_runner: str
    selected_runner: str
    selected_tool: str
    selected_model_version: str
    route_mode: str
    status: str
    reasons: list[str] = field(default_factory=list)
    guardrails: list[dict[str, Any]] = field(default_factory=list)
    alternatives: list[dict[str, Any]] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)
    applied_signals: dict[str, Any] = field(default_factory=dict)
    segment_policy: dict[str, Any] = field(default_factory=dict)
    cost_policy: dict[str, Any] = field(default_factory=dict)
    quality_policy: dict[str, Any] = field(default_factory=dict)

    def to_jsonable(self) -> dict[str, Any]:
        return asdict(self)


def build_workflow_routing(
    *,
    input_metadata: dict[str, Any],
    task: str = "",
    profile: str = "general_document",
    backend: str = "pipeline",
    method: str = "auto",
    lang: str = "ch",
    requested_runner: str = "auto",
    current_runner: str = "auto",
    llm_preplan: dict[str, Any] | None = None,
    precise_api_token_available: bool | None = None,
    local_cli_available: bool | None = None,
    allow_native: bool = True,
) -> WorkflowRoutingDecision:
    suffix = str(input_metadata.get("suffix") or "").lower()
    size_bytes = _safe_int(input_metadata.get("size_bytes"))
    page_count = _safe_optional_int(input_metadata.get("page_count"))
    requested_runner = _normalize_runner(requested_runner)
    current_runner = _normalize_runner(current_runner)
    precise_token = _has_precise_api_token() if precise_api_token_available is None else bool(precise_api_token_available)
    cli_available = True if local_cli_available is None else bool(local_cli_available)
    model_version = mineru_model_version_for(backend=backend, suffix=suffix)
    task_signals = _task_signals(task=task, profile=profile, backend=backend, method=method)
    constraints = _constraints(size_bytes=size_bytes, page_count=page_count)
    guardrails = _guardrails(
        suffix=suffix,
        size_bytes=size_bytes,
        page_count=page_count,
        precise_token=precise_token,
        allow_native=allow_native,
    )

    if suffix in NATIVE_SUFFIXES and allow_native:
        selected_runner = "native"
        route_mode = "local_native_parse"
        selected_tool = "native_extractor"
        status = "ready"
        reasons = [
            "local HTML/Office input can be parsed without a remote document parser",
            "native path preserves low cost and avoids unnecessary OCR/model calls",
        ]
        alternatives = [
            _alternative("precise-api", "Use MinerU-HTML for hosted HTML parsing when remote normalization is required.", precise_token),
            _alternative("cli", "Use local MinerU CLI only when native extraction is not sufficient.", cli_available),
        ]
    else:
        selected_runner, route_mode, status, reasons = _select_non_native_runner(
            requested_runner=requested_runner,
            current_runner=current_runner,
            suffix=suffix,
            size_bytes=size_bytes,
            page_count=page_count,
            model_version=model_version,
            precise_token=precise_token,
            cli_available=cli_available,
            task_signals=task_signals,
            llm_preplan=llm_preplan,
        )
        selected_tool = _tool_name(selected_runner)
        alternatives = _non_native_alternatives(
            selected_runner=selected_runner,
            precise_token=precise_token,
            cli_available=cli_available,
            constraints=constraints,
        )

    return WorkflowRoutingDecision(
        requested_runner=requested_runner,
        selected_runner=selected_runner,
        selected_tool=selected_tool,
        selected_model_version=model_version if selected_runner == "precise-api" else "",
        route_mode=route_mode,
        status=status,
        reasons=reasons,
        guardrails=guardrails,
        alternatives=alternatives,
        constraints=constraints,
        applied_signals={
            "suffix": suffix,
            "size_bytes": size_bytes,
            "page_count": page_count,
            "has_text_layer": input_metadata.get("has_text_layer"),
            "probe_source": input_metadata.get("probe_source"),
            "is_complex_layout": input_metadata.get("is_complex_layout"),
            "layout_type": input_metadata.get("layout_type"),
            "layout_risk": input_metadata.get("layout_risk"),
            "multi_column_pages": input_metadata.get("multi_column_pages"),
            "layout_sampled_pages": input_metadata.get("layout_sampled_pages"),
            "layout_probe_source": input_metadata.get("layout_probe_source"),
            "has_tables": input_metadata.get("has_tables"),
            "table_pages": input_metadata.get("table_pages"),
            "table_count": input_metadata.get("table_count"),
            "table_risk": input_metadata.get("table_risk"),
            "profile": profile,
            "backend": backend,
            "method": method,
            "lang": lang,
            "task_signals": task_signals,
            "llm_recommended_runner": (llm_preplan or {}).get("recommended_runner"),
            "precise_api_token_available": precise_token,
            "local_cli_available": cli_available,
        },
        segment_policy=_segment_policy(suffix=suffix, profile=profile, task_signals=task_signals),
        cost_policy=_cost_policy(selected_runner=selected_runner, task_signals=task_signals),
        quality_policy=_quality_policy(selected_runner=selected_runner, model_version=model_version, task_signals=task_signals),
    )


def build_input_metadata(input_path: Path) -> dict[str, Any]:
    path = Path(input_path)
    stat = path.stat()
    page_count: int | None = None
    has_text_layer: bool | None = None
    probe_source = "not_applicable"
    layout_probe: dict[str, Any] = {}
    if path.suffix.lower() == ".pdf":
        page_count, has_text_layer = probe_pdf_text_layer(path)
        probe_source = "pypdf" if page_count is not None else "unavailable"
        if has_text_layer:
            layout_probe = probe_pdf_layout_complexity(path)
    return {
        "filename": path.name,
        "suffix": path.suffix.lower(),
        "size_bytes": stat.st_size,
        "page_count": page_count,
        "has_text_layer": has_text_layer,
        "probe_source": probe_source,
        "layout_type": layout_probe.get("layout_type", "unknown"),
        "layout_risk": layout_probe.get("layout_risk", "unknown"),
        "is_complex_layout": bool(layout_probe.get("is_complex_layout", False)),
        "multi_column_pages": int(layout_probe.get("multi_column_pages") or 0),
        "layout_sampled_pages": int(layout_probe.get("sampled_pages") or 0),
        "layout_probe_source": layout_probe.get("probe_source", "not_applicable"),
        "has_tables": bool(layout_probe.get("has_tables", False)),
        "table_pages": layout_probe.get("table_pages", []),
        "table_count": int(layout_probe.get("table_count") or 0),
        "table_risk": layout_probe.get("table_risk", "unknown"),
        "is_native_extractor_input": path.suffix.lower() in NATIVE_SUFFIXES,
    }


def mineru_model_version_for(*, backend: str, suffix: str, explicit_model_version: str | None = None) -> str:
    if explicit_model_version and explicit_model_version in PRECISE_MODEL_VERSIONS:
        return explicit_model_version
    if suffix.lower() in HTML_SUFFIXES:
        return "MinerU-HTML"
    if backend == "vlm" or backend.startswith("vlm-"):
        return "vlm"
    return "pipeline"


def _select_non_native_runner(
    *,
    requested_runner: str,
    current_runner: str,
    suffix: str,
    size_bytes: int,
    page_count: int | None,
    model_version: str,
    precise_token: bool,
    cli_available: bool,
    task_signals: dict[str, Any],
    llm_preplan: dict[str, Any] | None,
) -> tuple[str, str, str, list[str]]:
    runner_request = _effective_runner_request(requested_runner, current_runner, llm_preplan)
    light_eligible = _within_light_limits(size_bytes=size_bytes, page_count=page_count)
    precise_eligible = _within_precise_limits(size_bytes=size_bytes, page_count=page_count)
    needs_precise = (
        task_signals["needs_json_artifacts"]
        or task_signals["complex_layout"]
        or model_version in {"vlm", "MinerU-HTML"}
        or not light_eligible
    )

    if runner_request == "precise-api":
        if precise_token and precise_eligible:
            return (
                "precise-api",
                "requested_precise_api",
                "ready",
                ["precise API was requested and token/size guardrails are satisfied"],
            )
        fallback, status, reason = _fallback_without_precise(
            light_eligible=light_eligible,
            cli_available=cli_available,
            precise_token=precise_token,
            precise_eligible=precise_eligible,
        )
        return fallback, "precise_api_unavailable_fallback", status, [reason]

    if runner_request == "agent-api":
        if light_eligible:
            return "agent-api", "requested_light_agent_api", "ready", ["light Agent API was requested and input fits its limits"]
        if precise_token and precise_eligible:
            return "precise-api", "agent_api_limit_escalation", "ready", ["light Agent API limit exceeded; precise API can handle this input"]
        if cli_available:
            return "cli", "agent_api_limit_cli_fallback", "ready_with_local_dependency", ["light Agent API limit exceeded; use local CLI fallback"]
        return "agent-api", "agent_api_limit_risk", "needs_config", ["light Agent API limit exceeded and no precise token or local CLI is available"]

    if runner_request == "cli":
        return (
            "cli",
            "requested_local_cli",
            "ready_with_local_dependency" if cli_available else "needs_config",
            ["local CLI was requested; it provides full local artifacts and page provenance"],
        )

    if needs_precise and precise_token and precise_eligible:
        return (
            "precise-api",
            "auto_precise_for_complex_or_large_input",
            "ready",
            ["complex/large/high-fidelity task signals favor precise API over the lightweight parser"],
        )
    if light_eligible:
        return (
            "agent-api",
            "auto_light_agent_api",
            "ready",
            ["input fits the lightweight Agent API; choose the economical parser first"],
        )
    if cli_available:
        return (
            "cli",
            "auto_local_cli_for_offline_or_large_input",
            "ready_with_local_dependency",
            ["input exceeds light API limits and no usable precise API route was selected"],
        )
    return (
        "agent-api",
        "auto_no_suitable_remote_route",
        "needs_config",
        ["input likely exceeds light API limits; configure precise API token or local CLI"],
    )


def _effective_runner_request(requested_runner: str, current_runner: str, llm_preplan: dict[str, Any] | None) -> str:
    if requested_runner != "auto":
        return requested_runner
    if current_runner != "auto":
        return current_runner
    llm_runner = _normalize_runner((llm_preplan or {}).get("recommended_runner"))
    if llm_runner in {"cli", "agent-api", "precise-api"}:
        return llm_runner
    return "auto"


def _fallback_without_precise(
    *,
    light_eligible: bool,
    cli_available: bool,
    precise_token: bool,
    precise_eligible: bool,
) -> tuple[str, str, str]:
    if not precise_token:
        reason = "precise API token is not configured"
    elif not precise_eligible:
        reason = "input exceeds precise API limits"
    else:
        reason = "precise API route is not available"
    if light_eligible:
        return "agent-api", "ready_with_quality_risk", f"{reason}; falling back to lightweight Agent API"
    if cli_available:
        return "cli", "ready_with_local_dependency", f"{reason}; falling back to local CLI"
    return "agent-api", "needs_config", f"{reason}; configure token or local CLI before production use"


def _constraints(*, size_bytes: int, page_count: int | None) -> dict[str, Any]:
    return {
        "input_size_bytes": size_bytes,
        "page_count": page_count,
        "agent_light_api": {
            "max_size_bytes": LIGHT_API_MAX_BYTES,
            "max_pages": LIGHT_API_MAX_PAGES,
            "markdown_only": True,
            "batch": False,
            "eligible": _within_light_limits(size_bytes=size_bytes, page_count=page_count),
        },
        "precise_api": {
            "max_size_bytes": PRECISE_API_MAX_BYTES,
            "max_pages": PRECISE_API_MAX_PAGES,
            "markdown_and_json_zip": True,
            "batch": True,
            "eligible": _within_precise_limits(size_bytes=size_bytes, page_count=page_count),
        },
    }


def _guardrails(
    *,
    suffix: str,
    size_bytes: int,
    page_count: int | None,
    precise_token: bool,
    allow_native: bool,
) -> list[dict[str, Any]]:
    checks = [
        {
            "name": "native_local_first",
            "status": "pass" if suffix in NATIVE_SUFFIXES and allow_native else "not_applicable",
            "message": "Local HTML/Office files should be parsed locally before remote parsers are considered.",
        },
        {
            "name": "agent_light_size_limit",
            "status": "pass" if size_bytes <= LIGHT_API_MAX_BYTES else "fail",
            "message": "Light Agent API is limited to 10MB.",
        },
        {
            "name": "agent_light_page_limit",
            "status": "unknown" if page_count is None else ("pass" if page_count <= LIGHT_API_MAX_PAGES else "fail"),
            "message": "Light Agent API is limited to 20 pages.",
        },
        {
            "name": "precise_api_token",
            "status": "pass" if precise_token else "missing",
            "message": "Precise API requires a server-side token.",
        },
        {
            "name": "precise_api_size_limit",
            "status": "pass" if size_bytes <= PRECISE_API_MAX_BYTES else "fail",
            "message": "Precise API is limited to 200MB.",
        },
    ]
    return checks


def _non_native_alternatives(
    *,
    selected_runner: str,
    precise_token: bool,
    cli_available: bool,
    constraints: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        _alternative(
            "agent-api",
            "Cheapest remote path for small single files, Markdown only.",
            bool(constraints["agent_light_api"]["eligible"]),
            selected=selected_runner == "agent-api",
        ),
        _alternative(
            "precise-api",
            "Higher-fidelity MinerU API with Markdown/JSON zip output and pipeline/vlm/MinerU-HTML model routing.",
            bool(precise_token and constraints["precise_api"]["eligible"]),
            selected=selected_runner == "precise-api",
        ),
        _alternative(
            "cli",
            "Local MinerU CLI path for offline artifacts, page provenance, and API fallback.",
            cli_available,
            selected=selected_runner == "cli",
        ),
    ]


def _alternative(name: str, reason: str, available: bool, *, selected: bool = False) -> dict[str, Any]:
    return {"runner": name, "available": bool(available), "selected": bool(selected), "reason": reason}


def _segment_policy(*, suffix: str, profile: str, task_signals: dict[str, Any]) -> dict[str, Any]:
    return {
        "mode": "document_then_blocks",
        "current_granularity": "section/table/block chunks after parser output",
        "next_granularity": "page/region routing before parser execution",
        "local_html_rule": suffix in NATIVE_SUFFIXES,
        "table_priority": bool(task_signals["needs_json_artifacts"] or profile == "financial_report"),
        "visual_priority": bool(task_signals["complex_layout"]),
        "merge_policy": "merge parser artifacts into one structured view, then export retrieval chunks and evidence records",
    }


def _cost_policy(*, selected_runner: str, task_signals: dict[str, Any]) -> dict[str, Any]:
    return {
        "selected_runner": selected_runner,
        "principle": "start with the cheapest parser that can satisfy quality and evidence requirements",
        "economy_first": selected_runner in {"native", "agent-api"},
        "escalation_signal": bool(task_signals["complex_layout"] or task_signals["needs_json_artifacts"]),
    }


def _quality_policy(*, selected_runner: str, model_version: str, task_signals: dict[str, Any]) -> dict[str, Any]:
    return {
        "selected_runner": selected_runner,
        "model_version": model_version if selected_runner == "precise-api" else "",
        "quality_gates": [
            "empty_result",
            "possible_mojibake",
            "short_text",
            "no_page_provenance",
            "numeric_total_mismatch",
        ],
        "recovery_triggers": [
            "text_cleanup",
            "ocr_retry",
            "cli_fallback",
            "manual_numeric_review",
        ],
        "requires_table_review": bool(task_signals["needs_json_artifacts"]),
        "requires_visual_review": bool(task_signals["complex_layout"]),
    }


def _task_signals(*, task: str, profile: str, backend: str, method: str) -> dict[str, Any]:
    text = f"{task} {profile} {backend} {method}".lower()
    complex_keywords = [
        "table",
        "chart",
        "diagram",
        "flow",
        "layout",
        "financial",
        "subtotal",
        "total",
        "formula",
        "vlm",
    ]
    json_keywords = [
        "json",
        "structured",
        "schema",
        "table",
        "financial",
        "subtotal",
        "total",
        "evidence",
        "provenance",
        "trace",
    ]
    return {
        "complex_layout": profile in {"workflow_or_diagram"} or any(item in text for item in complex_keywords),
        "needs_json_artifacts": profile in {"financial_report", "standard_or_contract"} or any(item in text for item in json_keywords),
        "ocr_heavy": profile == "low_quality_ocr" or method == "ocr" or "ocr" in text or "scan" in text,
    }


def _tool_name(runner: str) -> str:
    return {
        "native": "native_extractor",
        "cli": "mineru_cli",
        "agent-api": "mineru_agent_api",
        "precise-api": "mineru_precise_api",
        "auto": "mineru_auto_router",
    }.get(runner, "mineru_auto_router")


def _within_light_limits(*, size_bytes: int, page_count: int | None) -> bool:
    return size_bytes <= LIGHT_API_MAX_BYTES and (page_count is None or page_count <= LIGHT_API_MAX_PAGES)


def _within_precise_limits(*, size_bytes: int, page_count: int | None) -> bool:
    return size_bytes <= PRECISE_API_MAX_BYTES and (page_count is None or page_count <= PRECISE_API_MAX_PAGES)


def _normalize_runner(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text if text in RUNNER_CHOICES else "auto"


def _safe_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _safe_optional_int(value: Any) -> int | None:
    if value in {None, ""}:
        return None
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return None


def _has_precise_api_token() -> bool:
    return bool(os.getenv("MINERU_PRECISE_API_TOKEN") or os.getenv("MINERU_API_TOKEN"))
