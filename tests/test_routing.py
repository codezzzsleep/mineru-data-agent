from mineru_data_agent.routing import build_input_metadata, build_workflow_routing


def test_local_html_routes_to_native() -> None:
    decision = build_workflow_routing(
        input_metadata={"suffix": ".html", "size_bytes": 1024},
        task="extract fields",
        requested_runner="auto",
        current_runner="auto",
        precise_api_token_available=True,
        local_cli_available=True,
    )

    assert decision.selected_runner == "native"
    assert decision.selected_tool == "native_extractor"
    assert decision.route_mode == "local_native_parse"


def test_small_pdf_without_token_uses_agent_api() -> None:
    decision = build_workflow_routing(
        input_metadata={"suffix": ".pdf", "size_bytes": 1024 * 1024, "page_count": 2},
        task="extract text",
        requested_runner="auto",
        current_runner="auto",
        precise_api_token_available=False,
        local_cli_available=False,
    )

    assert decision.selected_runner == "agent-api"
    assert decision.status == "ready"
    assert decision.constraints["agent_light_api"]["eligible"] is True


def test_complex_financial_pdf_with_token_escalates_to_precise_api() -> None:
    decision = build_workflow_routing(
        input_metadata={"suffix": ".pdf", "size_bytes": 1024 * 1024, "page_count": 8},
        task="extract financial tables as JSON and verify totals",
        profile="financial_report",
        backend="vlm-transformers",
        requested_runner="auto",
        current_runner="auto",
        precise_api_token_available=True,
        local_cli_available=True,
    )

    assert decision.selected_runner == "precise-api"
    assert decision.selected_model_version == "vlm"
    assert decision.quality_policy["requires_table_review"] is True


def test_large_pdf_without_token_needs_config_when_no_cli() -> None:
    decision = build_workflow_routing(
        input_metadata={"suffix": ".pdf", "size_bytes": 20 * 1024 * 1024, "page_count": 50},
        task="extract document",
        requested_runner="auto",
        current_runner="auto",
        precise_api_token_available=False,
        local_cli_available=False,
    )

    assert decision.selected_runner == "agent-api"
    assert decision.status == "needs_config"
    assert decision.constraints["agent_light_api"]["eligible"] is False


def test_build_input_metadata_probes_pdf_page_count(monkeypatch, tmp_path) -> None:
    pdf = tmp_path / "demo.pdf"
    pdf.write_bytes(b"%PDF-1.4")

    monkeypatch.setattr("mineru_data_agent.routing.probe_pdf_text_layer", lambda path: (23, True))

    metadata = build_input_metadata(pdf)

    assert metadata["page_count"] == 23
    assert metadata["has_text_layer"] is True
    assert metadata["probe_source"] == "pypdf"
