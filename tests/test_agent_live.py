from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from mineru_data_agent import agent_live


RUNNER_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_agent_live_cases.py"
SPEC = importlib.util.spec_from_file_location("run_agent_live_cases", RUNNER_SCRIPT)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_clean_text_tool_updates_markdown_and_content_list(tmp_path: Path) -> None:
    state = agent_live.AgentState(input_path=tmp_path / "input.html", output_dir=tmp_path)
    state.parses["html"] = {
        "markdown": "设备 B-17 锟斤拷 温度异常",
        "content_list": [{"text": "设备 B-17 锟斤拷 温度异常"}],
    }

    result = agent_live._tool_clean_text(state)

    assert result["ok"] is True
    assert "锟斤拷" not in state.parses["html"]["markdown"]
    assert "锟斤拷" not in state.parses["html"]["content_list"][0]["text"]
    assert state.extracted is None
    assert state.quality is None



def test_resolve_path_defaults_to_input_file(tmp_path: Path) -> None:
    input_path = tmp_path / "input.html"
    input_path.write_text("<html></html>", encoding="utf-8")
    state = agent_live.AgentState(input_path=input_path, output_dir=tmp_path)

    assert agent_live._resolve_path(None, state) == input_path.resolve()



def test_resolve_path_allows_relative_file_under_input_directory(tmp_path: Path) -> None:
    input_path = tmp_path / "input.html"
    related_path = tmp_path / "related.html"
    input_path.write_text("<html></html>", encoding="utf-8")
    related_path.write_text("<html></html>", encoding="utf-8")
    state = agent_live.AgentState(input_path=input_path, output_dir=tmp_path)

    assert agent_live._resolve_path("related.html", state) == related_path.resolve()



