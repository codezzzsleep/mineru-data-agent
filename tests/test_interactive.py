from pathlib import Path

from mineru_data_agent.interactive import (
    _build_directory_batch_tasks,
    _build_workspace_context,
    _extract_url,
    _fallback_route_interactive_intent,
    _extract_existing_path,
    _is_document_workflow_request,
    answer_local_workspace_request,
    plan_chat_command,
    render_help,
    render_directory_batch_plan,
    render_directory_batch_result,
    render_single_document_plan,
    render_live_result,
    render_plan,
    run_interactive_chat,
)


def test_plan_chat_command_uses_heuristic_without_deepseek_key(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    doc = tmp_path / "report.html"
    doc.write_text("<h1>Report</h1>", encoding="utf-8")

    command = plan_chat_command(
        f"parse {doc} and extract financial table totals",
        output_root=tmp_path / "runs",
    )

    assert command.action == "run"
    assert command.input_path == str(doc)
    assert command.profile == "financial_report"
    assert command.runner == "auto"
    assert "heuristic" in command.rationale


def test_plan_chat_command_can_select_precise_runner(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    doc = tmp_path / "report.pdf"
    doc.write_bytes(b"%PDF-1.4")

    command = plan_chat_command(f"use precise api for {doc}, verify totals", output_root=tmp_path / "runs")

    assert command.runner == "precise-api"
    assert command.backend == "vlm-transformers"


def test_render_helpers_include_expected_commands() -> None:
    assert "/status" in render_help()
    plan = render_plan(
        plan_chat_command(
            "parse missing.pdf",
            output_root=Path("runs/chat"),
            provider="none",
        )
    )
    assert "Planned document workflow" in plan


def test_local_workspace_request_lists_current_directory(tmp_path: Path) -> None:
    (tmp_path / "史料.pdf").write_bytes(b"%PDF-1.4")
    (tmp_path / "notes").mkdir()

    answer = answer_local_workspace_request("ls", workspace_root=tmp_path, current_doc=None)

    assert answer is not None
    assert str(tmp_path) in answer
    assert "史料.pdf" in answer
    assert "notes/" in answer


def test_live_intent_router_keeps_casual_chat_out_of_workflow() -> None:
    assert not _is_document_workflow_request("hi", current_doc=None, path="", url="")
    assert not _is_document_workflow_request("你觉得这个设计怎么样", current_doc=None, path="", url="")
    assert _is_document_workflow_request("帮我解析这份 PDF", current_doc=None, path="", url="")
    assert _is_document_workflow_request("总结一下", current_doc="report.pdf", path="", url="")


def test_extract_url_for_online_document_requests() -> None:
    assert _extract_url("解析 https://example.com/report.html。") == "https://example.com/report.html"


def test_interactive_chat_answers_casual_message_without_live_workflow(monkeypatch, tmp_path: Path) -> None:
    prompts = iter(["hi", "/exit"])
    printed: list[str] = []

    def fail_build_live_session(**kwargs):
        raise AssertionError("casual chat must not start live tool workflow")

    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setattr("mineru_data_agent.interactive._build_live_session", fail_build_live_session)

    run_interactive_chat(
        output_root=tmp_path / "runs",
        dry_run=False,
        input_func=lambda prompt: next(prompts),
        print_func=printed.append,
    )

    assert not any("Running live tool-calling workflow" in item for item in printed)
    assert any("普通聊天模式" in item for item in printed)


def test_interactive_chat_routes_model_identity_through_ai(monkeypatch, tmp_path: Path) -> None:
    prompts = iter(["你是什么模型", "/exit"])
    printed: list[str] = []
    calls: dict[str, object] = {}

    def fail_build_live_session(**kwargs):
        raise AssertionError("model identity chat must not start live document workflow")

    def fake_chatbot_reply(text, **kwargs):
        calls["text"] = text
        calls["provider"] = kwargs["provider"]
        calls["model"] = kwargs["model"]
        calls["workspace_context"] = kwargs["workspace_context"]
        return "AI answered with injected Harness identity."

    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr("mineru_data_agent.interactive._build_live_session", fail_build_live_session)
    monkeypatch.setattr(
        "mineru_data_agent.interactive.route_interactive_intent",
        lambda *args, **kwargs: {"action": "chat", "task": "你是什么模型"},
    )
    monkeypatch.setattr("mineru_data_agent.interactive._chatbot_reply", fake_chatbot_reply)

    run_interactive_chat(
        output_root=tmp_path / "runs",
        dry_run=False,
        input_func=lambda prompt: next(prompts),
        print_func=printed.append,
    )

    assert calls["text"] == "你是什么模型"
    assert calls["provider"] == "deepseek"
    assert calls["model"] == "deepseek-v4-flash"
    assert isinstance(calls["workspace_context"], dict)
    assert any("AI answered with injected Harness identity." in item for item in printed)


def test_interactive_chat_handles_ls_as_workspace_tool(monkeypatch, tmp_path: Path) -> None:
    prompts = iter(["ls", "/exit"])
    printed: list[str] = []
    (tmp_path / "local.pdf").write_bytes(b"%PDF-1.4")

    def fail_build_live_session(**kwargs):
        raise AssertionError("ls must not start live document workflow")

    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("mineru_data_agent.interactive._build_live_session", fail_build_live_session)

    run_interactive_chat(
        output_root=tmp_path / "runs",
        dry_run=False,
        input_func=lambda prompt: next(prompts),
        print_func=printed.append,
    )

    assert any("local.pdf" in item for item in printed)
    assert not any("Running live tool-calling workflow" in item for item in printed)


def test_interactive_chat_uses_llm_route_for_current_directory_batch(monkeypatch, tmp_path: Path) -> None:
    prompts = iter(["请解析当前路径下的这些文件", "/exit"])
    printed: list[str] = []
    calls: dict[str, object] = {}
    (tmp_path / "local.pdf").write_bytes(b"%PDF-1.4")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr(
        "mineru_data_agent.interactive.route_interactive_intent",
        lambda *args, **kwargs: {
            "action": "current_directory_batch",
            "task": "整理当前目录资料",
            "profile": "auto",
            "reason": "llm chose directory batch",
        },
    )

    def fake_run_current_directory_batch(**kwargs):
        calls.update(kwargs)
        return {
            "ok": True,
            "batch_report": {"completed": 1, "total": 1, "failed": 0},
            "package_report": {"total_source_documents": 1},
            "document_root": str(tmp_path / "runs" / "packages"),
            "corpus_catalog": {"catalog_json": str(tmp_path / "runs" / "catalog.json")},
        }

    monkeypatch.setattr("mineru_data_agent.interactive.run_current_directory_batch", fake_run_current_directory_batch)

    run_interactive_chat(
        output_root=tmp_path / "runs",
        dry_run=False,
        input_func=lambda prompt: next(prompts),
        print_func=printed.append,
    )

    assert calls["workspace_root"] == tmp_path.resolve()
    assert calls["task"] == "整理当前目录资料"
    assert any("DeepSeek 已识别为目录批量资料处理任务" in item for item in printed)
    assert any("Completed current-directory Data Agent workflow" in item for item in printed)


def test_directory_name_can_be_extracted_from_natural_language(tmp_path: Path) -> None:
    folder = tmp_path / "史料part"
    folder.mkdir()

    detected = _extract_existing_path("把史料part 文件夹提取", workspace_root=tmp_path, allow_directories=True)

    assert detected == str(folder.resolve())


def test_fallback_router_batches_named_subdirectory(tmp_path: Path) -> None:
    folder = tmp_path / "史料part"
    folder.mkdir()
    (folder / "archive.pdf").write_bytes(b"%PDF-1.4")
    context = _build_workspace_context(workspace_root=tmp_path, output_root=tmp_path / "runs", current_doc=None)

    route = _fallback_route_interactive_intent(
        "把史料part 文件夹精确提取",
        workspace_context=context,
        path="",
        directory_path="",
        url="",
        current_doc=None,
    )

    assert route["action"] == "current_directory_batch"
    assert route["directory_path"] == str(folder)
    assert route["runner"] == "precise-api"


def test_interactive_chat_runs_batch_for_named_subdirectory(monkeypatch, tmp_path: Path) -> None:
    prompts = iter(["把史料part 文件夹提取", "/exit"])
    printed: list[str] = []
    calls: dict[str, object] = {}
    folder = tmp_path / "史料part"
    folder.mkdir()
    (folder / "archive.pdf").write_bytes(b"%PDF-1.4")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr(
        "mineru_data_agent.interactive.route_interactive_intent",
        lambda *args, **kwargs: {
            "action": "current_directory_batch",
            "task": "提取史料part资料",
            "directory_path": str(folder),
            "profile": "auto",
            "runner": "auto",
        },
    )

    def fake_run_current_directory_batch(**kwargs):
        calls.update(kwargs)
        return {
            "ok": True,
            "batch_report": {"completed": 1, "total": 1, "failed": 0},
            "package_report": {"total_source_documents": 1},
            "document_root": str(tmp_path / "runs" / "packages"),
            "corpus_catalog": {"catalog_json": str(tmp_path / "runs" / "catalog.json")},
        }

    monkeypatch.setattr("mineru_data_agent.interactive.run_current_directory_batch", fake_run_current_directory_batch)

    run_interactive_chat(
        output_root=tmp_path / "runs",
        dry_run=False,
        input_func=lambda prompt: next(prompts),
        print_func=printed.append,
    )

    assert calls["workspace_root"] == folder.resolve()
    assert calls["task"] == "提取史料part资料"
    assert any(str(folder.resolve()) in item for item in printed)


def test_build_directory_batch_tasks_chunks_large_scanned_pdf(monkeypatch, tmp_path: Path) -> None:
    pdf = tmp_path / "archive.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    monkeypatch.setattr(
        "mineru_data_agent.interactive.build_input_metadata",
        lambda path: {"suffix": ".pdf", "page_count": 401, "has_text_layer": False, "size_bytes": 1024},
    )

    tasks = _build_directory_batch_tasks([pdf], task="整理资料", profile="auto")

    assert [task["page_range"] for task in tasks] == ["1-200", "201-400", "401-401"]
    assert all(task["source_file"] == "archive.pdf" for task in tasks)
    assert all(task["method"] == "ocr" for task in tasks)


def test_render_directory_batch_plan_explains_each_file(monkeypatch, tmp_path: Path) -> None:
    born = tmp_path / "born.pdf"
    scanned = tmp_path / "scan.pdf"
    page = tmp_path / "page.html"
    born.write_bytes(b"%PDF-1.4")
    scanned.write_bytes(b"%PDF-1.4")
    page.write_text("<h1>ok</h1>", encoding="utf-8")

    def fake_metadata(path):
        if Path(path).name == "born.pdf":
            return {
                "suffix": ".pdf",
                "size_bytes": 1000,
                "page_count": 12,
                "has_text_layer": True,
                "layout_risk": "low",
            }
        if Path(path).name == "scan.pdf":
            return {"suffix": ".pdf", "size_bytes": 1000, "page_count": 401, "has_text_layer": False}
        return {"suffix": ".html", "size_bytes": 1000, "page_count": None, "has_text_layer": None}

    monkeypatch.setattr("mineru_data_agent.interactive.build_input_metadata", fake_metadata)

    text = render_directory_batch_plan(workspace_root=tmp_path, task="解析全部文档", runner="auto")

    assert "执行计划:" in text
    assert "born.pdf -> 本地 PDF 文字层优先" in text
    assert "scan.pdf -> 扫描 PDF OCR 分段处理" in text
    assert "切分为 3 个页段" in text
    assert "page.html -> 本地结构解析" in text
    assert "检测到可提取文字层" in text
    assert "未检测到可用文字层" in text


def test_render_directory_batch_plan_flags_complex_text_layer_pdf(monkeypatch, tmp_path: Path) -> None:
    pdf = tmp_path / "two-column.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    monkeypatch.setattr(
        "mineru_data_agent.interactive.build_input_metadata",
        lambda path: {
            "suffix": ".pdf",
            "size_bytes": 1000,
            "page_count": 20,
            "has_text_layer": True,
            "is_complex_layout": True,
            "layout_type": "multi_column",
            "layout_risk": "reading_order_risk",
            "multi_column_pages": 4,
            "layout_sampled_pages": 5,
            "has_tables": False,
        },
    )

    text = render_directory_batch_plan(workspace_root=tmp_path, task="解析全部文档", runner="auto")

    assert "two-column.pdf -> 本地 PDF 文字层试读 + 质量门" in text
    assert "复杂版式/双栏风险 4/5 页" in text
    assert "初判: 直接读取 PDF 文字层" in text
    assert "预检关注: 双栏/复杂版式会破坏裸文本阅读顺序" in text
    assert "执行时通过文字层/版式探测由质量门确认是否升级" in text
    assert "Harness 拦截:" not in text
    assert "拦截直接读取" not in text
    assert "风险成立时升级到 MinerU 版面解析" in text


