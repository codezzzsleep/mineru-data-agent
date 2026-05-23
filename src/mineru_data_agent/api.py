from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import os
import threading
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from . import __version__
from .agent import AgentRunError, MinerUDataAgent
from .llm_client import DeepSeekLLMClient, ModelScopeLLMClient
from .mineru_client import MinerUAgentAPIRunner, MinerURunner, resolve_mineru_executable

app = FastAPI(title="MinerU Data Agent", version=__version__)

VALID_RUNNERS = {"cli", "agent-api"}
VALID_LLMS = {"none", "deepseek", "modelscope"}
UPLOAD_CHUNK_BYTES = 1024 * 1024
ASYNC_WORKERS = max(1, int(os.getenv("MINERU_DATA_AGENT_ASYNC_WORKERS", "2")))
_EXECUTOR = ThreadPoolExecutor(max_workers=ASYNC_WORKERS, thread_name_prefix="mineru-agent-job")
_JOBS: dict[str, dict[str, Any]] = {}
_JOBS_LOCK = threading.Lock()


@dataclass
class ParseRequestConfig:
    task: str
    profile: str = "auto"
    backend: str = "pipeline"
    method: str = "auto"
    lang: str = "ch"
    runner: str = "cli"
    mineru_executable: str | None = None
    cli_fallback_on_no_page_provenance: bool = True
    fallback_mineru_executable: str | None = None
    api_max_retries: int = 2
    llm: str = "none"
    llm_model: str | None = None
    llm_base_url: str | None = None
    llm_timeout: float = 60.0


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy", "version": __version__}


@app.post("/v1/parse")
async def parse_document(
    file: UploadFile = File(...),
    task: str = Form(...),
    profile: str = Form("auto"),
    backend: str = Form("pipeline"),
    method: str = Form("auto"),
    lang: str = Form("ch"),
    runner: str = Form("cli"),
    mineru_executable: str | None = Form(None),
    cli_fallback_on_no_page_provenance: bool = Form(True),
    fallback_mineru_executable: str | None = Form(None),
    api_max_retries: int = Form(2),
    llm: str = Form("none"),
    llm_model: str | None = Form(None),
    llm_base_url: str | None = Form(None),
    llm_timeout: float = Form(60.0),
    output_root: str | None = Form(None),
) -> JSONResponse:
    config = _parse_config(
        task=task,
        profile=profile,
        backend=backend,
        method=method,
        lang=lang,
        runner=runner,
        mineru_executable=mineru_executable,
        cli_fallback_on_no_page_provenance=cli_fallback_on_no_page_provenance,
        fallback_mineru_executable=fallback_mineru_executable,
        api_max_retries=api_max_retries,
        llm=llm,
        llm_model=llm_model,
        llm_base_url=llm_base_url,
        llm_timeout=llm_timeout,
    )
    root = _resolve_output_root(output_root)
    input_path = await _persist_upload(file, root)
    return JSONResponse(_run_parse(input_path=input_path, root=root, config=config))


@app.post("/v1/jobs")
async def create_parse_job(
    file: UploadFile = File(...),
    task: str = Form(...),
    profile: str = Form("auto"),
    backend: str = Form("pipeline"),
    method: str = Form("auto"),
    lang: str = Form("ch"),
    runner: str = Form("cli"),
    mineru_executable: str | None = Form(None),
    cli_fallback_on_no_page_provenance: bool = Form(True),
    fallback_mineru_executable: str | None = Form(None),
    api_max_retries: int = Form(2),
    llm: str = Form("none"),
    llm_model: str | None = Form(None),
    llm_base_url: str | None = Form(None),
    llm_timeout: float = Form(60.0),
    output_root: str | None = Form(None),
) -> JSONResponse:
    config = _parse_config(
        task=task,
        profile=profile,
        backend=backend,
        method=method,
        lang=lang,
        runner=runner,
        mineru_executable=mineru_executable,
        cli_fallback_on_no_page_provenance=cli_fallback_on_no_page_provenance,
        fallback_mineru_executable=fallback_mineru_executable,
        api_max_retries=api_max_retries,
        llm=llm,
        llm_model=llm_model,
        llm_base_url=llm_base_url,
        llm_timeout=llm_timeout,
    )
    root = _resolve_output_root(output_root)
    input_path = await _persist_upload(file, root)
    job_id = uuid.uuid4().hex
    job_dir = root / "_jobs"
    job_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "job_id": job_id,
        "status": "queued",
        "created_at": _utc_now(),
        "started_at": None,
        "ended_at": None,
        "input_path": str(input_path),
        "output_root": str(root),
        "config": _public_config(config),
        "result": None,
        "error": None,
        "job_path": str(job_dir / f"{job_id}.json"),
    }
    _set_job(job_id, record)
    _write_job_record(record)
    _EXECUTOR.submit(_execute_job, job_id, input_path, root, config)
    return JSONResponse({"job_id": job_id, "status": "queued", "status_url": f"/v1/jobs/{job_id}"}, status_code=202)


