from mineru_data_agent.mineru_client import _build_page_range, _markdown_to_content_blocks, _redact_sensitive_text


def test_build_page_range() -> None:
    assert _build_page_range(None, None) is None
    assert _build_page_range(1, None) == "1"
    assert _build_page_range(None, 3) == "3"
    assert _build_page_range(1, 3) == "1-3"


def test_markdown_to_content_blocks_keeps_source() -> None:
    blocks = _markdown_to_content_blocks("# Title\n\nParagraph", source="agent-api")
    assert [item["text"] for item in blocks] == ["# Title", "Paragraph"]
    assert [item["type"] for item in blocks] == ["heading", "text"]
    assert blocks[0]["source"] == "agent-api"
    assert "page_idx" not in blocks[0]


def test_markdown_to_content_blocks_preserves_table_and_list_types() -> None:
    markdown = "\n".join(
        [
            "# Contract",
            "",
            "Intro paragraph.",
            "",
            "| Field | Value |",
            "| --- | --- |",
            "| Amount | 100 |",
            "",
            "- keep audit trail",
            "- verify totals",
        ]
    )

    blocks = _markdown_to_content_blocks(markdown, source="agent-api")

    assert [item["type"] for item in blocks] == ["heading", "text", "table", "list"]
    assert "| Amount | 100 |" in blocks[2]["text"]
    assert "verify totals" in blocks[3]["text"]


def test_markdown_to_content_blocks_preserves_html_table_type() -> None:
    blocks = _markdown_to_content_blocks("<table>\n<tr><td>A</td></tr>\n</table>\n\nDone", source="agent-api")
    assert [item["type"] for item in blocks] == ["table", "text"]


def test_markdown_to_content_blocks_single_line_html_table_does_not_swallow_following_heading() -> None:
    markdown = "<table><tr><td>A</td></tr></table>\n\n## Next\n\nDone"
    blocks = _markdown_to_content_blocks(markdown, source="agent-api")
    assert [item["type"] for item in blocks] == ["table", "heading", "text"]
    assert "## Next" not in blocks[0]["text"]


def test_redact_sensitive_text_masks_tokens_and_signed_urls() -> None:
    text = (
        "Authorization: Bearer abc.def token=secret "
        "https://host/file?X-Amz-Credential=abc&X-Amz-Signature=deadbeef&safe=1"
    )
    clean = _redact_sensitive_text(text)
    assert "abc.def" not in clean
    assert "token=secret" not in clean
    assert "deadbeef" not in clean
    assert "Bearer ***" in clean
    assert "X-Amz-Signature=***" in clean
