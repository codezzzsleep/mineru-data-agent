from __future__ import annotations

import json
import os
import re
from time import perf_counter
from typing import Any

import httpx

from .models import ToolCall


DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_DEEPSEEK_MODEL = "deepseek-v4-flash"
DEFAULT_MODELSCOPE_BASE_URL = "https://api-inference.modelscope.cn/v1"
DEFAULT_MODELSCOPE_MODEL = "deepseek-ai/DeepSeek-V4-Flash"


class OpenAICompatibleLLMClient:
    """Optional OpenAI-compatible adapter for agent reasoning.

    The API key is read from the environment by default. It is never included
    in tool call logs or returned artifacts.
    """

    def __init__(
        self,
        *,
        provider: str = "deepseek",
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float = 60.0,
        max_preview_chars: int = 4000,
    ) -> None:
        self.provider = provider
        if provider == "modelscope":
            self.api_key = api_key or os.getenv("MODELSCOPE_API_KEY")
            self.base_url = (base_url or os.getenv("MODELSCOPE_BASE_URL") or DEFAULT_MODELSCOPE_BASE_URL).rstrip("/")
            self.model = model or os.getenv("MODELSCOPE_MODEL") or DEFAULT_MODELSCOPE_MODEL
            self.key_env_name = "MODELSCOPE_API_KEY"
        else:
            self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
            self.base_url = (base_url or os.getenv("DEEPSEEK_BASE_URL") or DEFAULT_DEEPSEEK_BASE_URL).rstrip("/")
            self.model = model or os.getenv("DEEPSEEK_MODEL") or DEFAULT_DEEPSEEK_MODEL
            self.key_env_name = "DEEPSEEK_API_KEY"
        self.timeout_seconds = timeout_seconds
        self.max_preview_chars = max_preview_chars

    def analyze(
        self,
        *,
        task: str,
        profile: str,
        plan: list[str],
        extracted: dict[str, Any],
        quality: dict[str, Any],
    ) -> tuple[dict[str, Any], ToolCall]:
        if not self.api_key:
            raise RuntimeError(f"{self.key_env_name} is required when {self.provider} LLM mode is enabled.")

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a Data Agent controller for a MinerU-based document processing system. "
                        "Return strict JSON only. Do not include markdown fences."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "objective": (
                                "Analyze the task, refine the execution plan, propose a target extraction schema, "
                                "and review the current structured extraction for risks and recovery actions. "
                                "Be precise about tool provenance: if content_summary.source_counts contains html, "
                                "the input was parsed by the native HTML extractor, not by MinerU CLI/API. "
                                "Use error-level risk only when quality.issues contains an error-level finding."
                            ),
                            "required_json_schema": {
                                "task_understanding": "string",
                                "execution_plan": ["step strings"],
                                "target_schema": {"field_name": "description"},
                                "verification_focus": ["check strings"],
                                "risk_findings": [
                                    {"level": "info|warning|error", "message": "string", "evidence": "string"}
                                ],
                                "recovery_suggestions": ["action strings"],
                            },
                            "task": task,
                            "profile": profile,
                            "current_plan": plan,
                            "content_summary": extracted.get("content_summary", {}),
                            "parser_context": _parser_context(extracted),
                            "section_titles": [item.get("title") for item in extracted.get("sections", [])[:20]],
                            "table_count": len(extracted.get("tables", [])),
                            "numeric_fact_examples": extracted.get("numeric_facts", [])[:20],
                            "key_value_examples": extracted.get("key_values", [])[:20],
                            "quality": quality,
                            "markdown_preview": str(extracted.get("markdown_preview", ""))[: self.max_preview_chars],
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            "temperature": 0.1,
        }
        start = perf_counter()
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(
                    _chat_completions_url(self.base_url),
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
            content, reasoning_content = _extract_message_parts(data)
            analysis = _parse_json_object(content)
            analysis = _normalize_analysis(analysis, quality)
            if reasoning_content:
                analysis["reasoning_content"] = reasoning_content
            status = "completed"
            analysis.setdefault("status", status)
            stderr = ""
        except Exception as exc:
            error_text = _sanitize_error_text(str(exc), self.api_key)
            analysis = {
                "status": "failed",
                "error": error_text,
                "task_understanding": "",
                "execution_plan": [],
                "target_schema": {},
                "verification_focus": [],
                "risk_findings": [],
                "recovery_suggestions": [],
            }
            status = "failed"
            stderr = error_text[-4000:]

        call = ToolCall(
            tool=f"{self.provider}-llm",
            command=[f"{self.provider}-chat-completions", self.model],
            status=status,
            elapsed_seconds=round(perf_counter() - start, 3),
            stdout_tail=json.dumps(
                {
                    "provider": self.provider,
                    "model": self.model,
                    "base_url": self.base_url,
                    "analysis": _safe_analysis_preview(analysis),
                },
                ensure_ascii=False,
                indent=2,
            )[-4000:],
            stderr_tail=stderr,
        )
        return analysis, call


class DeepSeekLLMClient(OpenAICompatibleLLMClient):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(provider="deepseek", **kwargs)


class ModelScopeLLMClient(OpenAICompatibleLLMClient):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(provider="modelscope", **kwargs)


def _chat_completions_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    if base.endswith("/v1"):
        return f"{base}/chat/completions"
    return f"{base}/v1/chat/completions"


def _extract_message_parts(data: dict[str, Any]) -> tuple[str, str]:
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError(f"LLM response has no choices: {data!r}")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict) or not isinstance(message.get("content"), str):
        raise RuntimeError(f"LLM response has no message content: {data!r}")
    reasoning = message.get("reasoning_content")
    return message["content"], reasoning if isinstance(reasoning, str) else ""


