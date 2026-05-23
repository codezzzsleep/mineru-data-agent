from __future__ import annotations

import os
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from . import __version__
from .agent import AgentRunError, MinerUDataAgent
from .llm_client import DeepSeekLLMClient, ModelScopeLLMClient
from .mineru_client import MinerUAgentAPIRunner, MinerURunner

app = FastAPI(title="MinerU Data Agent", version=__version__)

VALID_RUNNERS = {"cli", "agent-api"}
VALID_LLMS = {"none", "deepseek", "modelscope"}
UPLOAD_CHUNK_BYTES = 1024 * 1024


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
    api_max_retries: int = Form(2),
    llm: str = Form("none"),
    llm_model: str | None = Form(None),
    llm_base_url: str | None = Form(None),
    llm_timeout: float = Form(60.0),
    output_root: str | None = Form(None),
) -> JSONResponse:
    runner = _normalize_choice(runner, "runner", VALID_RUNNERS)
    llm = _normalize_choice(llm, "llm", VALID_LLMS)
    if api_max_retries < 0 or api_max_retries > 10:
        raise HTTPException(status_code=400, detail={"error": "invalid_api_max_retries", "allowed_range": "0..10"})
    if llm_timeout <= 0 or llm_timeout > 600:
        raise HTTPException(status_code=400, detail={"error": "invalid_llm_timeout", "allowed_range": "0..600"})

    root = _resolve_output_root(output_root)
    upload_dir = root / "_uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    suffix = _safe_suffix(file.filename)
    input_path = upload_dir / f"{uuid.uuid4().hex}{suffix}"
    try:
        await _write_upload(file, input_path, _max_upload_bytes())
    except HTTPException:
        input_path.unlink(missing_ok=True)
        raise

    parser_runner = (
        MinerUAgentAPIRunner(max_retries=api_max_retries)
        if runner == "agent-api"
        else MinerURunner(executable=mineru_executable)
    )
    if llm == "modelscope":
        llm_client = ModelScopeLLMClient(model=llm_model, base_url=llm_base_url, timeout_seconds=llm_timeout)
    elif llm == "deepseek":
        llm_client = DeepSeekLLMClient(model=llm_model, base_url=llm_base_url, timeout_seconds=llm_timeout)
    else:
        llm_client = None
    try:
        result = MinerUDataAgent(parser_runner, llm_client=llm_client).run(
            input_path,
            root,
            task=task,
            profile=profile,
            backend=backend,
            method=method,
            lang=lang,
        )
    except AgentRunError as exc:
        raise HTTPException(
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
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"error": "parse_failed", "message": str(exc)[-1000:]}) from exc
    response = result.to_jsonable()
    response["api_output_root"] = str(root)
    return JSONResponse(response)


def _normalize_choice(value: str, name: str, allowed: set[str]) -> str:
    normalized = (value or "").strip().lower()
    if normalized not in allowed:
        raise HTTPException(
            status_code=400,
            detail={"error": f"invalid_{name}", "allowed": sorted(allowed), "received": value},
        )
    return normalized


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
