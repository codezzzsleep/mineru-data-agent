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
    assert result.schema_version == "2026-05-24"
    assert result.to_jsonable()["schema_version"] == "2026-05-24"
    runtime_plan = result.execution_control["runtime_recovery_plan"]
    assert runtime_plan["actions"][0]["action"] == "text_cleanup"
    assert runtime_plan["actions"][0]["runtime_status"] == "executed"
    assert "possible_mojibake" in result.recovery_decision["initial_issue_codes"]
    assert Path(result.artifacts["markdown_path"]).parts[-3:-1] == ("recovery", "text_cleanup")


def test_born_digital_pdf_uses_local_text_layer_without_mineru(tmp_path: Path, monkeypatch) -> None:
    input_path = tmp_path / "vector.pdf"
    input_path.write_bytes(b"%PDF-1.4")

    def fake_probe(path):
        return 2, True

    def fake_extract(path):
        text = "Local PDF text. " * 20
        return (
            "# Page 1\n\n" + text,
            [{"type": "text", "text": text, "source": "pdf-text-layer", "page_idx": 0}],
            {"page_count": 2, "text_chars": len(text), "has_text_layer": True},
        )

    monkeypatch.setattr("mineru_data_agent.routing.probe_pdf_text_layer", fake_probe)
    monkeypatch.setattr("mineru_data_agent.agent.extract_pdf_text", fake_extract)

    class FailingRunner:
        def parse(self, *args, **kwargs):
            raise AssertionError("MinerU should not be called for a text-layer PDF")

    result = MinerUDataAgent(mineru_runner=FailingRunner(), requested_runner="auto", auto_runner=True).run(
        input_path,
        tmp_path / "runs",
        task="整理 PDF 文本",
    )

    assert result.execution_control["resolved"]["runner"] == "local-pdf-text"
    assert result.extracted["content_summary"]["source_counts"]["pdf-text-layer"] == 1


def test_text_layer_pdf_overrides_unnecessary_llm_precise_api_route(tmp_path: Path, monkeypatch) -> None:
    input_path = tmp_path / "vector.pdf"
    input_path.write_bytes(b"%PDF-1.4")

    def fake_probe(path):
        return 7, True

    def fake_extract(path):
        text = "Born digital PDF text layer. " * 20
        return (
            "# Page 1\n\n" + text,
            [{"type": "text", "text": text, "source": "pdf-text-layer", "page_idx": 0}],
            {"page_count": 7, "text_chars": len(text), "has_text_layer": True},
        )

    class PrecisePreferringLLM:
        def plan_execution(self, **kwargs: object) -> tuple[dict, ToolCall]:
            return (
                {
                    "enabled": True,
                    "status": "completed",
                    "task_understanding": "born digital PDF",
                    "recommended_profile": "general_document",
                    "recommended_runner": "precise-api",
                    "recommended_backend": "pipeline",
                    "recommended_method": "txt",
                    "recommended_lang": "ch",
                    "confidence": 0.9,
                    "llm_usage": {"usage": {"total_tokens": 1}},
                },
                ToolCall(
                    tool="fake-llm-preplan",
                    command=["fake"],
                    status="completed",
                    elapsed_seconds=0.01,
                    metadata={"llm_usage": {"usage": {"total_tokens": 1}}},
                ),
            )

        def analyze(self, **kwargs: object) -> tuple[dict, ToolCall]:
            return (
                {"status": "completed", "risk_findings": [], "llm_usage": {"usage": {"total_tokens": 1}}},
                ToolCall(
                    tool="fake-llm",
                    command=["fake"],
                    status="completed",
                    elapsed_seconds=0.01,
                    metadata={"llm_usage": {"usage": {"total_tokens": 1}}},
                ),
            )

        def build_document_understanding(self, **kwargs: object) -> tuple[dict, ToolCall]:
            return (
                {
                    "status": "completed",
                    "name": "born-digital-pdf",
                    "description": "Born digital PDF text-layer document.",
                    "compressed": "Born digital PDF text-layer document.",
                    "llm_usage": {"usage": {"total_tokens": 1}},
                },
                ToolCall(
                    tool="fake-llm-understanding",
                    command=["fake"],
                    status="completed",
                    elapsed_seconds=0.01,
                    metadata={"llm_usage": {"usage": {"total_tokens": 1}}},
                ),
            )

    class FailingRunner:
        def parse(self, *args, **kwargs):
            raise AssertionError("Precise API should not be called for a text-layer PDF")

    monkeypatch.setattr("mineru_data_agent.routing.probe_pdf_text_layer", fake_probe)
    monkeypatch.setattr("mineru_data_agent.agent.extract_pdf_text", fake_extract)
    monkeypatch.setenv("MINERU_PRECISE_API_TOKEN", "test-token")

    result = MinerUDataAgent(
        mineru_runner=FailingRunner(),
        llm_client=PrecisePreferringLLM(),
        requested_runner="auto",
        auto_runner=True,
    ).run(
        input_path,
        tmp_path / "runs",
        task="summarize this born-digital PDF",
        profile="general_document",
        method="txt",
    )

    assert result.execution_control["resolved"]["runner"] == "local-pdf-text"
    assert result.execution_control["overrides"][0]["to"] == "local-pdf-text"
    assert result.extracted["content_summary"]["source_counts"]["pdf-text-layer"] == 1


