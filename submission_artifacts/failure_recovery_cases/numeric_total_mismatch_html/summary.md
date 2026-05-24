> Boundary: native HTML controlled fixture; validates numeric mismatch detection.

# MinerU Data Agent Run 9742489ae255

- Task: 检查财报表格总计是否一致，并标记人工复核项。
- Profile: financial_report
- Execution method: auto
- Execution backend: pipeline
- LLM preplan applied changes: 0
- Input: `<PROJECT_ROOT>\runs\failure_recovery_cases\_inputs\numeric_total_mismatch_html.html`
- Quality: pass_with_warnings (92/100)
- Content blocks: 3
- Pages with provenance: 0
- Provenance level: document
- Sections: 1
- Tables: 1
- Key-values: 3
- Field evidence records: 3
- Numeric facts: 3
- Dates detected: 0
- Recommendation signals: 0
- Anomaly signals: 0
- Retrieval chunks: 2
- Recovery decision: manual_numeric_review
- Recovery selected attempt: initial
- Recovery attempts: 1
- Task intents: aggregation
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
12. Apply task intent `aggregation` with schema-aware extraction and verification

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
- Intents: aggregation
- Target schema keys: company_name, report_period, line_item, current_value, previous_value, unit, evidence
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
- Initial issue codes: document_level_provenance, numeric_total_mismatch
- manual_numeric_review: skipped for numeric_total_mismatch (agent_action_plan.replan_triggers)

## Agent Replan After Quality
- Issue codes: document_level_provenance, numeric_total_mismatch
- Attempted actions: initial
- Selected reason: initial result remained the best accepted quality attempt

## Task-Specific Answers

## Extracted Fields
- 硬件收入: 100
- 软件收入: 200
- 合计: 400

## Field Evidence
- 硬件收入: confidence=0.86, location=5, evidence=| 项目 | 金额 | | --- | --- | | 硬件收入 | 100 | | 软件收入 | 200 | | 合计 | 400 |
- 软件收入: confidence=0.86, location=6, evidence=| 项目 | 金额 | | --- | --- | | 硬件收入 | 100 | | 软件收入 | 200 | | 合计 | 400 |
- 合计: confidence=0.86, location=7, evidence=| 项目 | 金额 | | --- | --- | | 硬件收入 | 100 | | 软件收入 | 200 | | 合计 | 400 |

## Recovery Decision
- Decision: manual_numeric_review
- Route total/subtotal mismatches to numeric review before downstream use.
- Native extractor result has document/slide-level provenance; use PDF/MinerU path for page-layout audit.

Attempts:
- initial: pass_with_warnings (92/100), selected

## Issues
- [info] document_level_provenance: Native document input has document-level provenance rather than page-level provenance.
- [warning] numeric_total_mismatch: A total/subtotal row does not match the sum of comparable numeric rows.

## Markdown Preview

# 财报总计校验负样本

| 项目 | 金额 |
| --- | --- |
| 硬件收入 | 100 |
| 软件收入 | 200 |
| 合计 | 400 |

本样本故意让合计行不等于明细行之和，用于验证 numeric_total_mismatch。