def test_render_directory_batch_plan_flags_table_pdf_for_vlm_and_ocr_check(monkeypatch, tmp_path: Path) -> None:
    pdf = tmp_path / "table.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    monkeypatch.setattr(
        "mineru_data_agent.interactive.build_input_metadata",
        lambda path: {
            "suffix": ".pdf",
            "size_bytes": 1000,
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

    text = render_directory_batch_plan(workspace_root=tmp_path, task="解析全部文档", runner="auto")

    assert "table.pdf -> 本地 PDF 文字层试读 + 质量门" in text
    assert "初判: 直接读取 PDF 文字层" in text
    assert "预检关注: 检测到表格页 2, 3，需要保持行列结构" in text
    assert "执行时通过文字层/版式探测由质量门确认是否升级" in text
    assert "Harness 拦截:" not in text
    assert "拦截直接读取" not in text
    assert "VLM 保表格结构" in text
    assert "OCR/文字层校验数字" in text


def test_render_single_document_plan_explains_before_live_workflow(monkeypatch, tmp_path: Path) -> None:
    pdf = tmp_path / "table.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    monkeypatch.setattr(
        "mineru_data_agent.interactive.build_input_metadata",
        lambda path: {
            "suffix": ".pdf",
            "size_bytes": 1000,
            "page_count": 8,
            "has_text_layer": True,
            "layout_risk": "low",
            "has_tables": True,
            "table_pages": [2, 3],
            "table_count": 2,
            "table_risk": "table_structure_or_numeric_risk",
        },
    )

    text = render_single_document_plan(input_path=pdf, task="解析成文本", runner="auto")

    assert "执行计划:" in text
    assert "文档: table.pdf" in text
    assert "初判: 直接读取 PDF 文字层" in text
    assert "预检关注: 检测到表格页 2, 3，需要保持行列结构" in text
    assert "执行时通过文字层/版式探测由质量门确认是否升级" in text
    assert "Harness 拦截:" not in text
    assert "VLM 保表格结构" in text