def test_complex_layout_text_layer_pdf_uses_layout_aware_parser(tmp_path: Path, monkeypatch) -> None:
    input_path = tmp_path / "two-column.pdf"
    input_path.write_bytes(b"%PDF-1.4")

    def fake_probe(path):
        return 20, True

    def fake_layout(path):
        return {
            "is_complex_layout": True,
            "layout_type": "multi_column",
            "layout_risk": "reading_order_risk",
            "multi_column_pages": 4,
            "sampled_pages": 5,
            "probe_source": "test",
        }

    def fail_extract(path):
        raise AssertionError("complex layout PDF should not use local text extraction as primary parser")

    class RecordingAgentAPIRunner:
        def __init__(self) -> None:
            self.called = False

        def parse(self, input_file, output_dir, **kwargs):
            self.called = True
            output_dir.mkdir(parents=True, exist_ok=True)
            md_path = output_dir / "out.md"
            content_path = output_dir / "out_content_list.json"
            md_path.write_text("# Page 1\n\nLayout-aware parse", encoding="utf-8")
            content_path.write_text(
                json.dumps(
                    [{"type": "text", "text": "Layout-aware parse", "source": "mineru", "page_idx": 0}],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            return (
                ParseArtifacts(markdown_path=md_path, content_list_path=content_path),
                ToolCall(tool="fake-mineru", command=["fake"], status="completed", elapsed_seconds=0.01),
            )

    runner = RecordingAgentAPIRunner()
    monkeypatch.setattr("mineru_data_agent.routing.probe_pdf_text_layer", fake_probe)
    monkeypatch.setattr("mineru_data_agent.routing.probe_pdf_layout_complexity", fake_layout)
    monkeypatch.setattr("mineru_data_agent.agent.extract_pdf_text", fail_extract)

    result = MinerUDataAgent(mineru_runner=runner, requested_runner="auto", auto_runner=True).run(
        input_path,
        tmp_path / "runs",
        task="整理双栏论文",
    )

    assert runner.called is True
    assert result.execution_control["workflow_routing"]["applied_signals"]["is_complex_layout"] is True
    assert result.execution_control["overrides"][0]["to"] == "agent-api"
    assert result.extracted["content_summary"]["source_counts"]["mineru"] == 1


def test_table_text_layer_pdf_records_vlm_and_numeric_check_gate(tmp_path: Path, monkeypatch) -> None:
    input_path = tmp_path / "table.pdf"
    input_path.write_bytes(b"%PDF-1.4")

    def fake_probe(path):
        return 8, True

    def fake_layout(path):
        return {
            "is_complex_layout": False,
            "layout_type": "simple_or_unknown",
            "layout_risk": "low",
            "multi_column_pages": 0,
            "sampled_pages": 5,
            "has_tables": True,
            "table_pages": [2, 3],
            "table_count": 2,
            "table_risk": "table_structure_or_numeric_risk",
            "probe_source": "test",
        }

    def fail_extract(path):
        raise AssertionError("table PDF should not trust local text extraction as primary parser")

    class RecordingPreciseAPIRunner:
        def __init__(self) -> None:
            self.called = False

        def parse(self, input_file, output_dir, **kwargs):
            self.called = True
            output_dir.mkdir(parents=True, exist_ok=True)
            md_path = output_dir / "out.md"
            content_path = output_dir / "out_content_list.json"
            md_path.write_text("# Page 1\n\n| 材料 | 数量 |\n|---|---:|\n| 铜 | 12 |", encoding="utf-8")
            content_path.write_text(
                json.dumps(
                    [{"type": "text", "text": "材料 数量 铜 12", "source": "mineru", "page_idx": 0}],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            return (
                ParseArtifacts(markdown_path=md_path, content_list_path=content_path),
                ToolCall(tool="fake-mineru", command=["fake"], status="completed", elapsed_seconds=0.01),
            )

    runner = RecordingPreciseAPIRunner()
    monkeypatch.setenv("MINERU_PRECISE_API_TOKEN", "test-token")
    monkeypatch.setattr("mineru_data_agent.routing.probe_pdf_text_layer", fake_probe)
    monkeypatch.setattr("mineru_data_agent.routing.probe_pdf_layout_complexity", fake_layout)
    monkeypatch.setattr("mineru_data_agent.agent.extract_pdf_text", fail_extract)

    result = MinerUDataAgent(mineru_runner=runner, requested_runner="auto", auto_runner=True).run(
        input_path,
        tmp_path / "runs",
        task="整理表格资料",
    )

    gate = result.execution_control["harness_gate"]
    assert runner.called is True
    assert gate["initial_decision"] == "local-pdf-text"
    assert "检测到表格页" in gate["reason"]
    actions = {item["action"]: item for item in gate["actions"]}
    assert actions["vlm_table_review"]["backend"] == "vlm-transformers"
    assert actions["ocr_or_text_numeric_check"]["method"] == "ocr_or_text"
    assert actions["ocr_or_text_numeric_check"]["pages"] == [2, 3]


def test_cross_run_memory_recommends_prior_successful_recovery(tmp_path: Path) -> None:
    html_path = tmp_path / "mojibake.html"
    noisy = "锟斤拷" + ("这是一段需要清理但仍可结构化的巡检文本。" * 20)
    html_path.write_text(
        f"<html><body><h1>巡检日报</h1><p>报告日期：2026-05-23</p><p>{noisy}</p></body></html>",
        encoding="utf-8",
    )
    output_root = tmp_path / "runs"
    agent = MinerUDataAgent()

    first = agent.run(
        html_path,
        output_root,
        task="清理网页巡检日报并输出结构化结果",
        profile="general_document",
    )
    second = agent.run(
        html_path,
        output_root,
        task="清理网页巡检日报并输出结构化结果",
        profile="general_document",
    )

    assert first.execution_control["cross_run_memory"]["recommended_actions"] == []
    memory = second.execution_control["cross_run_memory"]
    assert memory["enabled"] is True
    assert memory["recommended_actions"] == ["text_cleanup"]
    assert memory["stats"][0]["action"] == "text_cleanup"
    assert memory["stats"][0]["successes"] == 1
    runtime_plan = second.execution_control["runtime_recovery_plan"]
    assert "text_cleanup" in runtime_plan["memory_recommended_actions"]
    assert any(
        source["source"] == "local_sqlite_memory.recommended_actions"
        for source in runtime_plan["actions"][0].get("additional_sources", [])
    )
    assert (output_root / ".mineru_data_agent" / "memory.sqlite").exists()


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
    assert result.llm_analysis["usage_summary"]["total_tokens"] == 470
    assert result.llm_analysis["usage_summary"]["estimated_cost_usd"] == 0.0035
    assert result.llm_analysis["document_understanding"]["description"] == "Semantic document description"
    skill_package = result.skill_package
    assert skill_package["description_source"] == "llm"
    assert skill_package["has_compressed_view"] is True
    assert skill_package["has_full_content"] is True
    assert Path(skill_package["files"]["compressed"]).exists()
    assert Path(skill_package["files"]["content"]).exists()
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


def test_llm_recovery_suggestion_can_drive_runtime_ocr_retry(tmp_path: Path) -> None:
    input_path = tmp_path / "clean.pdf"
    input_path.write_bytes(b"%PDF-1.4\n% clean")
    runner = _LLMSuggestedRetryRunner()
    llm = _OcrRetrySuggestionLLM()

    result = MinerUDataAgent(mineru_runner=runner, llm_client=llm).run(
        input_path,
        tmp_path / "runs",
        task="解析 PDF，并让复核模型判断是否需要 OCR 复跑",
        profile="general_document",
        method="auto",
    )

    assert runner.methods == ["auto", "ocr"]
    actions = result.execution_control["runtime_recovery_plan"]["actions"]
    assert actions[0]["action"] == "ocr_retry"
    assert actions[0]["source"] == "llm_post_review.recovery_suggestions"
    assert actions[0]["runtime_status"] == "executed"
    assert result.llm_analysis["post_parse_analysis"]["recovery_suggestions"] == ["retry with OCR to verify faint scan"]
    trace = json.loads(Path(result.trace_path).read_text(encoding="utf-8"))
    step_names = [step["name"] for step in trace["steps"]]
    assert step_names.index("llm_agent_analysis") < step_names.index("agent_runtime_recovery_plan")


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


class _LLMSuggestedRetryRunner:
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
        markdown = (
            "# Reviewable PDF\n\n报告日期：2026-05-24\n\n"
            + f"Method {method} produced readable page-level text. "
            + ("The content is complete enough for initial validation. " * 12)
        )
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


class _DocumentUnderstandingMixin:
    def build_document_understanding(self, **kwargs: object) -> tuple[dict, ToolCall]:
        return (
            {
                "status": "completed",
                "name": "semantic-document",
                "description": "Semantic document description",
                "compressed": "This is an LLM-generated compact understanding for progressive loading.",
                "topics": ["topic-a"],
                "entities": ["entity-a"],
                "quality_notes": ["review quality gates"],
                "llm_usage": {
                    "provider": "fake",
                    "model": "fake-understanding",
                    "usage": {"prompt_tokens": 25, "completion_tokens": 15, "total_tokens": 40},
                    "cost_estimate": {"configured": True, "estimated_cost": 0.0005, "currency": "USD"},
                },
            },
            ToolCall(
                tool="fake-llm-document-understanding",
                command=["fake-llm", "document-understanding"],
                status="completed",
                elapsed_seconds=0.01,
                metadata={"llm_usage": {"usage": {"total_tokens": 40}}},
            ),
        )


class _OcrRetrySuggestionLLM(_DocumentUnderstandingMixin):
    def plan_execution(self, **kwargs: object) -> tuple[dict, ToolCall]:
        return (
            {
                "enabled": True,
                "status": "completed",
                "task_understanding": "reviewable pdf",
                "recommended_profile": "general_document",
                "confidence": 0.72,
                "llm_usage": {
                    "provider": "fake",
                    "model": "fake-preplan",
                    "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
                    "cost_estimate": {"configured": True, "estimated_cost": 0.0, "currency": "USD"},
                },
            },
            ToolCall(
                tool="fake-llm-preplan",
                command=["fake-llm", "preplan"],
                status="completed",
                elapsed_seconds=0.01,
                metadata={"llm_usage": {"usage": {"total_tokens": 30}}},
            ),
        )

    def analyze(self, **kwargs: object) -> tuple[dict, ToolCall]:
        return (
            {
                "status": "completed",
                "task_understanding": "post parse review",
                "risk_findings": [],
                "recovery_suggestions": ["retry with OCR to verify faint scan"],
                "llm_usage": {
                    "provider": "fake",
                    "model": "fake-post",
                    "usage": {"prompt_tokens": 30, "completion_tokens": 15, "total_tokens": 45},
                    "cost_estimate": {"configured": True, "estimated_cost": 0.0, "currency": "USD"},
                },
            },
            ToolCall(
                tool="fake-llm",
                command=["fake-llm", "analyze"],
                status="completed",
                elapsed_seconds=0.01,
                metadata={"llm_usage": {"usage": {"total_tokens": 45}}},
            ),
        )


class _PreplanningLLM(_DocumentUnderstandingMixin):
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
