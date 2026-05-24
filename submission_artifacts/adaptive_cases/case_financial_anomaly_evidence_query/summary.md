# MinerU Data Agent Run c7a3814fb200

- Schema version: 2026-05-24
- Task: 找出财报中需要复核的异常或风险信号，列出来源证据和建议处理动作。
- Profile: financial_report
- Execution method: auto
- Execution backend: pipeline
- LLM preplan applied changes: 0
- Input: `<PROJECT_ROOT>\examples\cases\case_1_financial_report.html`
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
- Task intents: anomaly_detection, evidence_trace
- LLM analysis: disabled

## Plan
1. Inspect input type, document metadata, and natural-language task objective
2. Infer task intents and generate a target extraction schema
3. Choose MinerU/native parsing path and record execution rationale
4. Normalize content blocks with page-level or document-level provenance
5. Build markdown, section, key-value, table, numeric, and field-evidence views
6. Run task-specific post-processing and quality checks
7. Select recovery action from issue codes, retry history, and task priorities
8. Produce traceable result, summary, retrieval chunks, and audit logs
9. Prioritize dense table extraction and numeric consistency checks
10. Compute trend/comparison candidates when the task asks for growth, decline, max/min, or year-over-year change
11. Flag subtotal/total rows and suspicious numeric cells
12. Apply task intent `anomaly_detection` with schema-aware extraction and verification
13. Apply task intent `evidence_trace` with schema-aware extraction and verification

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

## Adaptive Task Decision
- Intents: anomaly_detection, evidence_trace
- Target schema keys: company_name, report_period, line_item, current_value, previous_value, unit, evidence, risk_reason
- Quality thresholds: {"min_quality_score": 90, "require_tables": true, "require_numeric_facts": true, "prefer_page_provenance": false}
- Recovery strategy:
  - text_cleanup on mojibake_or_encoding_noise (normal)
  - manual_numeric_review on total_or_subtotal_mismatch (high)

## Agent Action Plan
- Subtasks: 6
- Selected tools: native_extractor, structured_extractor, numeric_validator, text_cleanup, retrieval_exporter
- understand_task: Classify the document task and identify intent-specific outputs.
- choose_parse_path: Pick the cheapest parser path that still preserves required provenance.
- extract_structure: Normalize sections, tables, key-values, numeric facts, and field evidence.
- validate_quality: Run profile and task-specific gates before accepting the result.
- replan_if_needed: Map quality issues to recovery actions and select the best attempt.
- export_artifacts: Write result, trace, summary, and retrieval artifacts.

## Runtime Recovery Plan
- Initial issue codes: document_level_provenance, numeric_total_verified

## Agent Replan After Quality
- Issue codes: document_level_provenance, numeric_total_verified
- Attempted actions: initial
- Selected reason: initial result remained the best accepted quality attempt

## Task-Specific Answers
- Anomaly candidates: 3

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
