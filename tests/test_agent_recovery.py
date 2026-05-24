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
    runtime_plan = result.execution_control["runtime_recovery_plan"]
    assert runtime_plan["actions"][0]["action"] == "text_cleanup"
    assert runtime_plan["actions"][0]["runtime_status"] == "executed"
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
    assert result.execution_control["runtime_recovery_plan"]["actions"][0]["action"] == "ocr_retry"
    assert result.execution_control["runtime_recovery_plan"]["actions"][0]["method_change"] == "auto->ocr"
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


def test_llm_preplan_controls_profile_method_and_trace(tmp_path: Path) -> None:
    input_path = tmp_path / "scan.pdf"
    input_path.write_bytes(b"%PDF-1.4\n% scanned")
    runner = _RetryRunner()
    llm = _PreplanningLLM()

    result = MinerUDataAgent(mineru_runner=runner, llm_client=llm).run(
        input_path,
        tmp_path / "runs",
        task="解析低质量扫描 PDF，抽取报告日期并保留质量日志",
        profile="auto",
        method="auto",
    )

    assert runner.methods == ["ocr"]
    assert result.profile == "low_quality_ocr"
    assert "LLM preplan: Force OCR parsing for scanned input" in result.plan
    assert result.execution_control["resolved"]["method"] == "ocr"
    assert result.execution_control["planning_rationale"]["source"] == "llm_preplan+rules"
    assert result.execution_control["agent_action_plan"]["subtasks"][0]["id"] == "understand_task"
    selected_tools = {
        item["name"]
        for item in result.execution_control["agent_action_plan"]["tool_registry"]
        if item["selected"]
    }
    assert {"llm_preplanner", "llm_post_review", "mineru_cli"} <= selected_tools
    assert "OCR" in result.execution_control["planning_rationale"]["profile_reason"]
    assert {"field": "method", "from": "auto", "to": "ocr", "reason": "llm_preplan"} in result.execution_control["applied"]
    assert result.llm_analysis["pre_execution_plan"]["target_schema"]["报告日期"] == "date"
    assert result.llm_analysis["usage_summary"]["total_tokens"] == 430
    assert result.llm_analysis["usage_summary"]["estimated_cost_usd"] == 0.003
    assert result.llm_analysis["quality_decision"]["risk_counts"]["warning"] == 1
    assert result.recovery_decision["decision"] == "accept_with_llm_review_notes"
    assert result.recovery_decision["llm_quality_decision"]["suggested_actions"] == ["keep OCR quality review note"]
    assert result.execution_control["replan_after_quality"]["selected_attempt"] == "initial"
    assert llm.post_parse_profile == "low_quality_ocr"
    trace = json.loads(Path(result.trace_path).read_text(encoding="utf-8"))
    step_names = [step["name"] for step in trace["steps"]]
    assert step_names.index("llm_pre_execution_planning") < step_names.index("mineru_parse")
    assert "agent_task_decomposition" in step_names
    assert "agent_runtime_recovery_plan" in step_names
    assert "agent_replan_after_quality" in step_names
    assert "llm_quality_decision" in step_names
    assert trace["tool_calls"][0]["tool"] == "fake-llm-preplan"
    structured_step = next(step for step in trace["steps"] if step["name"] == "build_structured_view")
    retrieval_step = next(step for step in trace["steps"] if step["name"] == "build_retrieval_export")
    assert structured_step["detail"]["item_count"] >= 1
    assert structured_step["detail"]["page_count"] >= 1
    assert "table_count" in structured_step["detail"]
    assert retrieval_step["detail"]["chunks_count"] >= 1
    assert retrieval_step["detail"]["by_type"]["text"] >= 1


