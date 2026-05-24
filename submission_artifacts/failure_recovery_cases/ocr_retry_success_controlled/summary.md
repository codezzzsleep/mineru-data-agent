> Boundary: controlled fake MinerU runner; validates retry selection logic, not live OCR quality.

# MinerU Data Agent Run 40786b721414

- Task: 解析稀疏 PDF；初始文本过短时切到 OCR。
- Profile: general_document
- Execution method: auto
- Execution backend: pipeline
- LLM preplan applied changes: 0
- Input: `<PROJECT_ROOT>\runs\failure_recovery_cases\_inputs\ocr_retry_success_controlled.pdf`
- Quality: pass (100/100)
- Content blocks: 1
- Pages with provenance: 1
- Provenance level: page
- Sections: 1
- Tables: 0
- Key-values: 1
- Field evidence records: 1
- Numeric facts: 0
- Dates detected: 1
- Recommendation signals: 0
- Anomaly signals: 0
- Retrieval chunks: 1
- Recovery decision: recovered_accept
- Recovery selected attempt: ocr_retry
- Recovery attempts: 2
- Task intents: structured_extraction
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
9. Apply task intent `structured_extraction` with schema-aware extraction and verification

## Planning Rationale
- no specialized profile signal was strong enough; use general structured extraction
- local MinerU CLI is selected when full artifacts and page-level provenance are required
- backend=pipeline is used for MinerU parsing when the selected runner calls MinerU
- method=auto balances automatic parsing with OCR fallback when quality gates require it
- lang=ch is passed to MinerU or recorded for native extraction audit
- Recovery policy:
  - text_cleanup if mojibake or encoding noise is detected
  - ocr_retry for PDF/image results with blocking extraction or OCR-related quality issues
  - cli_fallback when online API lacks page-level provenance and a local MinerU CLI is available
  - manual_numeric_review when subtotal/total consistency checks fail

## Adaptive Task Decision
- Intents: structured_extraction
- Target schema keys: title, key_fact, evidence
- Quality thresholds: {"min_quality_score": 80, "require_tables": false, "require_numeric_facts": false, "prefer_page_provenance": true}
- Recovery strategy:
  - cli_fallback on online_api_missing_page_provenance (normal)
  - ocr_retry on empty_or_sparse_text_or_ocr_quality_issue (normal)
  - text_cleanup on mojibake_or_encoding_noise (normal)

## Agent Action Plan
- Subtasks: 6
- Selected tools: mineru_cli, structured_extractor, text_cleanup, ocr_retry, retrieval_exporter
- understand_task: Classify the document task and identify intent-specific outputs.
- choose_parse_path: Pick the cheapest parser path that still preserves required provenance.
- extract_structure: Normalize sections, tables, key-values, numeric facts, and field evidence.
- validate_quality: Run profile and task-specific gates before accepting the result.
- replan_if_needed: Map quality issues to recovery actions and select the best attempt.
- export_artifacts: Write result, trace, summary, and retrieval artifacts.

## Runtime Recovery Plan
- Initial issue codes: short_text
- ocr_retry: executed for short_text (agent_action_plan.replan_triggers)

## Agent Replan After Quality
- Issue codes: none
- Attempted actions: initial, ocr_retry
- Selected reason: ocr_retry had quality_status=pass and score=100

## Extracted Fields
- 报告日期: 2026-05-24

## Field Evidence
- 报告日期: confidence=0.95, location=1, evidence=# OCR Recovery 报告日期：2026-05-24 OCR recovery produced page-level text. OCR recovery produced page-level text. OCR recovery produced page-level text. OCR recovery produced page-level text. OCR recovery produced page-level text. OCR recovery produced page-level text. OCR recovery produced page-level te

## Recovery Decision
- Decision: recovered_accept
- Executed 1 automatic recovery attempt(s); selected `ocr_retry`.
- Initial quality issues were preserved for audit: short_text.

Attempts:
- initial: pass_with_warnings (92/100), not selected
- ocr_retry: pass (100/100), selected

## Issues
- No blocking issues detected.

## Markdown Preview

# OCR Recovery

报告日期：2026-05-24

OCR recovery produced page-level text. OCR recovery produced page-level text. OCR recovery produced page-level text. OCR recovery produced page-level text. OCR recovery produced page-level text. OCR recovery produced page-level text. OCR recovery produced page-level text. OCR recovery produced page-level text. OCR recovery produced page-level text. OCR recovery produced page-level text. OCR recovery produced page-level text. OCR recovery produced page-level text. OCR recovery produced page-level text. OCR recovery produced page-level text. OCR recovery produced page-level text. OCR recovery produced page-level text. OCR recovery produced page-level text. OCR recovery produced page-level text. OCR recovery produced page-level text. OCR recovery produced page-level text. OCR recovery produced page-level text. OCR recovery produced page-level text. OCR recovery produced page-level text. OCR recovery produced page-level text.
