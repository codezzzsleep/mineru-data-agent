from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from time import perf_counter
from typing import Any

import httpx

from .models import ParseArtifacts, ToolCall


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
            call = ToolCall(
                tool="mineru-agent-api",
                command=command,
                status="failed",
                elapsed_seconds=elapsed,
                stdout_tail=_tail_json(events),
                stderr_tail=str(exc)[-4000:],
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
                        "error": str(exc)[-500:],
                    }
                )
                time.sleep(self.retry_backoff_seconds * (attempt + 1))
        raise RuntimeError(f"unreachable retry state while trying to {action}")


def _build_page_range(start_page: int | None, end_page: int | None) -> str | None:
    if start_page is None and end_page is None:
        return None
    if start_page is not None and end_page is not None:
        return f"{start_page}-{end_page}"
    return str(start_page or end_page)


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
    for index, paragraph in enumerate(markdown.split("\n\n")):
        text = paragraph.strip()
        if not text:
            continue
        blocks.append({"type": "text", "text": text, "block_idx": index, "source": source})
    return blocks


def _tail_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)[-4000:]