def test_agent_api_no_page_provenance_falls_back_to_cli_attempt(tmp_path: Path) -> None:
    input_path = tmp_path / "contract.pdf"
    input_path.write_bytes(b"%PDF-1.4\n% contract")
    primary = _AgentAPIRunnerNoProvenance()
    fallback = _CLIFallbackRunner()

    result = MinerUDataAgent(mineru_runner=primary, fallback_mineru_runner=fallback).run(
        input_path,
        tmp_path / "runs",
        task="解析合同 PDF，缺少页级 provenance 时自动切换本地 CLI",
        profile="standard_or_contract",
    )

    assert primary.calls == ["auto"]
    assert fallback.calls == ["auto"]
    assert result.quality["status"] == "pass"
    assert result.recovery_decision["executed"] is True
    assert result.recovery_decision["selected_attempt"] == "cli_fallback"
    runtime_actions = result.execution_control["runtime_recovery_plan"]["actions"]
    assert runtime_actions[0]["action"] == "cli_fallback"
    assert runtime_actions[0]["runner_change"] == "agent-api->cli"
    assert result.recovery_decision["attempts"][0]["issue_codes"] == ["no_page_provenance"]
    assert result.recovery_decision["attempts"][1]["quality_status"] == "pass"
    trace = json.loads(Path(result.trace_path).read_text(encoding="utf-8"))
    step = next(item for item in trace["steps"] if item["name"] == "auto_recovery_cli_fallback")
    assert step["detail"]["fallback_quality"]["provenance_level"] == "page"
    assert trace["tool_calls"][0]["tool"] == "fake-agent-api"
    assert trace["tool_calls"][1]["tool"] == "fake-mineru-cli"


def test_strict_page_provenance_marks_unrecovered_pdf_as_partial_result(tmp_path: Path) -> None:
    input_path = tmp_path / "contract.pdf"
    input_path.write_bytes(b"%PDF-1.4\n% contract")
    primary = _AgentAPIRunnerNoProvenance()

    result = MinerUDataAgent(mineru_runner=primary).run(
        input_path,
        tmp_path / "runs",
        task="解析合同 PDF，并要求字段能追溯到页码",
        profile="standard_or_contract",
        strict_page_provenance=True,
    )

    issue_codes = [issue["code"] for issue in result.quality["issues"]]
    assert primary.calls == ["auto"]
    assert result.quality["status"] == "needs_review"
    assert "no_page_provenance" in issue_codes
    assert "strict_page_provenance_failed" in issue_codes
    assert result.execution_control["strict_page_provenance"]["satisfied"] is False
    assert result.execution_control["strict_page_provenance"]["mode"] == "partial_result_returned"
    assert result.recovery_decision["decision"] == "strict_page_provenance_failed"
    assert result.recovery_decision["executed"] is False
    trace = json.loads(Path(result.trace_path).read_text(encoding="utf-8"))
    step = next(item for item in trace["steps"] if item["name"] == "strict_page_provenance_gate")
    assert step["detail"]["failure_code"] == "strict_page_provenance_failed"


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


class _AgentAPIRunnerNoProvenance:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def parse(
        self,
        input_path: Path,
        output_dir: Path,
        *,
        backend: str = "pipeline",
        method: str = "auto",
        lang: str = "ch",
    ) -> tuple[ParseArtifacts, ToolCall]:
        self.calls.append(method)
        base = output_dir / input_path.stem / "agent_api"
        base.mkdir(parents=True, exist_ok=True)
        markdown_path = base / f"{input_path.stem}.md"
        content_path = base / f"{input_path.stem}_content_list.json"
        markdown = "# Contract\n\nContract No: API-ONLY-01\n\n## Risk\n\n" + ("Needs page provenance. " * 20)
        content = [
            {"type": "heading", "text": "# Contract", "source": "mineru-agent-api"},
            {"type": "text", "text": "Contract No: API-ONLY-01", "source": "mineru-agent-api"},
            {"type": "heading", "text": "## Risk", "source": "mineru-agent-api"},
            {"type": "text", "text": "Needs page provenance. " * 20, "source": "mineru-agent-api"},
        ]
        markdown_path.write_text(markdown, encoding="utf-8")
        content_path.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")
        return (
            ParseArtifacts(markdown_path=markdown_path, content_list_path=content_path),
            ToolCall(
                tool="fake-agent-api",
                command=["fake-agent-api", method],
                status="completed",
                elapsed_seconds=0.01,
            ),
        )