@app.get("/v1/jobs/{job_id}")
def get_parse_job(job_id: str, output_root: str | None = None) -> JSONResponse:
    record = _get_job(job_id)
    if record is None:
        record = _load_job_record(job_id, output_root=output_root)
    if record is None:
        raise HTTPException(status_code=404, detail={"error": "job_not_found", "job_id": job_id})
    return JSONResponse(record)


def _parse_config(
    *,
    task: str,
    profile: str,
    backend: str,
    method: str,
    lang: str,
    runner: str,
    mineru_executable: str | None,
    cli_fallback_on_no_page_provenance: bool,
    fallback_mineru_executable: str | None,
    api_max_retries: int,
    llm: str,
    llm_model: str | None,
    llm_base_url: str | None,
    llm_timeout: float,
) -> ParseRequestConfig:
    runner = _normalize_choice(runner, "runner", VALID_RUNNERS)
    llm = _normalize_choice(llm, "llm", VALID_LLMS)
    if api_max_retries < 0 or api_max_retries > 10:
        raise HTTPException(status_code=400, detail={"error": "invalid_api_max_retries", "allowed_range": "0..10"})
    if llm_timeout <= 0 or llm_timeout > 600:
        raise HTTPException(status_code=400, detail={"error": "invalid_llm_timeout", "allowed_range": "0..600"})
    return ParseRequestConfig(
        task=task,
        profile=profile,
        backend=backend,
        method=method,
        lang=lang,
        runner=runner,
        mineru_executable=mineru_executable,
        cli_fallback_on_no_page_provenance=cli_fallback_on_no_page_provenance,
        fallback_mineru_executable=fallback_mineru_executable,
        api_max_retries=api_max_retries,
        llm=llm,
        llm_model=llm_model,
        llm_base_url=llm_base_url,
        llm_timeout=llm_timeout,
    )


def _run_parse(*, input_path: Path, root: Path, config: ParseRequestConfig) -> dict[str, Any]:
    parser_runner = (
        MinerUAgentAPIRunner(max_retries=config.api_max_retries)
        if config.runner == "agent-api"
        else MinerURunner(executable=config.mineru_executable)
    )
    fallback_runner = _build_fallback_runner(
        runner=config.runner,
        enabled=config.cli_fallback_on_no_page_provenance,
        fallback_mineru_executable=config.fallback_mineru_executable,
        mineru_executable=config.mineru_executable,
    )
    if config.llm == "modelscope":
        llm_client = ModelScopeLLMClient(
            model=config.llm_model, base_url=config.llm_base_url, timeout_seconds=config.llm_timeout
        )
    elif config.llm == "deepseek":
        llm_client = DeepSeekLLMClient(
            model=config.llm_model, base_url=config.llm_base_url, timeout_seconds=config.llm_timeout
        )
    else:
        llm_client = None
    try:
        result = MinerUDataAgent(parser_runner, llm_client=llm_client, fallback_mineru_runner=fallback_runner).run(
            input_path,
            root,
            task=config.task,
            profile=config.profile,
            backend=config.backend,
            method=config.method,
            lang=config.lang,
        )
    except AgentRunError as exc:
        raise _parse_failed_http_error(exc) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"error": "parse_failed", "message": str(exc)[-1000:]}) from exc
    response = result.to_jsonable()
    response["api_output_root"] = str(root)
    return response


def _parse_failed_http_error(exc: AgentRunError) -> HTTPException:
    return HTTPException(
        status_code=500,
        detail={
            "error": "parse_failed",
            "message": str(exc)[-1000:],
            "run_id": exc.run_id,
            "output_dir": exc.output_dir,
            "trace_path": exc.trace_path,
            "result_path": exc.result_path,
            "summary_path": exc.summary_path,
        },
    )


