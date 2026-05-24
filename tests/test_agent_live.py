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
    assert data["autonomy_controls"]["mode"] == "skill_guided_tool_calling"
    assert Path(trace.output_dir, "live_agent_trace.json").exists()
    assert Path(trace.output_dir, "live_agent_summary.md").exists()


def test_finalize_requires_prior_answer_validation(tmp_path: Path) -> None:
    state = agent_live.AgentState(input_path=tmp_path / "input.html", output_dir=tmp_path)

    result = agent_live._tool_finalize(state, answer="ok", evidence=["x"])

    assert result["ok"] is False
    assert result["required_tool"] == "validate_answer"


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
