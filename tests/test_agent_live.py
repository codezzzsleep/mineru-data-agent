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

    def fake_post_chat(**kwargs):
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
                                    "name": "finalize",
                                    "arguments": '{"answer":"ok","evidence":["input contained ok"]}',
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
        max_turns=1,
    )

    result_path = Path(trace.output_dir) / "result.json"
    data = __import__("json").loads(result_path.read_text(encoding="utf-8"))
    assert data["agent_mode"] == "live_tool_calling"
    assert data["status"] == "completed"
    assert data["tool_call_completed"] is True
    assert data["answer_quality_pass"] is None
    assert data["quality_review"]["status"] == "unreviewed"
    assert data["final_answer"] == "ok"
    assert data["tool_sequence"] == ["finalize"]
    assert Path(trace.output_dir, "live_agent_trace.json").exists()
    assert Path(trace.output_dir, "live_agent_summary.md").exists()


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
    assert "Answer-quality pass cases: **0**" in markdown
    assert "| 2 | `bad` | empty | false | unreviewed | assistant_answer_without_finalize" in markdown
