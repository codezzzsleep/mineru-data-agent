from mineru_data_agent.mineru_client import _build_page_range, _markdown_to_content_blocks


def test_build_page_range() -> None:
    assert _build_page_range(None, None) is None
    assert _build_page_range(1, None) == "1"
    assert _build_page_range(None, 3) == "3"
    assert _build_page_range(1, 3) == "1-3"


def test_markdown_to_content_blocks_keeps_source() -> None:
    blocks = _markdown_to_content_blocks("# Title\n\nParagraph", source="agent-api")
    assert [item["text"] for item in blocks] == ["# Title", "Paragraph"]
    assert blocks[0]["source"] == "agent-api"
    assert "page_idx" not in blocks[0]
