import json
from pathlib import Path

import pytest

from mineru_data_agent.agent import MinerUDataAgent
from mineru_data_agent.mineru_client import MinerUParseError
from mineru_data_agent.models import ParseArtifacts, ToolCall


def test_text_cleanup_recovery_selects_cleaned_attempt(tmp_path: Path) -> None:
    html_path = tmp_path / "mojibake.html"
    noisy = "锟斤拷" + ("这是一段需要清理但仍可结构化的巡检文本。" * 20)
    html_path.write_text(
        f"<html><body><h1>巡检日报</h1><p>报告日期：2026-05-23</p><p>{noisy}</p></body></html>",
        encoding="utf-8",
    )

    result = MinerUDataAgent().run(
        html_path,
        tmp_path / "runs",
        task="清理网页巡检日报并输出结构化结果",
        profile="general_document",
    )

    assert result.quality["status"] == "pass"
    assert result.recovery_decision["decision"] == "recovered_accept"
    assert result.recovery_decision["selected_attempt"] == "text_cleanup"
    assert result.recovery_decision["executed"] is True
    assert "possible_mojibake" in result.recovery_decision["initial_issue_codes"]
    assert Path(result.artifacts["markdown_path"]).parts[-3:-1] == ("recovery", "text_cleanup")


def test_pdf_quality_warning_retries_with_ocr_and_selects_better_attempt(tmp_path: Path) -> None:
    input_path = tmp_path / "sample.pdf"
    input_path.write_bytes(b"%PDF-1.4\n% test")
    runner = _RetryRunner()

    result = MinerUDataAgent(mineru_runner=runner).run(
        input_path,
        tmp_path / "runs",
        task="解析 PDF，输出日期和质量日志",
        profile="general_document",
        method="auto",
    )

    assert runner.methods == ["auto", "ocr"]
    assert result.quality["status"] == "pass"
    assert result.recovery_decision["selected_attempt"] == "ocr_retry"
    assert result.recovery_decision["attempts"][0]["quality_status"] == "pass_with_warnings"
    assert result.recovery_decision["attempts"][1]["quality_status"] == "pass"


def test_failed_parse_writes_trace_file(tmp_path: Path) -> None:
    input_path = tmp_path / "broken.pdf"
    input_path.write_bytes(b"%PDF-1.4\n% broken")

    with pytest.raises(RuntimeError, match="simulated mineru failure"):
        MinerUDataAgent(mineru_runner=_FailingRunner()).run(
            input_path,
            tmp_path / "runs",
            task="解析失败也要保留日志",
        )

    traces = list((tmp_path / "runs").glob("*/trace.json"))
    assert len(traces) == 1
    payload = json.loads(traces[0].read_text(encoding="utf-8"))
    assert payload["status"] == "failed"
    assert "simulated mineru failure" in payload["error"]
    assert payload["steps"][-1]["name"] == "mineru_parse"
    assert payload["steps"][-1]["status"] == "failed"
    assert payload["tool_calls"][0]["tool"] == "fake-mineru"
    assert payload["tool_calls"][0]["status"] == "failed"


def test_ocr_retry_failure_keeps_initial_result_and_audit_record(tmp_path: Path) -> None:
    input_path = tmp_path / "sample.pdf"
    input_path.write_bytes(b"%PDF-1.4\n% retry failure")
    runner = _RetryFailingRunner()

    result = MinerUDataAgent(mineru_runner=runner).run(
        input_path,
        tmp_path / "runs",
        task="解析 PDF，输出日期和质量日志",
        profile="general_document",
        method="auto",
    )

    assert runner.methods == ["auto", "ocr"]
    assert result.quality["status"] == "pass_with_warnings"
    assert result.recovery_decision["selected_attempt"] == "initial"
    assert result.recovery_decision["attempts"][1]["quality_status"] == "failed"
    assert result.recovery_decision["attempts"][1]["issue_codes"] == ["recovery_attempt_failed"]
    trace = json.loads(Path(result.trace_path).read_text(encoding="utf-8"))
    assert trace["status"] == "completed"
    assert trace["tool_calls"][-1]["status"] == "failed"
    retry_step = next(step for step in trace["steps"] if step["name"] == "auto_recovery_ocr_retry")
    assert "recovery_error" in retry_step["detail"]


class _RetryRunner:
    def __init__(self) -> None:
        self.methods: list[str] = []

    def parse(
        self,
        input_path: Path,
        output_dir: Path,
        *,
        backend: str = "pipeline",
        method: str = "auto",
        lang: str = "ch",
    ) -> tuple[ParseArtifacts, ToolCall]:
        self.methods.append(method)
        base = output_dir / input_path.stem / method
        base.mkdir(parents=True, exist_ok=True)
        markdown_path = base / f"{input_path.stem}.md"
        content_path = base / f"{input_path.stem}_content_list.json"
        if method == "ocr":
            markdown = "# OCR Recovery\n\n报告日期：2026-05-23\n\n" + ("恢复后文本包含足够内容和页级证据。" * 20)
            content = [{"type": "text", "text": markdown, "page_idx": 0, "source": "native"}]
        else:
            markdown = "too short"
            content = [{"type": "text", "text": markdown, "page_idx": 0, "source": "native"}]
        markdown_path.write_text(markdown, encoding="utf-8")
        content_path.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")
        return (
            ParseArtifacts(markdown_path=markdown_path, content_list_path=content_path),
            ToolCall(
                tool="fake-mineru",
                command=["fake-mineru", method],
                status="completed",
                elapsed_seconds=0.01,
            ),
        )


class _FailingRunner:
    def parse(
        self,
        input_path: Path,
        output_dir: Path,
        *,
        backend: str = "pipeline",
        method: str = "auto",
        lang: str = "ch",
    ) -> tuple[ParseArtifacts, ToolCall]:
        call = ToolCall(
            tool="fake-mineru",
            command=["fake-mineru", method],
            status="failed",
            elapsed_seconds=0.01,
            stderr_tail="simulated mineru failure",
        )
        raise MinerUParseError("simulated mineru failure", call)


class _RetryFailingRunner(_RetryRunner):
    def parse(
        self,
        input_path: Path,
        output_dir: Path,
        *,
        backend: str = "pipeline",
        method: str = "auto",
        lang: str = "ch",
    ) -> tuple[ParseArtifacts, ToolCall]:
        if method == "ocr":
            self.methods.append(method)
            call = ToolCall(
                tool="fake-mineru",
                command=["fake-mineru", method],
                status="failed",
                elapsed_seconds=0.01,
                stderr_tail="simulated OCR retry failure",
            )
            raise MinerUParseError("simulated OCR retry failure", call)
        return super().parse(input_path, output_dir, backend=backend, method=method, lang=lang)