def test_render_directory_batch_result_reports_runtime_harness_gate(tmp_path: Path) -> None:
    text = render_directory_batch_result(
        {
            "ok": True,
            "batch_report": {
                "completed": 1,
                "total": 1,
                "failed": 0,
                "items": [
                    {
                        "source_file": "table.pdf",
                        "harness_gate": {
                            "blocked": True,
                            "initial_decision": "local-pdf-text",
                            "target": "precise-api",
                            "reason": "检测到表格页 [2, 3]，需要保持行列结构",
                            "actions": [
                                {
                                    "action": "vlm_table_review",
                                    "backend": "vlm-transformers",
                                    "pages": [2, 3],
                                    "reason": "表格页使用 VLM 保持行列结构",
                                }
                            ],
                        },
                    }
                ],
            },
            "package_report": {"total_source_documents": 1},
            "document_root": str(tmp_path / "packages"),
            "corpus_catalog": {"catalog_json": str(tmp_path / "catalog.json")},
        }
    )

    assert "执行中 Harness 拦截:" in text
    assert "table.pdf: 初始 local-pdf-text 被拦截，升级到 precise-api" in text
    assert "vlm_table_review pages=[2, 3]" in text


def test_interactive_chat_prompts_for_document_when_workflow_intent_has_no_source(monkeypatch, tmp_path: Path) -> None:
    prompts = iter(["帮我解析这份PDF并提取字段", "/exit"])
    printed: list[str] = []

    def fail_build_live_session(**kwargs):
        raise AssertionError("missing document source should not start live workflow")

    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setattr("mineru_data_agent.interactive._build_live_session", fail_build_live_session)

    run_interactive_chat(
        output_root=tmp_path / "runs",
        dry_run=False,
        input_func=lambda prompt: next(prompts),
        print_func=printed.append,
    )

    assert any("补充" in item and ("路径" in item or "目录" in item) for item in printed)
    assert not any("Running live tool-calling workflow" in item for item in printed)