def test_resolve_path_rejects_absolute_file_outside_input_directory(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    outside_dir = tmp_path / "outside"
    input_dir.mkdir()
    outside_dir.mkdir()
    input_path = input_dir / "input.html"
    outside_path = outside_dir / "secret.html"
    input_path.write_text("<html></html>", encoding="utf-8")
    outside_path.write_text("secret", encoding="utf-8")
    state = agent_live.AgentState(input_path=input_path, output_dir=tmp_path)

    with pytest.raises(ValueError, match="outside allowed input directory"):
        agent_live._resolve_path(str(outside_path), state)



def test_resolve_path_rejects_parent_traversal(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    input_path = input_dir / "input.html"
    outside_path = tmp_path / "secret.html"
    input_path.write_text("<html></html>", encoding="utf-8")
    outside_path.write_text("secret", encoding="utf-8")
    state = agent_live.AgentState(input_path=input_path, output_dir=tmp_path)

    with pytest.raises(ValueError, match="outside allowed input directory"):
        agent_live._resolve_path("../secret.html", state)


def test_post_chat_normalizes_base_url(monkeypatch) -> None:
    captured: dict[str, str] = {}

    class _Response:
        status_code = 200
        text = "{}"

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"choices": [{"message": {"content": "ok"}}], "usage": {"total_tokens": 1}}

    def fake_post(url: str, **kwargs):
        captured["url"] = url
        return _Response()

    monkeypatch.setattr(agent_live.httpx, "post", fake_post)

    agent_live._post_chat(
        api_key="test-key",
        base_url="https://api.deepseek.com",
        model="deepseek-v4-flash",
        messages=[{"role": "user", "content": "hi"}],
        tools=[],
        max_tokens=10,
        timeout=1,
    )

    assert captured["url"] == "https://api.deepseek.com/v1/chat/completions"


def test_parse_pdf_tool_uses_requested_precise_runner(tmp_path: Path) -> None:
    input_path = tmp_path / "input.pdf"
    input_path.write_bytes(b"%PDF-1.4")
    markdown_path = tmp_path / "out" / "input.md"
    content_path = tmp_path / "out" / "input_content_list.json"
    markdown_path.parent.mkdir()
    markdown_path.write_text("PDF text", encoding="utf-8")
    content_path.write_text('[{"type":"text","text":"PDF text"}]', encoding="utf-8")

    class FakeRunner:
        def parse(self, **kwargs):
            from mineru_data_agent.models import ParseArtifacts, ToolCall

            return (
                ParseArtifacts(markdown_path=markdown_path, content_list_path=content_path),
                ToolCall(
                    tool="mineru-precise-api",
                    command=["fake"],
                    status="completed",
                    elapsed_seconds=0.01,
                ),
            )

    state = agent_live.AgentState(input_path=input_path, output_dir=tmp_path / "run")
    result = agent_live._tool_parse_pdf(
        state,
        {"precise-api": FakeRunner()},
        parser="precise-api",
        backend="vlm-transformers",
    )

    assert result["ok"] is True
    assert result["parser"] == "precise-api"
    assert result["backend"] == "vlm-transformers"
    assert result["mineru_tool"] == "mineru-precise-api"
    assert state.parses["pdf"]["parser"] == "precise-api"


def test_parse_pdf_tool_passes_page_range_to_online_runner(tmp_path: Path) -> None:
    input_path = tmp_path / "input.pdf"
    input_path.write_bytes(b"%PDF-1.4")
    markdown_path = tmp_path / "out" / "input.md"
    content_path = tmp_path / "out" / "input_content_list.json"
    markdown_path.parent.mkdir()
    markdown_path.write_text("PDF page text", encoding="utf-8")
    content_path.write_text('[{"type":"text","text":"PDF page text"}]', encoding="utf-8")
    captured: dict[str, object] = {}

    class FakeRunner:
        def parse(self, **kwargs):
            from mineru_data_agent.models import ParseArtifacts, ToolCall

            captured.update(kwargs)
            return (
                ParseArtifacts(markdown_path=markdown_path, content_list_path=content_path),
                ToolCall(
                    tool="mineru-precise-api",
                    command=["fake"],
                    status="completed",
                    elapsed_seconds=0.01,
                ),
            )

    state = agent_live.AgentState(input_path=input_path, output_dir=tmp_path / "run")
    result = agent_live._tool_parse_pdf(
        state,
        {"precise-api": FakeRunner()},
        parser="precise-api",
        start_page=3,
        end_page=5,
    )

    assert result["ok"] is True
    assert captured["start_page"] == 3
    assert captured["end_page"] == 5
    assert result["start_page"] == 3
    assert result["end_page"] == 5


def test_parse_pdf_tool_blocks_local_text_layer_when_runtime_gate_fires(tmp_path: Path, monkeypatch) -> None:
    input_path = tmp_path / "table.pdf"
    input_path.write_bytes(b"%PDF-1.4")
    markdown_path = tmp_path / "out" / "table.md"
    content_path = tmp_path / "out" / "table_content_list.json"
    markdown_path.parent.mkdir()
    markdown_path.write_text("table text", encoding="utf-8")
    content_path.write_text('[{"type":"text","text":"table text"}]', encoding="utf-8")

    monkeypatch.setattr(
        agent_live,
        "build_input_metadata",
        lambda path: {
            "suffix": ".pdf",
            "page_count": 8,
            "has_text_layer": True,
            "is_complex_layout": False,
            "layout_type": "simple_or_unknown",
            "layout_risk": "low",
            "has_tables": True,
            "table_pages": [2, 3],
            "table_count": 2,
            "table_risk": "table_structure_or_numeric_risk",
        },
    )
    monkeypatch.setenv("MINERU_PRECISE_API_TOKEN", "test-token")

    class FakeRunner:
        def parse(self, **kwargs):
            from mineru_data_agent.models import ParseArtifacts, ToolCall

            return (
                ParseArtifacts(markdown_path=markdown_path, content_list_path=content_path),
                ToolCall(
                    tool="mineru-precise-api",
                    command=["fake"],
                    status="completed",
                    elapsed_seconds=0.01,
                ),
            )

    state = agent_live.AgentState(input_path=input_path, output_dir=tmp_path / "run", default_pdf_parser="local")
    result = agent_live._tool_parse_pdf(
        state,
        {"precise-api": FakeRunner()},
        parser="auto",
    )

    assert result["ok"] is True
    assert result["parser"] == "precise-api"
    assert result["backend"] == "vlm-transformers"
    assert result["harness_gate"]["blocked"] is True
    assert result["harness_gate"]["initial_decision"] == "local-pdf-text"
    assert "表格页" in result["harness_gate"]["reason"]
    assert state.runtime_harness_events[0]["target"] == "precise-api"


def test_parse_url_tool_routes_online_html_to_precise_mineru_html(tmp_path: Path, monkeypatch) -> None:
    captured: dict[str, object] = {}
    markdown_path = tmp_path / "runner" / "doc.md"
    content_path = tmp_path / "runner" / "doc_content_list.json"

    class FakeResponse:
        headers = {"content-type": "text/html; charset=utf-8"}
        content = b"<html><body>online html</body></html>"

        def raise_for_status(self) -> None:
            return None

    class FakeRunner:
        def parse(self, **kwargs):
            from mineru_data_agent.models import ParseArtifacts, ToolCall

            captured.update(kwargs)
            markdown_path.parent.mkdir(parents=True, exist_ok=True)
            markdown_path.write_text("Online HTML parsed by MinerU-HTML", encoding="utf-8")
            content_path.write_text('[{"type":"text","text":"Online HTML parsed by MinerU-HTML"}]', encoding="utf-8")
            return (
                ParseArtifacts(markdown_path=markdown_path, content_list_path=content_path),
                ToolCall(
                    tool="mineru-precise-api",
                    command=["fake"],
                    status="completed",
                    elapsed_seconds=0.01,
                ),
            )

    monkeypatch.setattr(agent_live.httpx, "get", lambda *args, **kwargs: FakeResponse())

    state = agent_live.AgentState(output_dir=tmp_path / "run", workspace_root=tmp_path)
    result = agent_live._tool_parse_url(
        state,
        {"precise-api": FakeRunner()},
        url="https://example.com/source.html",
        parser="precise-api",
    )

    assert result["ok"] is True
    assert result["backend"] == "MinerU-HTML"
    assert result["parser"] == "precise-api"
    assert captured["backend"] == "pipeline"
    assert Path(captured["input_path"]).suffix == ".html"
    assert state.parses["url"]["backend"] == "MinerU-HTML"
    assert state.parses["url"]["markdown"] == "Online HTML parsed by MinerU-HTML"


def test_plan_escalation_tool_recommends_focused_vlm_and_ocr_chunks(tmp_path: Path) -> None:
    state = agent_live.AgentState(input_path=tmp_path / "scan.pdf", output_dir=tmp_path)
    state.extracted = {
        "content_summary": {"page_count": 8, "page_indices": [0, 1, 2, 3, 4, 5, 6, 7]},
        "tables": [{"page": 4, "headers": ["A"], "rows": [["1"]]}],
    }
    state.quality = {
        "issues": [
            {"code": "short_text", "level": "warning"},
            {"code": "numeric_total_mismatch", "level": "warning"},
        ]
    }

    result = agent_live._tool_plan_escalation(state)

    actions = {item["action"]: item for item in result["actions"]}
    assert result["ok"] is True
    assert actions["ocr_pipeline_retry"]["method"] == "ocr"
    assert actions["vlm_region_or_page_retry"]["backend"] == "vlm-transformers"
    assert actions["vlm_region_or_page_retry"]["pages"] == [4]
    assert "fine_grained_escalation_plan" in state.notes[-1]


def test_compare_parsers_tool_flags_vlm_disagreement_as_hallucination_risk(tmp_path: Path) -> None:
    state = agent_live.AgentState(input_path=tmp_path / "doc.pdf", output_dir=tmp_path)
    state.parses["pdf"] = {
        "markdown": "archive source says cotton exports were 1200 tons in 1931",
        "content_list": [],
        "parser": "local-text-layer",
    }

    result = agent_live._tool_compare_parsers(
        state,
        candidate_parser="mineru-vlm",
        candidate_text="fictional railway revenue was 9988 yuan in 1949",
    )

    assert result["ok"] is True
    assert result["status"] == "needs_review"
    assert result["hallucination_risks"][0]["parser"] == "mineru-vlm"
    assert state.consistency == {key: value for key, value in result.items() if key != "ok"}
    assert "vlm_hallucination_risk_detected" in state.notes


def test_run_live_agent_writes_result_json_with_unified_schema(tmp_path: Path, monkeypatch) -> None:
    input_path = tmp_path / "input.html"
    input_path.write_text("<html><body>ok</body></html>", encoding="utf-8")
    calls = iter(
        [
            (
                "select_skill",
                '{"skill_id":"structured_extraction","reason":"simple HTML smoke","plan":["validate answer then finalize"]}',
            ),
            (
                "parse_html",
                "{}",
            ),
            (
                "validate_answer",
                '{"answer":"ok","evidence":["input contained ok"],"claims":["ok"]}',
            ),
            (
                "finalize",
                '{"answer":"ok","evidence":["input contained ok"]}',
            ),
        ]
    )

    def fake_post_chat(**kwargs):
        name, arguments = next(calls)
        return {
            "choices": [
                {
                    "message": {
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": name,
                                    "arguments": arguments,
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5},
        }

    monkeypatch.setattr(agent_live, "_post_chat", fake_post_chat)

    trace = agent_live.run_live_agent(
        input_file=input_path,
        output_root=tmp_path / "runs",
        task="answer directly",
        provider="deepseek",
        api_key="test-key",
        max_turns=4,
    )

    result_path = Path(trace.output_dir) / "result.json"
    data = __import__("json").loads(result_path.read_text(encoding="utf-8"))
    assert data["agent_mode"] == "live_tool_calling"
    assert data["status"] == "completed"
    assert data["tool_call_completed"] is True
    assert data["answer_quality_pass"] is None
    assert data["quality_review"]["status"] == "tool_validated_unreviewed"
    assert data["final_answer"] == "ok"
    assert data["tool_sequence"] == ["select_skill", "parse_html", "validate_answer", "finalize"]
    assert data["selected_skill"]["skill_id"] == "structured_extraction"
    assert data["answer_validation"]["ok"] is True
    assert data["answer_validation"]["answer_full"] == "ok"
    assert data["answer_validation"]["evidence_full"] == ["input contained ok"]
    assert data["autonomy_controls"]["mode"] == "skill_guided_tool_calling"
    assert Path(trace.output_dir, "live_agent_trace.json").exists()
    assert Path(trace.output_dir, "live_agent_summary.md").exists()


def test_finalize_requires_prior_answer_validation(tmp_path: Path) -> None:
    state = agent_live.AgentState(input_path=tmp_path / "input.html", output_dir=tmp_path)

    result = agent_live._tool_finalize(state, answer="ok", evidence=["x"])

    assert result["ok"] is False
    assert result["required_tool"] == "validate_answer"


def test_run_live_agent_harness_finalizes_after_validated_answer(tmp_path: Path, monkeypatch) -> None:
    input_path = tmp_path / "input.html"
    input_path.write_text("<html><body>ok</body></html>", encoding="utf-8")
    calls = iter(
        [
            (
                "select_skill",
                '{"skill_id":"structured_extraction","reason":"simple HTML smoke"}',
            ),
            (
                "parse_html",
                "{}",
            ),
            (
                "validate_answer",
                '{"answer":"ok","evidence":["ok"],"claims":["ok"]}',
            ),
        ]
    )

    def fake_post_chat(**kwargs):
        name, arguments = next(calls)
        return {
            "choices": [
                {
                    "message": {
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {"name": name, "arguments": arguments},
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }

    monkeypatch.setattr(agent_live, "_post_chat", fake_post_chat)

    trace = agent_live.run_live_agent(
        input_file=input_path,
        output_root=tmp_path / "runs",
        task="answer directly",
        provider="deepseek",
        api_key="test-key",
        max_turns=3,
    )

    assert trace.status == "completed"
    assert trace.final_answer == "ok"
    assert trace.final_evidence == ["ok"]
    assert "harness_assisted_finalize_after_validated_answer" in trace.to_jsonable()["notes"]


def test_run_live_agent_summarizes_when_model_loops_after_parse(tmp_path: Path, monkeypatch) -> None:
    input_path = tmp_path / "input.html"
    input_path.write_text("<html><body><h1>Title</h1><p>alpha beta</p></body></html>", encoding="utf-8")
    calls = iter(
        [
            ("select_skill", '{"skill_id":"structured_extraction","reason":"simple HTML smoke"}'),
            ("parse_html", "{}"),
            ("build_extracted", "{}"),
            ("validate_quality", '{"profile":"general_document","task":"parse"}'),
            ("query_extracted", '{"query":"alpha"}'),
            ("query_extracted", '{"query":"beta"}'),
        ]
    )

    monkeypatch.setattr(agent_live, "_post_chat", _fake_tool_sequence(calls))

    trace = agent_live.run_live_agent(
        input_file=input_path,
        output_root=tmp_path / "runs",
        task="parse only",
        provider="deepseek",
        api_key="test-key",
        max_turns=6,
    )

    assert trace.status == "completed"
    assert "文档解析已完成" in (trace.final_answer or "")
    assert "harness_assisted_finalize_after_parse_summary" in trace.to_jsonable()["notes"]


def test_dispatch_requires_skill_before_tool_use(tmp_path: Path) -> None:
    input_path = tmp_path / "input.html"
    input_path.write_text("<html><body>ok</body></html>", encoding="utf-8")
    state = agent_live.AgentState(input_path=input_path, output_dir=tmp_path)

    result = agent_live._dispatch_tool("parse_html", {}, state=state, runner=object())

    assert result["ok"] is False
    assert result["error"] == "select_skill_required_before_tool_use"
    assert result["required_tool"] == "select_skill"


def test_validate_answer_requires_parse_after_skill(tmp_path: Path) -> None:
    input_path = tmp_path / "input.html"
    input_path.write_text("<html><body>ok</body></html>", encoding="utf-8")
    state = agent_live.AgentState(input_path=input_path, output_dir=tmp_path)
    agent_live._tool_select_skill(state, skill_id="structured_extraction", reason="test")

    result = agent_live._dispatch_tool(
        "validate_answer",
        {"answer": "ok", "evidence": ["input contained ok"]},
        state=state,
        runner=object(),
    )

    assert result["ok"] is False
    assert result["error"] == "parse_required_before_answer_validation"


def test_finalize_requires_exact_answer_and_evidence_fingerprint(tmp_path: Path) -> None:
    input_path = tmp_path / "input.html"
    input_path.write_text("<html><body>alpha beta</body></html>", encoding="utf-8")
    state = agent_live.AgentState(input_path=input_path, output_dir=tmp_path)
    agent_live._tool_select_skill(state, skill_id="structured_extraction", reason="test")
    agent_live._tool_parse_html(state)
    validation = agent_live._tool_validate_answer(
        state,
        answer="alpha beta",
        evidence=["alpha"],
        claims=["alpha"],
    )
    assert validation["ok"] is True

    changed_answer = agent_live._tool_finalize(state, answer="alpha beta changed", evidence=["alpha"])
    changed_evidence = agent_live._tool_finalize(state, answer="alpha beta", evidence=["beta"])

    assert changed_answer["ok"] is False
    assert changed_answer["required_tool"] == "validate_answer"
    assert changed_evidence["ok"] is False
    assert changed_evidence["required_tool"] == "validate_answer"


def test_validate_answer_flags_self_contradictory_arithmetic(tmp_path: Path) -> None:
    input_path = tmp_path / "input.html"
    state = agent_live.AgentState(input_path=input_path, output_dir=tmp_path)
    state.parses["html"] = {
        "markdown": "Product 12860.50 Service 8430.25 Other 615.30 Tax 781.20 Profit 3033.75 Total 25721.00",
        "content_list": [],
    }
    agent_live._tool_select_skill(state, skill_id="financial_total_audit", reason="test")

    result = agent_live._tool_validate_answer(
        state,
        answer="合计行（25,721.00）不等于明细项之和（12,860.50 + 8,430.25 + 615.30 + 781.20 + 3,033.75 = 25,721.00），但计算一致。",
        evidence=["financial table"],
    )

    assert result["ok"] is False
    assert any(issue["code"] == "self_contradictory_arithmetic" for issue in result["blocking_issues"])


def test_validate_answer_flags_contract_not_found_conflict(tmp_path: Path) -> None:
    input_path = tmp_path / "contract.html"
    state = agent_live.AgentState(input_path=input_path, output_dir=tmp_path)
    state.parses["html"] = {
        "markdown": "服务范围：乙方应当提供数据安全服务。验收标准：甲方需在五日内确认。",
        "content_list": [],
    }
    agent_live._tool_select_skill(state, skill_id="contract_clause_review", reason="test")

    result = agent_live._tool_validate_answer(
        state,
        answer="not_found: 文档中未明确列出甲方或乙方的义务条款。",
        evidence=["searched 甲方/乙方/义务"],
        claims=["甲方", "乙方", "义务"],
    )

    assert result["ok"] is False
    assert any(issue["code"] == "potential_not_found_conflict" for issue in result["blocking_issues"])


def test_validate_answer_allows_not_found_query_numbers_when_search_recorded(tmp_path: Path) -> None:
    input_path = tmp_path / "financial.html"
    state = agent_live.AgentState(input_path=input_path, output_dir=tmp_path)
    state.parses["html"] = {
        "markdown": "2026Q1 revenue 12860.50. 2025Q4 revenue 11320.20.",
        "content_list": [],
    }
    agent_live._tool_select_skill(state, skill_id="not_found_guard", reason="missing quarter")

    result = agent_live._tool_validate_answer(
        state,
        answer="not_found: 文档中没有 2025Q3 的营业收入。实际包含 2026Q1 和 2025Q4。",
        evidence=["searched 2025Q3; found 2026Q1 and 2025Q4"],
        claims=["2025Q3", "2026Q1", "2025Q4"],
    )

    assert result["ok"] is True
    assert not any(issue["code"] == "unsupported_numbers" for issue in result["blocking_issues"])


def test_summary_counts_only_completed_finalize_token_cases() -> None:
    rows = [
        {"status": "completed", "tokens": 12, "turns": 3, "duration_seconds": 1.0, "tool_sequence": ["parse_html", "finalize"]},
        {"status": "completed", "tokens": 0, "turns": 1, "duration_seconds": 0.1, "tool_sequence": []},
        {"status": "max_turns_exceeded", "tokens": 50, "turns": 18, "duration_seconds": 3.0, "tool_sequence": ["query_extracted"]},
    ]

    summary = runner._summary(rows)

    assert summary["total"] == 3
    assert summary["live_evidence_cases"] == 1
    assert summary["tool_call_completed_cases"] == 1
    assert summary["tool_validated_cases"] == 0
    assert summary["answer_quality_pass_cases"] == 0
    assert summary["answer_quality_unreviewed_cases"] == 1
    assert summary["completed_status"] == 2
    assert summary["failed_or_incomplete"] == 2


def test_report_markdown_marks_incomplete_cases_as_non_evidence() -> None:
    rows = [
        {
            "id": "ok",
            "difficulty": "done",
            "status": "completed",
            "tokens": 12,
            "turns": 3,
            "duration_seconds": 1.0,
            "tool_sequence": ["parse_html", "finalize"],
            "task": "task",
            "final_answer_preview": "answer",
            "trace_path": "trace.json",
            "summary_path": "summary.md",
            "error": None,
        },
        {
            "id": "bad",
            "difficulty": "empty",
            "status": "assistant_answer_without_finalize",
            "tokens": 0,
            "turns": 1,
            "duration_seconds": 0.1,
            "tool_sequence": [],
            "task": "task",
            "final_answer_preview": "",
            "trace_path": "trace.json",
            "summary_path": "summary.md",
            "error": None,
        },
    ]

    markdown = runner._render_markdown(rows)

    assert "Tool-call completed cases: **1**" in markdown
    assert "Tool-validated cases: **0**" in markdown
    assert "Answer-quality pass cases: **0**" in markdown
    assert "| 2 | `bad` | `-` | empty | false | false | unreviewed | assistant_answer_without_finalize" in markdown


def _fake_tool_sequence(calls):
    def fake_post_chat(**kwargs):
        name, arguments = next(calls)
        return {
            "choices": [
                {
                    "message": {
                        "content": "",
                        "tool_calls": [
                            {"id": "c", "type": "function", "function": {"name": name, "arguments": arguments}}
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
        }

    return fake_post_chat


def _new_session(tmp_path: Path, input_path: Path | None = None) -> "agent_live.LiveAgentSession":
    return agent_live.LiveAgentSession(
        output_dir=tmp_path / "out",
        provider="deepseek",
        model="m",
        api_key="k",
        base_url="https://api.deepseek.com/v1",
        max_turns=8,
        max_tokens=256,
        timeout=1,
        runners=agent_live._build_live_mineru_runners(None),
        workspace_root=tmp_path,
        input_path=input_path,
    )


def test_live_session_reuses_parse_across_sends(tmp_path: Path, monkeypatch) -> None:
    input_path = tmp_path / "doc.html"
    input_path.write_text("<html><body>alpha beta gamma</body></html>", encoding="utf-8")
    calls = iter(
        [
            # send #1: parse + extract + finalize
            ("select_skill", '{"skill_id":"structured_extraction","reason":"smoke"}'),
            ("parse_html", "{}"),
            ("build_extracted", "{}"),
            ("validate_answer", '{"answer":"alpha","evidence":["alpha"]}'),
            ("finalize", '{"answer":"alpha","evidence":["alpha"]}'),
            # send #2: must reuse prior parse/extract (no parse_html again)
            ("query_extracted", '{"query":"alpha"}'),
            ("validate_answer", '{"answer":"beta","evidence":["beta"]}'),
            ("finalize", '{"answer":"beta","evidence":["beta"]}'),
        ]
    )
    monkeypatch.setattr(agent_live, "_post_chat", _fake_tool_sequence(calls))

    session = _new_session(tmp_path, input_path)
    first = session.send("extract alpha")
    assert first["status"] == "completed"
    parse_obj = session.state.parses.get("html")
    assert parse_obj is not None

    second = session.send("now answer beta from the same document")
    assert second["status"] == "completed"
    # Hard state reuse: the second turn did NOT re-parse the document.
    assert session.state.parses.get("html") is parse_obj
    send2_tools = [t.tool_call["name"] for t in session.trace.turns if t.tool_call][-3:]
    assert "parse_html" not in send2_tools


def test_live_session_interrupt_returns_and_keeps_session(tmp_path: Path, monkeypatch) -> None:
    input_path = tmp_path / "doc.html"
    input_path.write_text("<html><body>ok</body></html>", encoding="utf-8")

    def boom(**kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(agent_live, "_post_chat", boom)

    session = _new_session(tmp_path, input_path)
    result = session.send("do something")

    assert result["status"] == "interrupted"
    assert "user_interrupted" in session.trace.notes
    # Conversation is preserved so the user can continue after interrupting.
    assert any(message["role"] == "user" for message in session.messages)


def test_live_session_set_current_document_sets_parser_and_message(tmp_path: Path) -> None:
    pdf_path = tmp_path / "a.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    session = _new_session(tmp_path)

    session.set_current_document(
        pdf_path,
        default_pdf_parser="precise-api",
        routing_note="router selected runner=precise-api",
    )

    assert session.state.default_pdf_parser == "precise-api"
    assert session.state.input_path == pdf_path.resolve()
    assert any("precise-api" in str(m.get("content", "")) for m in session.messages if m["role"] == "user")


def test_live_session_set_current_document_clears_prior_document_state(tmp_path: Path) -> None:
    first = tmp_path / "first.html"
    second = tmp_path / "second.html"
    first.write_text("<html>first</html>", encoding="utf-8")
    second.write_text("<html>second</html>", encoding="utf-8")
    session = _new_session(tmp_path, first)
    session.state.parses["html"] = {"markdown": "first", "content_list": []}
    session.state.extracted = {"sections": [{"title": "first"}]}
    session.state.quality = {"status": "pass"}
    session.state.retrieval = {"stats": {"total_chunks": 1}}
    session.state.answer_validation = {"ok": True}

    session.set_current_document(second)

    assert session.state.input_path == second.resolve()
    assert session.state.parses == {}
    assert session.state.extracted is None
    assert session.state.quality is None
    assert session.state.retrieval is None
    assert session.state.answer_validation is None