def _parse_json_object(content: str) -> dict[str, Any]:
    clean = content.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?\s*", "", clean)
        clean = re.sub(r"\s*```$", "", clean)
    try:
        data = json.loads(clean)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", clean, flags=re.DOTALL)
        if not match:
            raise
        data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise RuntimeError("LLM output must be a JSON object.")
    return data


def _parser_context(extracted: dict[str, Any]) -> dict[str, Any]:
    summary = extracted.get("content_summary", {})
    source_counts = summary.get("source_counts", {})
    if isinstance(source_counts, dict) and source_counts.get("html"):
        parser = "native-html-extractor"
        warning = "Do not describe this HTML fixture as parsed by MinerU CLI or MinerU API."
    elif isinstance(source_counts, dict) and source_counts.get("native"):
        parser = "mineru-cli-or-mineru-api"
        warning = ""
    else:
        parser = "unknown"
        warning = "Avoid overclaiming parser provenance."
    return {
        "actual_parser": parser,
        "source_counts": source_counts if isinstance(source_counts, dict) else {},
        "provenance_level": summary.get("provenance_level"),
        "warning": warning,
    }


def _normalize_analysis(analysis: dict[str, Any], quality: dict[str, Any]) -> dict[str, Any]:
    has_quality_error = any(
        isinstance(item, dict) and item.get("level") == "error"
        for item in quality.get("issues", [])
        if isinstance(quality.get("issues", []), list)
    )
    findings = analysis.get("risk_findings")
    if not isinstance(findings, list):
        return analysis
    normalized = []
    for item in findings:
        if not isinstance(item, dict):
            continue
        clean = dict(item)
        if clean.get("level") == "error" and not has_quality_error:
            clean["level"] = "warning"
            message = str(clean.get("message", ""))
            clean["message"] = f"LLM downgraded from error because validator found no blocking error. {message}".strip()
        normalized.append(clean)
    analysis["risk_findings"] = normalized
    return analysis


def _safe_analysis_preview(analysis: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": analysis.get("status", "completed"),
        "task_understanding": str(analysis.get("task_understanding", ""))[:500],
        "execution_plan": analysis.get("execution_plan", [])[:10]
        if isinstance(analysis.get("execution_plan"), list)
        else [],
        "risk_findings": analysis.get("risk_findings", [])[:10]
        if isinstance(analysis.get("risk_findings"), list)
        else [],
    }


def _sanitize_error_text(text: str, api_key: str | None = None) -> str:
    clean = text
    if api_key:
        clean = clean.replace(api_key, "***")
    clean = re.sub(r"Bearer\s+[A-Za-z0-9._\-]+", "Bearer ***", clean)
    clean = re.sub(r"(api[_-]?key=)[^&\s]+", r"\1***", clean, flags=re.IGNORECASE)
    return clean