def test_interactive_chat_runs_live_workflow_by_default(monkeypatch, tmp_path: Path) -> None:
    doc = tmp_path / "report.html"
    doc.write_text("<h1>Report</h1>", encoding="utf-8")
    prompts = iter([f"parse {doc} and summarize", "/exit"])
    printed: list[str] = []
    calls: dict[str, object] = {}

    class FakeSession:
        def set_current_document(self, path, *, default_pdf_parser="auto", routing_note=""):
            calls["doc"] = path
            calls["default_pdf_parser"] = default_pdf_parser

        def send(self, text):
            calls["sent"] = text
            return {
                "run_id": "live123",
                "status": "completed",
                "tool_sequence": ["select_skill", "parse_html", "finalize"],
                "final_answer": "ok",
                "summary_path": "summary.md",
                "trace_path": "trace.json",
            }

    def fake_build_live_session(**kwargs):
        calls["build_kwargs"] = kwargs
        return FakeSession()

    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setattr("mineru_data_agent.interactive._build_live_session", fake_build_live_session)

    run_interactive_chat(
        output_root=tmp_path / "runs",
        dry_run=False,
        input_func=lambda prompt: next(prompts),
        print_func=printed.append,
    )

    # No [Y/n] confirmation prompt anymore: the user message goes straight into the
    # autonomous live session, which keeps state across turns.
    assert calls["build_kwargs"]["provider"] == "deepseek"
    assert calls["doc"] == str(doc)
    assert calls["default_pdf_parser"] == "auto"  # HTML routes to native, not a PDF parser
    assert calls["sent"] == f"parse {doc} and summarize"
    assert any("Completed live Agent workflow" in item for item in printed)
    assert any("执行计划:" in item for item in printed)


