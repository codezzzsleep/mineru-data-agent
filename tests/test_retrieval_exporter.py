from mineru_data_agent.retrieval_exporter import build_retrieval_chunks


def test_build_retrieval_chunks_filters_noise_and_tracks_section() -> None:
    content_list = [
        {"type": "page_header", "text": "Annual Report", "page_idx": 0},
        {"type": "text", "text": "## Revenue", "page_idx": 0},
        {"type": "text", "text": "Revenue was 100 million yuan.", "page_idx": 0},
        {"type": "page_number", "text": "1", "page_idx": 0},
    ]

    chunks, report = build_retrieval_chunks(markdown="", content_list=content_list, doc_id="demo.pdf")

    assert len(chunks) == 1
    assert chunks[0].section_title == "Revenue"
    assert chunks[0].content_type == "text"
    assert "100 million" in chunks[0].chunk_text
    assert len(report["skipped_blocks"]) == 2


def test_build_retrieval_chunks_supports_nested_mineru_v2_pages() -> None:
    content_list = [
        [
            {
                "type": "paragraph",
                "content": {"paragraph_content": [{"type": "text", "content": "First page paragraph."}]},
            }
        ],
        [
            {
                "type": "paragraph",
                "content": {"paragraph_content": [{"type": "text", "content": "Second page paragraph."}]},
            }
        ],
    ]

    chunks, _ = build_retrieval_chunks(markdown="", content_list=content_list, doc_id="nested")

    assert len(chunks) == 1
    assert chunks[0].page_no == 1
    assert "First page paragraph" in chunks[0].chunk_text
    assert "Second page paragraph" in chunks[0].chunk_text


def test_build_retrieval_chunks_uses_html_heading_blocks() -> None:
    content_list = [
        {"type": "heading", "text": "# 设备巡检日报", "page_idx": 0},
        {"type": "text", "text": "报告日期：2026-05-22", "page_idx": 0},
        {"type": "list_item", "text": "- 复查异常点", "page_idx": 0},
    ]

    chunks, report = build_retrieval_chunks(markdown="", content_list=content_list, doc_id="html")

    assert report["parse_errors"] == []
    assert len(chunks) == 1
    assert chunks[0].section_title == "设备巡检日报"
    assert "复查异常点" in chunks[0].chunk_text


def test_build_retrieval_chunks_falls_back_to_markdown() -> None:
    markdown = "# Main\nAlpha\n\n## Detail\nBeta"

    chunks, report = build_retrieval_chunks(markdown=markdown, content_list=[], doc_id="md")

    assert report["parse_errors"] == []
    assert [chunk.section_title for chunk in chunks] == ["Main", "Detail"]
    assert chunks[0].chunk_id.startswith("md:p1:text:")
