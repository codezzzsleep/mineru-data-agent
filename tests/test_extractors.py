import zipfile

from mineru_data_agent.extractors import (
    build_extracted_view,
    extract_docx,
    extract_html,
    extract_key_value_candidates,
    extract_markdown_tables,
    extract_pptx,
    extract_sections,
)


def test_extract_sections_from_markdown() -> None:
    markdown = "# Title\nintro\n## Clause 1\ncontent\n## Clause 2\nmore"
    sections = extract_sections(markdown)
    assert [item["title"] for item in sections] == ["Title", "Clause 1", "Clause 2"]
    assert sections[1]["level"] == 2


def test_extract_markdown_tables() -> None:
    markdown = """
| item | amount |
| --- | ---: |
| revenue | 100 |
| total | 100 |
"""
    tables = extract_markdown_tables(markdown)
    assert len(tables) == 1
    assert tables[0]["headers"] == ["item", "amount"]
    assert tables[0]["row_count"] == 2


def test_extract_mineru_html_tables_from_markdown() -> None:
    markdown = """
## Operating Result

<table><tr><td>Line Item</td><td>Q1</td><td>Total</td></tr><tr><td>Revenue</td><td>100</td><td>100</td></tr></table>
"""
    view = build_extracted_view(markdown, [{"type": "table", "text": markdown, "page_idx": 0}])
    assert view["tables"][0]["source"] == "html_table"
    assert view["tables"][0]["headers"] == ["Line Item", "Q1", "Total"]
    assert view["tables"][0]["rows"] == [["Revenue", "100", "100"]]
    assert "rowspan" not in view["numeric_facts"][0]["text"]


def test_extract_key_value_candidates() -> None:
    pairs = extract_key_value_candidates("公司名称：示例公司\nReport date: 2026")
    assert {"key": "公司名称", "value": "示例公司"} in pairs
    assert {"key": "Report date", "value": "2026"} in pairs


def test_build_extracted_view() -> None:
    view = build_extracted_view("# A\nvalue: 1", [{"type": "text", "text": "value: 1", "page_idx": 0}])
    assert view["content_summary"]["item_count"] == 1
    assert view["content_summary"]["provenance_level"] == "page"
    assert view["sections"][0]["title"] == "A"
    assert view["key_value_map"]["value"] == "1"


def test_numeric_facts_do_not_split_dates() -> None:
    view = build_extracted_view(
        "报告日期：2026-05-22\n完成 42 次巡检，发现 2 个异常点。",
        [{"type": "text", "text": "报告日期：2026-05-22", "page_idx": 0}],
    )
    numbers = [number for fact in view["numeric_facts"] for number in fact["numbers"]]
    assert "-05" not in numbers
    assert "-22" not in numbers
    assert "42" in numbers
    assert "2" in numbers


def test_extract_html_preserves_document_structure(tmp_path) -> None:
    html_path = tmp_path / "report.html"
    html_path.write_text(
        """
        <html><body><article>
          <h1>设备巡检日报</h1>
          <p>报告日期：2026-05-22</p>
          <p>处理建议：优先复查高温轴承。</p>
        </article></body></html>
        """,
        encoding="utf-8",
    )

    markdown, content = extract_html(html_path)
    view = build_extracted_view(markdown, content)

    assert "# 设备巡检日报" in markdown
    assert {"key": "报告日期", "value": "2026-05-22"} in view["key_values"]
    assert view["semantic_signals"]["field_coverage"]["has_date"] is True
    assert view["semantic_signals"]["field_coverage"]["has_recommendation"] is True
    assert view["structure_quality"]["heading_section_count"] == 1
    assert view["content_summary"]["provenance_level"] == "document"
    assert view["content_summary"]["source_counts"]["html"] == len(content)


def test_extract_html_tables_as_markdown(tmp_path) -> None:
    html_path = tmp_path / "table.html"
    html_path.write_text(
        """
        <html><body>
          <table>
            <tr><th>项目</th><th>数量</th></tr>
            <tr><td>异常点</td><td>2</td></tr>
          </table>
        </body></html>
        """,
        encoding="utf-8",
    )

    markdown, content = extract_html(html_path)
    view = build_extracted_view(markdown, content)

    assert "| 项目 | 数量 |" in markdown
    assert view["tables"][0]["headers"] == ["项目", "数量"]
    assert content[0]["type"] == "table"
    assert "page_idx" not in content[0]


def test_extract_docx_paragraphs_and_tables(tmp_path) -> None:
    docx_path = tmp_path / "sample.docx"
    document_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
      <w:body>
        <w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>合同审查报告</w:t></w:r></w:p>
        <w:p><w:r><w:t>Effective Date: 2026-05-22</w:t></w:r></w:p>
        <w:tbl>
          <w:tr><w:tc><w:p><w:r><w:t>Clause</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>Status</w:t></w:r></w:p></w:tc></w:tr>
          <w:tr><w:tc><w:p><w:r><w:t>2.1</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>pass</w:t></w:r></w:p></w:tc></w:tr>
        </w:tbl>
      </w:body>
    </w:document>
    """
    with zipfile.ZipFile(docx_path, "w") as archive:
        archive.writestr("word/document.xml", document_xml)

    markdown, content = extract_docx(docx_path)
    view = build_extracted_view(markdown, content)

    assert "# 合同审查报告" in markdown
    assert view["content_summary"]["source_counts"]["docx"] == len(content)
    assert view["tables"][0]["headers"] == ["Clause", "Status"]
    assert {"key": "Effective Date", "value": "2026-05-22"} in view["key_values"]


def test_extract_pptx_slides_and_tables(tmp_path) -> None:
    pptx_path = tmp_path / "sample.pptx"
    slide_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
           xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
      <p:cSld><p:spTree>
        <p:sp><p:txBody><a:p><a:r><a:t>流程复核</a:t></a:r></a:p><a:p><a:r><a:t>Inspection Date: 2026-05-22</a:t></a:r></a:p></p:txBody></p:sp>
        <p:graphicFrame><a:graphic><a:graphicData><a:tbl>
          <a:tr><a:tc><a:txBody><a:p><a:r><a:t>Step</a:t></a:r></a:p></a:txBody></a:tc><a:tc><a:txBody><a:p><a:r><a:t>Tool</a:t></a:r></a:p></a:txBody></a:tc></a:tr>
          <a:tr><a:tc><a:txBody><a:p><a:r><a:t>1</a:t></a:r></a:p></a:txBody></a:tc><a:tc><a:txBody><a:p><a:r><a:t>MinerU</a:t></a:r></a:p></a:txBody></a:tc></a:tr>
        </a:tbl></a:graphicData></a:graphic></p:graphicFrame>
      </p:spTree></p:cSld>
    </p:sld>
    """
    with zipfile.ZipFile(pptx_path, "w") as archive:
        archive.writestr("ppt/slides/slide1.xml", slide_xml)

    markdown, content = extract_pptx(pptx_path)
    view = build_extracted_view(markdown, content)

    assert "# Slide 1" in markdown
    assert view["content_summary"]["page_count"] == 1
    assert view["content_summary"]["source_counts"]["pptx"] == len(content)
    assert view["tables"][0]["headers"] == ["Step", "Tool"]
