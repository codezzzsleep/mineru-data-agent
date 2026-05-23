from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter
from typing import Any

from .agent import MinerUDataAgent
from .logging_utils import utc_now


def run_batch(
    *,
    manifest_path: Path,
    output_root: Path,
    agent: MinerUDataAgent,
    defaults: dict[str, Any] | None = None,
) -> dict[str, Any]:
    manifest_path = manifest_path.expanduser().resolve()
    output_root = output_root.expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    manifest = _load_manifest(manifest_path)
    manifest_defaults = manifest.get("defaults") if isinstance(manifest.get("defaults"), dict) else {}
    effective_defaults = {
        "profile": "auto",
        "backend": "pipeline",
        "method": "auto",
        "lang": "ch",
        **manifest_defaults,
        **(defaults or {}),
    }
    tasks = manifest.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("Batch manifest must contain a non-empty 'tasks' list.")

    started = perf_counter()
    items: list[dict[str, Any]] = []
    for index, raw_item in enumerate(tasks, start=1):
        item_started = perf_counter()
        if not isinstance(raw_item, dict):
            items.append(
                {
                    "index": index,
                    "status": "failed",
                    "error": "task item must be an object",
                    "elapsed_seconds": round(perf_counter() - item_started, 3),
                }
            )
            continue

        task = {**effective_defaults, **raw_item}
        input_file = task.get("input")
        objective = task.get("task")
        resolved_input = _resolve_task_input(input_file, manifest_path.parent) if input_file else None
        record: dict[str, Any] = {
            "index": index,
            "id": task.get("id") or f"task_{index}",
            "input": str(input_file),
            "resolved_input": str(resolved_input) if resolved_input else None,
            "task": objective,
            "profile": task.get("profile", "auto"),
            "status": "running",
        }
        try:
            if not input_file or not objective:
                raise ValueError("Each batch task needs 'input' and 'task'.")
            result = agent.run(
                resolved_input,
                output_root,
                task=str(objective),
                profile=str(task.get("profile", "auto")),
                backend=str(task.get("backend", "pipeline")),
                method=str(task.get("method", "auto")),
                lang=str(task.get("lang", "ch")),
            )
            record.update(
                {
                    "status": "completed",
                    "run_id": result.run_id,
                    "output_dir": result.output_dir,
                    "result_path": str(Path(result.output_dir) / "result.json"),
                    "trace_path": result.trace_path,
                    "summary_path": result.summary_path,
                    "quality_status": result.quality.get("status"),
                    "quality_score": result.quality.get("score"),
                    "retrieval_chunks_path": result.retrieval_export.get("chunks_path"),
                }
            )
        except Exception as exc:
            record.update({"status": "failed", "error": repr(exc)})
        record["elapsed_seconds"] = round(perf_counter() - item_started, 3)
        items.append(record)

    completed = sum(1 for item in items if item["status"] == "completed")
    failed = len(items) - completed
    report = {
        "created_at": utc_now(),
        "manifest_path": str(manifest_path),
        "output_root": str(output_root),
        "total": len(items),
        "completed": completed,
        "failed": failed,
        "elapsed_seconds": round(perf_counter() - started, 3),
        "items": items,
    }
    report_path = output_root / "batch_report.json"
    report["report_path"] = str(report_path)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def _load_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Batch manifest must be a JSON object.")
    return data


def _resolve_task_input(input_file: Any, manifest_dir: Path) -> Path:
    path = Path(str(input_file)).expanduser()
    if not path.is_absolute():
        path = manifest_dir / path
    return path.resolve()
