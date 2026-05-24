# MinerU Data Agent Run e9681de1b983

- Task: 处理跨页财报表格，合并上下文，检查小计和总计，并输出需要人工复核的差异。
- Profile: financial_report
- Execution method: auto
- Execution backend: pipeline
- LLM preplan applied changes: 0
- Input: `<PROJECT_ROOT>\examples\challenge_cases\case_6_cross_page_financial_table.html`
- Quality: pass_with_warnings (92/100)
- Content blocks: 12
- Pages with provenance: 0
- Provenance level: document
- Sections: 4
- Tables: 2
- Key-values: 6
- Field evidence records: 6
- Numeric facts: 10
- Dates detected: 2
- Recommendation signals: 1
- Anomaly signals: 1
- Retrieval chunks: 5
- Recovery decision: manual_numeric_review
- Recovery selected attempt: initial
- Recovery attempts: 1
- Task intents: aggregation, cross_page_reasoning
- LLM analysis: enabled/completed

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
12. Apply task intent `aggregation` with schema-aware extraction and verification
13. Apply task intent `cross_page_reasoning` with schema-aware extraction and verification
14. LLM preplan: Decompose task into extraction, validation, and recovery decisions
15. LLM preplan: Select tools based on profile, provenance need, and quality risks

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
- Intents: aggregation, cross_page_reasoning
- Target schema keys: company_name, report_period, line_item, current_value, previous_value, unit, evidence, page_span, 跨页表格, 小计, 总计, 差异
- Quality thresholds: {"min_quality_score": 90, "require_tables": true, "require_numeric_facts": true, "prefer_page_provenance": false}
- Recovery strategy:
  - text_cleanup on mojibake_or_encoding_noise (normal)
  - manual_numeric_review on total_or_subtotal_mismatch (high)
  - llm_suggested_review on manual_numeric_review on total mismatch (advisory)
  - llm_suggested_review on chunk_stitch_review for cross-page reference (advisory)

## Agent Action Plan
- Subtasks: 7
- Selected tools: native_extractor, llm_preplanner, structured_extractor, numeric_validator, text_cleanup, llm_post_review, retrieval_exporter
- understand_task: Classify the document task and identify intent-specific outputs.
- choose_parse_path: Pick the cheapest parser path that still preserves required provenance.
- extract_structure: Normalize sections, tables, key-values, numeric facts, and field evidence.
- validate_quality: Run profile and task-specific gates before accepting the result.
- llm_review: Review parse output against task-specific risks and propose follow-up actions.
- replan_if_needed: Map quality issues to recovery actions and select the best attempt.

## Agent Replan After Quality
- Issue codes: document_level_provenance, numeric_total_verified, numeric_total_mismatch
- Attempted actions: initial
- Selected reason: initial result remained the best accepted quality attempt

## Task-Specific Answers
- Top growth candidate: Maintenance Service delta=7246.0 percent_change=181150.0
- Comparison candidates: 5

## LLM Agent Analysis

Pre-execution control: profile=financial_report, runner=native, method=auto, backend=pipeline

处理跨页财报表格，合并上下文，检查小计和总计，并输出需要人工复核的差异。

LLM usage: 1460 tokens across 2 call(s); estimated cost=None

Suggested execution plan:
1. Review quality issues
2. Map issue codes to replan actions

## Extracted Fields
- Document ID: FIN-CROSS-2026-06
- Reporting Period: 2026-01-01 to 2026-03-31
- Owner: Finance Shared Service Center
- Scenario: the table is designed to mimic a PDF where the header and subtotal continue across pages.
- Risk: subtotal and total rows are separated by a page break in the source PDF.
- Recommendation: verify that retrieval chunks preserve both page labels and table context.

## Field Evidence
- Document ID: confidence=0.86, location=3, evidence=Document ID: FIN-CROSS-2026-06
- Reporting Period: confidence=0.86, location=5, evidence=Reporting Period: 2026-01-01 to 2026-03-31
- Owner: confidence=0.86, location=7, evidence=Owner: Finance Shared Service Center
- Scenario: confidence=0.86, location=11, evidence=Scenario: the table is designed to mimic a PDF where the header and subtotal continue across pages.
- Risk: confidence=0.86, location=31, evidence=Risk: subtotal and total rows are separated by a page break in the source PDF.

## Recommendation Evidence
- Recommendation: verify that retrieval chunks preserve both page labels and table context.

## Recovery Decision
- Decision: manual_numeric_review
- Route total/subtotal mismatches to numeric review before downstream use.
- Native extractor result has document/slide-level provenance; use PDF/MinerU path for page-layout audit.
- LLM suggested: manual_numeric_review on total mismatch
- LLM suggested: chunk_stitch_review for cross-page reference

Attempts:
- initial: pass_with_warnings (92/100), selected

## Issues
- [info] document_level_provenance: Native document input has document-level provenance rather than page-level provenance.
- [info] numeric_total_verified: A total/subtotal row matched the sum of comparable numeric rows.
- [warning] numeric_total_mismatch: A total/subtotal row does not match the sum of comparable numeric rows.

## Markdown Preview

# Cross Page Financial Control Pack

Document ID: FIN-CROSS-2026-06

Reporting Period: 2026-01-01 to 2026-03-31

Owner: Finance Shared Service Center

## Page 1 - Revenue Detail

Scenario: the table is designed to mimic a PDF where the header and subtotal continue across pages.

| Line Item | Q1 Amount | Evidence Note |
| --- | --- | --- |
| Hardware Subscription | 18400 | invoice batch A17 |
| Maintenance Service | 7250 | invoice batch B04 |
| Channel Rebate | -1380 | manual confirmation required |
| Subtotal Revenue | 24270 | first-page subtotal |

## Page 2 - Cost Detail

| Line Item | Q1 Amount | Evidence Note |
| --- | --- | --- |
| Cloud Cost | -6410 | usage statement U23 |
| Delivery Labor | -3890 | timesheet rollup |
| Support Expense | -2160 | ticket group S11 |
| Total Operating Result | 11810 | 24270 - 6410 - 3890 - 2160 |

## Audit Notes

Risk: subtotal and total rows are separated by a page break in the source PDF.

Recommendation: verify that retrieval chunks preserve both page labels and table context.