def _execute_job(job_id: str, input_path: Path, root: Path, config: ParseRequestConfig) -> None:
    _update_job(job_id, status="running", started_at=_utc_now())
    try:
        result = _run_parse(input_path=input_path, root=root, config=config)
        _update_job(job_id, status="completed", ended_at=_utc_now(), result=result)
    except HTTPException as exc:
        _update_job(job_id, status="failed", ended_at=_utc_now(), error=exc.detail)
    except Exception as exc:  # pragma: no cover - defensive guard for background worker stability.
        _update_job(job_id, status="failed", ended_at=_utc_now(), error={"error": "job_failed", "message": str(exc)[-1000:]})


async def _persist_upload(file: UploadFile, root: Path) -> Path:
    upload_dir = root / "_uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    suffix = _safe_suffix(file.filename)
    input_path = upload_dir / f"{uuid.uuid4().hex}{suffix}"
    try:
        await _write_upload(file, input_path, _max_upload_bytes())
    except HTTPException:
        input_path.unlink(missing_ok=True)
        raise
    return input_path


def _normalize_choice(value: str, name: str, allowed: set[str]) -> str:
    normalized = (value or "").strip().lower()
    if normalized not in allowed:
        raise HTTPException(
            status_code=400,
            detail={"error": f"invalid_{name}", "allowed": sorted(allowed), "received": value},
        )
    return normalized


def _set_job(job_id: str, record: dict[str, Any]) -> None:
    with _JOBS_LOCK:
        _JOBS[job_id] = record


def _get_job(job_id: str) -> dict[str, Any] | None:
    with _JOBS_LOCK:
        record = _JOBS.get(job_id)
        return dict(record) if record else None


def _update_job(job_id: str, **updates: Any) -> None:
    with _JOBS_LOCK:
        record = _JOBS[job_id]
        record.update(updates)
        snapshot = dict(record)
    _write_job_record(snapshot)


def _write_job_record(record: dict[str, Any]) -> None:
    Path(record["job_path"]).write_text(json_dumps(record), encoding="utf-8")


def _load_job_record(job_id: str, *, output_root: str | None) -> dict[str, Any] | None:
    root = _resolve_output_root(output_root)
    path = root / "_jobs" / f"{job_id}.json"
    if not path.exists():
        return None
    import json

    record = json.loads(path.read_text(encoding="utf-8"))
    _set_job(job_id, record)
    return record


def _public_config(config: ParseRequestConfig) -> dict[str, Any]:
    data = asdict(config)
    data.pop("llm_base_url", None)
    data.pop("mineru_executable", None)
    data.pop("fallback_mineru_executable", None)
    return data


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def json_dumps(value: Any) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, indent=2)


def _build_fallback_runner(
    *,
    runner: str,
    enabled: bool,
    fallback_mineru_executable: str | None,
    mineru_executable: str | None,
) -> MinerURunner | None:
    if runner != "agent-api" or not enabled:
        return None
    executable = resolve_mineru_executable(fallback_mineru_executable or mineru_executable)
    if not executable:
        return None
    return MinerURunner(executable=executable)


def _resolve_output_root(output_root: str | None) -> Path:
    default_root = os.getenv("MINERU_DATA_AGENT_OUTPUT_DIR", "runs/api")
    root = Path(output_root or default_root).expanduser().resolve()
    if output_root:
        allowed_base = Path(os.getenv("MINERU_DATA_AGENT_ALLOWED_OUTPUT_BASE", Path.cwd())).expanduser().resolve()
        if not root.is_relative_to(allowed_base):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "output_root_outside_allowed_base",
                    "allowed_base": str(allowed_base),
                    "received": str(root),
                },
            )
    return root


def _safe_suffix(filename: str | None) -> str:
    suffix = Path(filename or "input.pdf").suffix.lower()
    if not suffix or len(suffix) > 12 or not suffix.startswith("."):
        return ".pdf"
    return suffix


def _max_upload_bytes() -> int:
    raw_bytes = os.getenv("MINERU_DATA_AGENT_MAX_UPLOAD_BYTES")
    if raw_bytes:
        return max(1, int(raw_bytes))
    max_mb = float(os.getenv("MINERU_DATA_AGENT_MAX_UPLOAD_MB", "200"))
    return max(1, int(max_mb * 1024 * 1024))


async def _write_upload(file: UploadFile, input_path: Path, max_bytes: int) -> None:
    total = 0
    with input_path.open("wb") as handle:
        while True:
            chunk = await file.read(UPLOAD_CHUNK_BYTES)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise HTTPException(
                    status_code=413,
                    detail={"error": "upload_too_large", "max_bytes": max_bytes, "received_at_least": total},
                )
            handle.write(chunk)
    if total == 0:
        raise HTTPException(status_code=400, detail={"error": "empty_upload"})