class _CLIFallbackRunner:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def parse(
        self,
        input_path: Path,
        output_dir: Path,
        *,
        backend: str = "pipeline",
        method: str = "auto",
        lang: str = "ch",
    ) -> tuple[ParseArtifacts, ToolCall]:
        self.calls.append(method)
        base = output_dir / input_path.stem / "auto"
        base.mkdir(parents=True, exist_ok=True)
        markdown_path = base / f"{input_path.stem}.md"
        content_path = base / f"{input_path.stem}_content_list.json"
        markdown = "# Contract\n\nContract No: CLI-RECOVERED-01\n\n## Scope\n\n" + ("Recovered page-level text. " * 20)
        content = [
            {"type": "heading", "text": "# Contract", "page_idx": 0, "source": "native"},
            {"type": "text", "text": "Contract No: CLI-RECOVERED-01", "page_idx": 0, "source": "native"},
            {"type": "heading", "text": "## Scope", "page_idx": 0, "source": "native"},
            {"type": "text", "text": "Recovered page-level text. " * 20, "page_idx": 0, "source": "native"},
        ]
        markdown_path.write_text(markdown, encoding="utf-8")
        content_path.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")
        return (
            ParseArtifacts(markdown_path=markdown_path, content_list_path=content_path),
            ToolCall(
                tool="fake-mineru-cli",
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


class _PreplanningLLM:
    def __init__(self) -> None:
        self.post_parse_profile = ""

    def plan_execution(self, **kwargs: object) -> tuple[dict, ToolCall]:
        return (
            {
                "enabled": True,
                "status": "completed",
                "task_understanding": "scanned low quality pdf",
                "recommended_profile": "low_quality_ocr",
                "recommended_runner": "cli",
                "recommended_backend": "pipeline",
                "recommended_method": "ocr",
                "recommended_lang": "ch",
                "execution_plan": ["Force OCR parsing for scanned input"],
                "target_schema": {"报告日期": "date"},
                "verification_focus": ["date coverage"],
                "recovery_policy": ["manual review if OCR is sparse"],
                "confidence": 0.9,
                "llm_usage": {
                    "provider": "fake",
                    "model": "fake-preplan",
                    "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
                    "cost_estimate": {"configured": True, "estimated_cost": 0.001, "currency": "USD"},
                },
            },
            ToolCall(
                tool="fake-llm-preplan",
                command=["fake-llm", "preplan"],
                status="completed",
                elapsed_seconds=0.01,
                metadata={"llm_usage": {"usage": {"total_tokens": 150}}},
            ),
        )

    def analyze(self, **kwargs: object) -> tuple[dict, ToolCall]:
        self.post_parse_profile = str(kwargs.get("profile"))
        return (
            {
                "status": "completed",
                "task_understanding": "post parse review",
                "execution_plan": ["review OCR quality"],
                "target_schema": {"报告日期": "date"},
                "verification_focus": ["trace"],
                "risk_findings": [
                    {
                        "level": "warning",
                        "message": "OCR quality should remain reviewable",
                        "evidence": "post-parse quality review",
                    }
                ],
                "recovery_suggestions": ["keep OCR quality review note"],
                "llm_usage": {
                    "provider": "fake",
                    "model": "fake-post",
                    "usage": {"prompt_tokens": 200, "completion_tokens": 80, "total_tokens": 280},
                    "cost_estimate": {"configured": True, "estimated_cost": 0.002, "currency": "USD"},
                },
            },
            ToolCall(
                tool="fake-llm",
                command=["fake-llm", "analyze"],
                status="completed",
                elapsed_seconds=0.01,
                metadata={"llm_usage": {"usage": {"total_tokens": 280}}},
            ),
        )
