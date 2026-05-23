# MinerU Data Agent Run bba6bc28deb2

- Task: HTTP 压测：抽取财报日期、公司名称、合计数字和可验证证据
- Profile: financial_report
- Execution method: auto
- Execution backend: pipeline
- LLM preplan applied changes: 0
- Input: `<PROJECT_ROOT>\submission_artifacts\http_load_test\request_artifacts\request_000\_uploads\d2e161d494294ccfb993fd26d3aa8580.html`
- Quality: pass (100/100)
- Content blocks: 8
- Pages with provenance: 0
- Provenance level: document
- Sections: 2
- Tables: 1
- Key-values: 5
- Field evidence records: 5
- Numeric facts: 7
- Dates detected: 1
- Recommendation signals: 2
- Anomaly signals: 3
- Retrieval chunks: 3
- Recovery decision: accept
- Recovery selected attempt: initial
- Recovery attempts: 1
- LLM analysis: disabled

## Plan
1. Inspect input type and task objective
2. Parse document with MinerU or native HTML extractor
3. Normalize content blocks with page-level or document-level provenance
4. Build markdown, section, key-value, table, and numeric views
5. Run quality checks and produce traceable logs
6. Prioritize dense table extraction and numeric consistency checks
7. Flag subtotal/total rows and suspicious numeric cells

## Planning Rationale
- financial keywords or explicit profile require table and numeric consistency checks
- HTML/DOCX/PPTX inputs are handled by native extractors to preserve document structure without MinerU
- backend=pipeline is used for MinerU parsing when the selected runner calls MinerU
- method=auto balances automatic parsing with OCR fallback when quality gates require it
- lang=ch is passed to MinerU or recorded for native extraction audit
- Recovery policy:
  - text_cleanup if mojibake or encoding noise is detected
  - ocr_retry for PDF/image results with blocking extraction or OCR-related quality issues
  - cli_fallback when online API lacks page-level provenance and a local MinerU CLI is available
  - manual_numeric_review when subtotal/total consistency checks fail

## Extracted Fields
- 报告日期: 2026-04-30
- 公司名称: 华东制造有限公司
- 报表口径: 人民币万元，未经审计，用于 Data Agent 结构化处理与数字复核演示。
- 异常提示: 合计行需要与明细项重新核验，避免 OCR 或表格跨列导致金额幻觉。
- 处理建议: 将总计、小计、合计行加入复核队列，并保留源页和表格行号证据。

## Field Evidence
- 报告日期: confidence=0.86, location=3, evidence=报告日期：2026-04-30
- 公司名称: confidence=0.86, location=5, evidence=公司名称：华东制造有限公司
- 报表口径: confidence=0.86, location=7, evidence=报表口径：人民币万元，未经审计，用于 Data Agent 结构化处理与数字复核演示。
- 异常提示: confidence=0.86, location=20, evidence=异常提示：合计行需要与明细项重新核验，避免 OCR 或表格跨列导致金额幻觉。
- 处理建议: confidence=0.86, location=22, evidence=处理建议：将总计、小计、合计行加入复核队列，并保留源页和表格行号证据。

## Recommendation Evidence
- 处理建议: 将总计、小计、合计行加入复核队列，并保留源页和表格行号证据。
- 处理建议：将总计、小计、合计行加入复核队列，并保留源页和表格行号证据。

## Recovery Decision
- Decision: accept
- Native extractor result has document/slide-level provenance; use PDF/MinerU path for page-layout audit.

Attempts:
- initial: pass (100/100), selected

## Issues
- [info] document_level_provenance: Native document input has document-level provenance rather than page-level provenance.
- [info] numeric_total_verified: A total/subtotal row matched the sum of comparable numeric rows.

## Markdown Preview

# 华东制造有限公司 2026 年一季度经营报表

报告日期：2026-04-30

公司名称：华东制造有限公司

报表口径：人民币万元，未经审计，用于 Data Agent 结构化处理与数字复核演示。

## 资产负债与利润摘要

| 项目 | 2026Q1 | 2025Q4 | 变动率 |
| --- | --- | --- | --- |
| 营业收入 | 12,860.50 | 11,902.10 | 8.05% |
| 营业成本 | 8,430.25 | 7,921.30 | 6.43% |
| 销售费用 | 615.30 | 590.00 | 4.29% |
| 管理费用 | 781.20 | 760.15 | 2.77% |
| 利润总额 | 3,033.75 | 2,630.65 | 15.32% |
| 合计 | 25,721.00 | 23,804.20 | 8.05% |

异常提示：合计行需要与明细项重新核验，避免 OCR 或表格跨列导致金额幻觉。

处理建议：将总计、小计、合计行加入复核队列，并保留源页和表格行号证据。
