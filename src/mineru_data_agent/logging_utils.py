from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Iterator

from .models import AgentStep


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TraceRecorder:
    def __init__(self) -> None:
        self.steps: list[AgentStep] = []
        self.tool_calls: list[dict[str, Any]] = []

    @contextmanager
    def step(self, name: str, **detail: Any) -> Iterator[AgentStep]:
        item = AgentStep(name=name, status="running", started_at=utc_now(), detail=detail)
        self.steps.append(item)
        try:
            yield item
        except Exception as exc:
            item.status = "failed"
            item.detail["error"] = repr(exc)
            item.ended_at = utc_now()
            raise
        else:
            item.status = "completed"
            item.ended_at = utc_now()

    def add_tool_call(self, call: dict[str, Any]) -> None:
        self.tool_calls.append(call)

    def write(self, path: Path, extra: dict[str, Any]) -> None:
        payload = {
            "created_at": utc_now(),
            "steps": [step.__dict__ for step in self.steps],
            "tool_calls": self.tool_calls,
            **extra,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


@contextmanager
def elapsed() -> Iterator[dict[str, float]]:
    data: dict[str, float] = {}
    start = perf_counter()
    try:
        yield data
    finally:
        data["elapsed_seconds"] = round(perf_counter() - start, 3)
