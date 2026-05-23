from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AgentStep:
    name: str
    status: str
    started_at: str
    ended_at: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolCall:
    tool: str
    command: list[str]
    status: str
    elapsed_seconds: float
    stdout_tail: str = ""
    stderr_tail: str = ""


@dataclass
class QualityIssue:
    code: str
    level: str
    message: str
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParseArtifacts:
    markdown_path: Path | None = None
    content_list_path: Path | None = None
    middle_json_path: Path | None = None
    model_json_path: Path | None = None
    layout_pdf_path: Path | None = None
    span_pdf_path: Path | None = None
    origin_pdf_path: Path | None = None
    image_dir: Path | None = None

    def to_jsonable(self) -> dict[str, str | None]:
        return {key: str(value) if value else None for key, value in asdict(self).items()}


@dataclass
class AgentResult:
    run_id: str
    task: str
    profile: str
    input_file: str
    output_dir: str
    plan: list[str]
    extracted: dict[str, Any]
    quality: dict[str, Any]
    recovery_decision: dict[str, Any]
    retrieval_export: dict[str, Any]
    llm_analysis: dict[str, Any]
    artifacts: dict[str, str | None]
    trace_path: str
    summary_path: str

    def to_jsonable(self) -> dict[str, Any]:
        return asdict(self)
