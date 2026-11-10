from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
import zipfile
from pathlib import Path
from time import perf_counter
from typing import Any

import httpx

from .models import ParseArtifacts, ToolCall


def resolve_mineru_executable(executable: str | None = None) -> str | None:
    candidate = executable or os.getenv("MINERU_EXECUTABLE")
    if candidate:
        return candidate
    return shutil.which("mineru")


class MinerUParseError(RuntimeError):
    def __init__(self, message: str, tool_call: ToolCall) -> None:
        super().__init__(message)
        self.tool_call = tool_call


class MinerURunner:
    """Thin adapter around MinerU CLI output.

    The competition requires reproducibility and traceability. Calling the CLI
    keeps deployment simple on HeyWhale images while still exposing every
    generated artifact to the Data Agent.
    """

    def __init__(
        self,
        executable: str | None = None,
        model_source: str | None = None,
        timeout_seconds: int = 1800,
    ) -> None:
        self.executable = executable or os.getenv("MINERU_EXECUTABLE") or "mineru"
        self.model_source = model_source or os.getenv("MINERU_MODEL_SOURCE") or "modelscope"
        self.timeout_seconds = timeout_seconds

    def parse(
        self,
        input_path: Path,
        output_dir: Path,
        *,
        backend: str = "pipeline",
        method: str = "auto",
        lang: str = "ch",
        start_page: int | None = None,
        end_page: int | None = None,
    ) -> tuple[ParseArtifacts, ToolCall]:
        input_path = input_path.resolve()
        output_dir = output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        command = [
            self.executable,
            "-p",
            str(input_path),
            "-o",
            str(output_dir),
            "-b",
            backend,
            "-m",
            method,
            "-l",
            lang,
        ]
        if start_page is not None:
            command += ["--start", str(start_page)]
        if end_page is not None:
            command += ["--end", str(end_page)]

        env = os.environ.copy()
        env.setdefault("MINERU_MODEL_SOURCE", self.model_source)
        start = perf_counter()
        try:
            proc = subprocess.run(
                command,
                cwd=output_dir,
                env=env,
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except Exception as exc:
            elapsed = round(perf_counter() - start, 3)
            call = ToolCall(
                tool="mineru-cli",
                command=command,
                status="failed",
                elapsed_seconds=elapsed,
                stdout_tail="",
                stderr_tail=str(exc)[-4000:],
            )
            raise MinerUParseError(f"MinerU CLI failed before completion. {call.stderr_tail}", call) from exc
        elapsed = round(perf_counter() - start, 3)
        call = ToolCall(
            tool="mineru-cli",
            command=command,
            status="completed" if proc.returncode == 0 else "failed",
            elapsed_seconds=elapsed,
            stdout_tail=proc.stdout[-4000:],
            stderr_tail=proc.stderr[-4000:],
        )
        if proc.returncode != 0:
            raise MinerUParseError(
                "MinerU CLI failed. "
                f"returncode={proc.returncode}; stderr_tail={call.stderr_tail}",
                call,
            )
        return self._find_artifacts(output_dir, input_path.stem, method), call

    @staticmethod
    def _find_artifacts(output_dir: Path, stem: str, method: str) -> ParseArtifacts:
        candidate_dirs = [
            output_dir / stem / method,
            output_dir / stem / "auto",
            output_dir / stem / "ocr",
            output_dir / stem / "txt",
            output_dir,
        ]
        base = next((item for item in candidate_dirs if item.exists()), output_dir)

        def first(pattern: str) -> Path | None:
            matches = sorted(base.glob(pattern))
            if matches:
                return matches[0]
            matches = sorted(output_dir.rglob(pattern))
            return matches[0] if matches else None

        return ParseArtifacts(
            markdown_path=first("*.md"),
            content_list_path=first("*content_list.json"),
            middle_json_path=first("*middle.json"),
            model_json_path=first("*model.json"),
            layout_pdf_path=first("*layout.pdf"),
            span_pdf_path=first("*span.pdf"),
            origin_pdf_path=first("*origin.pdf"),
            image_dir=(base / "images") if (base / "images").exists() else None,
        )


class MinerUAgentAPIRunner:
    """Adapter for MinerU's no-token Agent lightweight API.

    This backend is intentionally small: it uploads one local file, polls the
    async task, downloads the final Markdown, and writes a synthetic content
    list so the rest of the Data Agent pipeline can stay unchanged.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        timeout_seconds: int = 300,
        poll_interval_seconds: float = 3.0,
        request_timeout_seconds: float = 60.0,
        max_retries: int = 2,
        retry_backoff_seconds: float = 2.0,
        enable_table: bool = True,
        enable_formula: bool = True,
        is_ocr: bool | None = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("MINERU_AGENT_API_BASE_URL") or "https://mineru.net/api/v1/agent").rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.poll_interval_seconds = poll_interval_seconds
        self.request_timeout_seconds = request_timeout_seconds
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self.enable_table = enable_table
        self.enable_formula = enable_formula
        self.is_ocr = is_ocr

    def parse(
        self,
        input_path: Path,
        output_dir: Path,
        *,
        backend: str = "pipeline",
        method: str = "auto",
        lang: str = "ch",
        start_page: int | None = None,
        end_page: int | None = None,
    ) -> tuple[ParseArtifacts, ToolCall]:
        input_path = input_path.resolve()
        output_dir = output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        page_range = _build_page_range(start_page, end_page)
        payload: dict[str, Any] = {
            "file_name": input_path.name,
            "language": lang,
            "enable_table": self.enable_table,
            "enable_formula": self.enable_formula,
            "is_ocr": method == "ocr" if self.is_ocr is None else self.is_ocr,
        }
        if page_range:
            payload["page_range"] = page_range

        start = perf_counter()
        events: list[dict[str, Any]] = []
        command = ["mineru-agent-api", "parse-file", input_path.name]
        try:
            with httpx.Client(timeout=self.request_timeout_seconds) as client:
                submit = self._request_with_retries(
                    client,
                    "POST",
                    f"{self.base_url}/parse/file",
                    events,
                    action="create_upload_task",
                    json=payload,
                )
                submit_data = _load_api_json(submit, "create upload task")
                _ensure_api_success(submit_data, "create upload task")
                task_id = submit_data["data"]["task_id"]
                file_url = submit_data["data"]["file_url"]
                events.append({"event": "task_created", "task_id": task_id, "trace_id": submit_data.get("trace_id")})

                with input_path.open("rb") as handle:
                    upload_bytes = handle.read()
                upload = self._request_with_retries(
                    client,
                    "PUT",
                    file_url,
                    events,
                    action="upload_file",
                    content=upload_bytes,
                )
                events.append({"event": "file_uploaded", "status_code": upload.status_code})

                final_data = self._poll_until_done(client, task_id, events)
                events.append({"event": "task_done", "task_id": task_id, "markdown_url": final_data.get("markdown_url")})
                markdown_url = final_data["markdown_url"]
                markdown_response = self._request_with_retries(
                    client,
                    "GET",
                    markdown_url,
                    events,
                    action="download_markdown",
                )
                markdown = markdown_response.content.decode("utf-8", errors="replace")
        except Exception as exc:
            elapsed = round(perf_counter() - start, 3)
            error_text = _redact_sensitive_text(str(exc))
            call = ToolCall(
                tool="mineru-agent-api",
                command=command,
                status="failed",
                elapsed_seconds=elapsed,
                stdout_tail=_tail_json(events),
                stderr_tail=error_text[-4000:],
            )
            raise MinerUParseError(f"MinerU Agent API failed. {call.stderr_tail}", call) from exc

        base = output_dir / input_path.stem / "agent_api"
        base.mkdir(parents=True, exist_ok=True)
        markdown_path = base / f"{input_path.stem}.md"
        content_list_path = base / f"{input_path.stem}_content_list.json"
        response_path = base / f"{input_path.stem}_agent_response.json"
        markdown_path.write_text(markdown, encoding="utf-8")
        content_list_path.write_text(
            json.dumps(_markdown_to_content_blocks(markdown, source="mineru-agent-api"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        response_path.write_text(_tail_json(events), encoding="utf-8")

        elapsed = round(perf_counter() - start, 3)
        call = ToolCall(
            tool="mineru-agent-api",
            command=command,
            status="completed",
            elapsed_seconds=elapsed,
            stdout_tail=_tail_json(events),
            stderr_tail="",
        )
        return ParseArtifacts(markdown_path=markdown_path, content_list_path=content_list_path, model_json_path=response_path), call

    def _poll_until_done(
        self,
        client: httpx.Client,
        task_id: str,
        events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        deadline = time.monotonic() + self.timeout_seconds
        while time.monotonic() < deadline:
            response = self._request_with_retries(
                client,
                "GET",
                f"{self.base_url}/parse/{task_id}",
                events,
                action="poll_task",
            )
            result = _load_api_json(response, "poll task")
            _ensure_api_success(result, "poll task")
            data = result.get("data") or {}
            state = data.get("state")
            events.append({"event": "task_polled", "state": state, "trace_id": result.get("trace_id")})
            if state == "done":
                if not data.get("markdown_url"):
                    raise RuntimeError(f"Task {task_id} completed without markdown_url.")
                return data
            if state == "failed":
                err_msg = data.get("err_msg") or "unknown MinerU Agent API failure"
                err_code = data.get("err_code")
                raise RuntimeError(f"Task {task_id} failed: {err_code} {err_msg}")
            time.sleep(self.poll_interval_seconds)
        raise TimeoutError(f"MinerU Agent API task timed out after {self.timeout_seconds}s: {task_id}")

    def _request_with_retries(
        self,
        client: httpx.Client,
        method: str,
        url: str,
        events: list[dict[str, Any]],
        *,
        action: str,
        **kwargs: Any,
    ) -> httpx.Response:
        retry_statuses = {408, 409, 425, 429, 500, 502, 503, 504}
        for attempt in range(self.max_retries + 1):
            try:
                response = client.request(method, url, **kwargs)
                if response.status_code in retry_statuses and attempt < self.max_retries:
                    events.append(
                        {
                            "event": "request_retry",
                            "action": action,
                            "attempt": attempt + 1,
                            "status_code": response.status_code,
                        }
                    )
                    time.sleep(self.retry_backoff_seconds * (attempt + 1))
                    continue
                response.raise_for_status()
                return response
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                if attempt >= self.max_retries:
                    raise
                events.append(
                    {
                        "event": "request_retry",
                        "action": action,
                        "attempt": attempt + 1,
                        "error": _redact_sensitive_text(str(exc))[-500:],
                    }
                )
                time.sleep(self.retry_backoff_seconds * (attempt + 1))
        raise RuntimeError(f"unreachable retry state while trying to {action}")


class MinerUPreciseAPIRunner:
    """Adapter for MinerU's token-based precise extraction API.

    The precise API is the high-fidelity branch in the Data Agent tool router.
    It supports pipeline/vlm/MinerU-HTML model versions and returns a zip
    package with Markdown plus structured JSON artifacts.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_token: str | None = None,
        model_version: str | None = None,
        timeout_seconds: int = 1800,
        poll_interval_seconds: float = 5.0,
        request_timeout_seconds: float = 60.0,
        max_retries: int = 2,
        retry_backoff_seconds: float = 2.0,
        enable_table: bool = True,
        enable_formula: bool = True,
        extra_formats: list[str] | None = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("MINERU_PRECISE_API_BASE_URL") or "https://mineru.net/api/v4").rstrip("/")
        self.api_token = api_token or os.getenv("MINERU_PRECISE_API_TOKEN") or os.getenv("MINERU_API_TOKEN")
        self.model_version = model_version or os.getenv("MINERU_PRECISE_MODEL_VERSION")
        self.timeout_seconds = timeout_seconds
        self.poll_interval_seconds = poll_interval_seconds
        self.request_timeout_seconds = request_timeout_seconds
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self.enable_table = enable_table
        self.enable_formula = enable_formula
        self.extra_formats = list(extra_formats or _env_list("MINERU_PRECISE_EXTRA_FORMATS"))

    def parse(
        self,
        input_path: Path,
        output_dir: Path,
        *,
        backend: str = "pipeline",
        method: str = "auto",
        lang: str = "ch",
        start_page: int | None = None,
        end_page: int | None = None,
    ) -> tuple[ParseArtifacts, ToolCall]:
        input_path = input_path.resolve()
        output_dir = output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        model_version = _precise_model_version(input_path, backend=backend, explicit_model_version=self.model_version)
        page_ranges = _build_page_range(start_page, end_page)
        payload = _build_precise_file_urls_payload(
            input_path,
            model_version=model_version,
            method=method,
            lang=lang,
            enable_table=self.enable_table,
            enable_formula=self.enable_formula,
            page_ranges=page_ranges,
            extra_formats=self.extra_formats,
        )
        command = ["mineru-precise-api", "file-urls-batch", input_path.name, "--model-version", model_version]
        events: list[dict[str, Any]] = []
        start = perf_counter()

        try:
            if not self.api_token:
                raise RuntimeError("MINERU_PRECISE_API_TOKEN or MINERU_API_TOKEN is required for precise-api runner.")
            headers = self._headers()
            with httpx.Client(timeout=self.request_timeout_seconds) as client:
                submit = self._request_with_retries(
                    client,
                    "POST",
                    f"{self.base_url}/file-urls/batch",
                    events,
                    action="create_precise_upload_urls",
                    headers=headers,
                    json=payload,
                )
                submit_data = _load_api_json(submit, "create precise upload urls")
                _ensure_api_success(submit_data, "create precise upload urls")
                data = submit_data.get("data") or {}
                batch_id = str(data.get("batch_id") or "")
                upload_urls = data.get("file_urls") or []
                if not batch_id or not isinstance(upload_urls, list) or not upload_urls:
                    raise RuntimeError(f"Precise API did not return batch_id/file_urls: {_tail_json(submit_data)}")
                upload_url = str(upload_urls[0])
                events.append(
                    {
                        "event": "precise_batch_created",
                        "batch_id": batch_id,
                        "trace_id": submit_data.get("trace_id"),
                        "model_version": model_version,
                    }
                )

                with input_path.open("rb") as handle:
                    upload = self._request_with_retries(
                        client,
                        "PUT",
                        upload_url,
                        events,
                        action="upload_precise_file",
                        content=handle.read(),
                    )
                events.append({"event": "precise_file_uploaded", "status_code": upload.status_code})

                final_data = self._poll_batch_until_done(client, batch_id, input_path.name, events, headers=headers)
                zip_url = str(final_data.get("full_zip_url") or "")
                if not zip_url:
                    raise RuntimeError(f"Precise API result completed without full_zip_url: {_tail_json(final_data)}")
                zip_response = self._request_with_retries(
                    client,
                    "GET",
                    zip_url,
                    events,
                    action="download_precise_zip",
                )
        except Exception as exc:
            elapsed = round(perf_counter() - start, 3)
            call = ToolCall(
                tool="mineru-precise-api",
                command=command,
                status="failed",
                elapsed_seconds=elapsed,
                stdout_tail=_tail_json(events),
                stderr_tail=_redact_sensitive_text(str(exc))[-4000:],
                metadata={"model_version": model_version},
            )
            raise MinerUParseError(f"MinerU precise API failed. {call.stderr_tail}", call) from exc

        base = output_dir / input_path.stem / "precise_api"
        extract_dir = base / "extracted"
        base.mkdir(parents=True, exist_ok=True)
        extract_dir.mkdir(parents=True, exist_ok=True)
        zip_path = base / f"{input_path.stem}_full.zip"
        response_path = base / f"{input_path.stem}_precise_response.json"
        zip_path.write_bytes(zip_response.content)
        _extract_zip(zip_path, extract_dir)
        response_path.write_text(_tail_json(events), encoding="utf-8")

        artifacts = _find_precise_artifacts(extract_dir, input_path.stem)
        if artifacts.markdown_path and not artifacts.content_list_path:
            content_path = base / f"{input_path.stem}_content_list.json"
            markdown = artifacts.markdown_path.read_text(encoding="utf-8", errors="replace")
            content_path.write_text(
                json.dumps(_markdown_to_content_blocks(markdown, source="mineru-precise-api"), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            artifacts.content_list_path = content_path
        artifacts.model_json_path = artifacts.model_json_path or response_path

        elapsed = round(perf_counter() - start, 3)
        call = ToolCall(
            tool="mineru-precise-api",
            command=command,
            status="completed",
            elapsed_seconds=elapsed,
            stdout_tail=_tail_json(events),
            stderr_tail="",
            metadata={"model_version": model_version, "zip_path": str(zip_path)},
        )
        return artifacts, call

    def _poll_batch_until_done(
        self,
        client: httpx.Client,
        batch_id: str,
        filename: str,
        events: list[dict[str, Any]],
        *,
        headers: dict[str, str],
    ) -> dict[str, Any]:
        deadline = time.monotonic() + self.timeout_seconds
        while time.monotonic() < deadline:
            response = self._request_with_retries(
                client,
                "GET",
                f"{self.base_url}/extract-results/batch/{batch_id}",
                events,
                action="poll_precise_batch",
                headers=headers,
            )
            result = _load_api_json(response, "poll precise batch")
            _ensure_api_success(result, "poll precise batch")
            data = result.get("data") or {}
            selected = _select_precise_extract_result(data.get("extract_result"), filename)
            state = str(selected.get("state") or data.get("state") or "")
            events.append(
                {
                    "event": "precise_batch_polled",
                    "batch_id": batch_id,
                    "state": state,
                    "trace_id": result.get("trace_id"),
                    "progress": selected.get("extract_progress"),
                }
            )
            if state == "done":
                return selected
            if state == "failed":
                raise RuntimeError(f"Precise API batch {batch_id} failed: {selected.get('err_msg') or selected}")
            time.sleep(self.poll_interval_seconds)
        raise TimeoutError(f"MinerU precise API batch timed out after {self.timeout_seconds}s: {batch_id}")

    def _request_with_retries(
        self,
        client: httpx.Client,
        method: str,
        url: str,
        events: list[dict[str, Any]],
        *,
        action: str,
        **kwargs: Any,
    ) -> httpx.Response:
        retry_statuses = {408, 409, 425, 429, 500, 502, 503, 504}
        for attempt in range(self.max_retries + 1):
            try:
                response = client.request(method, url, **kwargs)
                if response.status_code in retry_statuses and attempt < self.max_retries:
                    events.append(
                        {
                            "event": "request_retry",
                            "action": action,
                            "attempt": attempt + 1,
                            "status_code": response.status_code,
                        }
                    )
                    time.sleep(self.retry_backoff_seconds * (attempt + 1))
                    continue
                response.raise_for_status()
                return response
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                if attempt >= self.max_retries:
                    raise
                events.append(
                    {
                        "event": "request_retry",
                        "action": action,
                        "attempt": attempt + 1,
                        "error": _redact_sensitive_text(str(exc))[-500:],
                    }
                )
                time.sleep(self.retry_backoff_seconds * (attempt + 1))
        raise RuntimeError(f"unreachable retry state while trying to {action}")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "Accept": "*/*",
        }


def _build_page_range(start_page: int | None, end_page: int | None) -> str | None:
    if start_page is None and end_page is None:
        return None
    if start_page is not None and end_page is not None:
        return f"{start_page}-{end_page}"
    return str(start_page or end_page)


def _precise_model_version(
    input_path: Path,
    *,
    backend: str,
    explicit_model_version: str | None = None,
) -> str:
    if explicit_model_version in {"pipeline", "vlm", "MinerU-HTML"}:
        return explicit_model_version
    if input_path.suffix.lower() in {".html", ".htm"}:
        return "MinerU-HTML"
    if backend == "vlm" or backend.startswith("vlm-"):
        return "vlm"
    return "pipeline"


def _build_precise_file_urls_payload(
    input_path: Path,
    *,
    model_version: str,
    method: str,
    lang: str,
    enable_table: bool,
    enable_formula: bool,
    page_ranges: str | None,
    extra_formats: list[str] | None,
) -> dict[str, Any]:
    file_item: dict[str, Any] = {
        "name": input_path.name,
        "data_id": _safe_data_id(input_path.stem),
    }
    if model_version != "MinerU-HTML":
        file_item["is_ocr"] = method == "ocr"
        if page_ranges:
            file_item["page_ranges"] = page_ranges

    payload: dict[str, Any] = {"files": [file_item], "model_version": model_version}
    if model_version != "MinerU-HTML":
        payload.update(
            {
                "language": lang,
                "enable_table": bool(enable_table),
                "enable_formula": bool(enable_formula),
            }
        )
        clean_formats = [item for item in (extra_formats or []) if item in {"docx", "html", "latex"}]
        if clean_formats:
            payload["extra_formats"] = clean_formats
    return payload


def _safe_data_id(value: str) -> str:
    data_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._-")
    return (data_id or "document")[:128]


def _select_precise_extract_result(raw_result: Any, filename: str) -> dict[str, Any]:
    if isinstance(raw_result, list):
        for item in raw_result:
            if isinstance(item, dict) and item.get("file_name") == filename:
                return item
        for item in raw_result:
            if isinstance(item, dict):
                return item
        return {}
    if isinstance(raw_result, dict):
        return raw_result
    return {}


def _extract_zip(zip_path: Path, extract_dir: Path) -> None:
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            target = (extract_dir / member.filename).resolve()
            if not target.is_relative_to(extract_dir.resolve()):
                raise RuntimeError(f"Unsafe zip member path: {member.filename}")
        archive.extractall(extract_dir)


def _find_precise_artifacts(extract_dir: Path, stem: str) -> ParseArtifacts:
    def first(*patterns: str) -> Path | None:
        matches: list[Path] = []
        for pattern in patterns:
            matches.extend(sorted(extract_dir.rglob(pattern)))
        return matches[0] if matches else None

    markdown_path = first("full.md", "*.md")
    content_list_path = first("*content_list.json", "content_list.json")
    middle_json_path = first("*middle.json", "middle.json", "layout.json")
    model_json_path = first("*model.json", "model.json")
    return ParseArtifacts(
        markdown_path=markdown_path,
        content_list_path=content_list_path,
        middle_json_path=middle_json_path,
        model_json_path=model_json_path,
        layout_pdf_path=first("*layout.pdf"),
        span_pdf_path=first("*span.pdf"),
        origin_pdf_path=first("*origin.pdf"),
        image_dir=first("images") if first("images") and first("images").is_dir() else None,
    )


def _env_list(name: str) -> list[str]:
    raw = os.getenv(name, "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def _load_api_json(response: httpx.Response, action: str) -> dict[str, Any]:
    try:
        data = response.json()
    except ValueError as exc:
        raise RuntimeError(f"MinerU API returned non-JSON while trying to {action}.") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"MinerU API returned unexpected payload while trying to {action}: {data!r}")
    return data


def _ensure_api_success(data: dict[str, Any], action: str) -> None:
    if data.get("code") != 0:
        raise RuntimeError(f"MinerU API could not {action}: {data.get('msg') or data}")


def _markdown_to_content_blocks(markdown: str, *, source: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    lines = markdown.splitlines()
    index = 0

    def append_block(block_type: str, text: str) -> None:
        clean = text.strip()
        if clean:
            blocks.append({"type": block_type, "text": clean, "block_idx": len(blocks), "source": source})

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped:
            index += 1
            continue

        if _looks_like_markdown_heading(stripped):
            append_block("heading", stripped)
            index += 1
            continue

        if _looks_like_html_table_start(stripped):
            table_lines = [line]
            index += 1
            if "</table" not in stripped.lower():
                while index < len(lines):
                    table_lines.append(lines[index])
                    if "</table" in lines[index].lower():
                        index += 1
                        break
                    index += 1
            append_block("table", "\n".join(table_lines))
            continue

        if _starts_markdown_table(lines, index):
            table_lines = [line]
            index += 1
            while index < len(lines) and _is_markdown_table_line(lines[index]):
                table_lines.append(lines[index])
                index += 1
            append_block("table", "\n".join(table_lines))
            continue

        if _looks_like_markdown_list(stripped):
            list_lines = [line]
            index += 1
            while index < len(lines):
                next_stripped = lines[index].strip()
                if not next_stripped:
                    break
                if not _looks_like_markdown_list(next_stripped):
                    break
                list_lines.append(lines[index])
                index += 1
            append_block("list", "\n".join(list_lines))
            continue

        paragraph_lines = [line]
        index += 1
        while index < len(lines):
            next_line = lines[index]
            next_stripped = next_line.strip()
            if not next_stripped:
                break
            if (
                _looks_like_markdown_heading(next_stripped)
                or _looks_like_html_table_start(next_stripped)
                or _starts_markdown_table(lines, index)
                or _looks_like_markdown_list(next_stripped)
            ):
                break
            paragraph_lines.append(next_line)
            index += 1
        append_block("text", "\n".join(paragraph_lines))
    return blocks


def _tail_json(value: Any) -> str:
    return _redact_sensitive_text(json.dumps(value, ensure_ascii=False, indent=2))[-4000:]


def _looks_like_markdown_heading(text: str) -> bool:
    return bool(re.match(r"^#{1,6}\s+\S+", text))


def _looks_like_html_table_start(text: str) -> bool:
    return bool(re.search(r"<table(?:\s|>|$)", text, flags=re.IGNORECASE))


def _is_markdown_table_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.count("|") >= 2


def _is_markdown_table_separator(line: str) -> bool:
    stripped = line.strip()
    return bool(re.fullmatch(r"\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?", stripped))


def _starts_markdown_table(lines: list[str], index: int) -> bool:
    if index >= len(lines) or not _is_markdown_table_line(lines[index]):
        return False
    if index + 1 < len(lines) and _is_markdown_table_separator(lines[index + 1]):
        return True
    return False


def _looks_like_markdown_list(text: str) -> bool:
    return bool(re.match(r"(?:[-*+]\s+|\d+[.)]\s+)\S+", text))


def _redact_sensitive_text(text: str) -> str:
    clean = text
    clean = re.sub(r"Bearer\s+[A-Za-z0-9._~+/=\-]+", "Bearer ***", clean, flags=re.IGNORECASE)
    clean = re.sub(
        r"((?:api[_-]?key|access[_-]?token|token|secret|signature)=)[^&\s\"']+",
        r"\1***",
        clean,
        flags=re.IGNORECASE,
    )
    clean = re.sub(r"(X-Amz-[A-Za-z0-9_-]+=)[^&\s\"']+", r"\1***", clean, flags=re.IGNORECASE)
    clean = re.sub(
        r"(Authorization:\s*)(?:Bearer\s+)?[A-Za-z0-9._~+/=\-]+",
        r"\1Bearer ***",
        clean,
        flags=re.IGNORECASE,
    )
    return clean