def test_render_live_result_explains_tools_for_humans() -> None:
    text = render_live_result(
        {
            "run_id": "live123",
            "status": "completed",
            "provider": "deepseek",
            "model": "deepseek-v4-flash",
            "selected_skill": {"name": "Structured extraction", "reason": "用户要求提取字段"},
            "tool_sequence": ["select_skill", "parse_html", "build_extracted", "validate_answer", "finalize"],
            "answer_validation": {"ok": True, "recommendation": "finalize"},
            "parse_runtime": {
                "kind": "pdf",
                "parser": "local",
                "backend": "local-text-layer",
                "page_count": 9,
                "has_text_layer": True,
                "blocks": 12,
                "markdown_chars": 8000,
            },
            "final_answer": "提取完成。",
            "summary_path": "summary.md",
            "trace_path": "trace.json",
            "result_path": "result.json",
        }
    )

    assert "工具使用:" in text
    assert "选择任务策略" in text
    assert "本地 HTML 解析" in text
    assert "解析路径:" in text
    assert "pdf: local/local-text-layer" in text
    assert "答案校验: 通过" in text
    assert "trace.json" in text


def test_render_live_result_reports_runtime_harness_gate() -> None:
    text = render_live_result(
        {
            "run_id": "live123",
            "status": "completed",
            "tool_sequence": ["select_skill", "parse_pdf", "build_extracted"],
            "runtime_harness_events": [
                {
                    "blocked": True,
                    "source_file": "table.pdf",
                    "initial_decision": "local-pdf-text",
                    "target": "precise-api",
                    "backend": "vlm-transformers",
                    "reason": "检测到表格页 [2, 3]，需要保持行列结构并校验数字",
                    "actions": [
                        {
                            "action": "vlm_table_review",
                            "pages": [2, 3],
                            "reason": "表格页使用 VLM 保持行列结构和跨行/跨列关系",
                        }
                    ],
                }
            ],
            "summary_path": "summary.md",
            "trace_path": "trace.json",
        }
    )

    assert "执行中 Harness 拦截:" in text
    assert "table.pdf: 初始 local-pdf-text 被拦截，升级到 precise-api/vlm-transformers" in text
    assert "vlm_table_review pages=[2, 3]" in text
