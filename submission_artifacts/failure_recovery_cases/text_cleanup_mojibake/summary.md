> Boundary: native HTML controlled fixture; validates text cleanup recovery path.

# MinerU Data Agent Run c8075b57983d

- Schema version: 2026-05-24
- Task: 清理 OCR 噪声合同并保留质量问题。
- Profile: low_quality_ocr
- Execution method: auto
- Execution backend: pipeline
- LLM preplan applied changes: 0
- Input: `<PROJECT_ROOT>\runs\failure_recovery_cases\_inputs\text_cleanup_mojibake.html`
- Quality: pass_with_warnings (92/100)
- Content blocks: 4
- Pages with provenance: 0
- Provenance level: document
- Sections: 1
- Tables: 0
- Key-values: 2
- Field evidence records: 2
- Numeric facts: 0
- Dates detected: 1
- Recommendation signals: 0
- Anomaly signals: 0
- Retrieval chunks: 1
- Recovery decision: recovered_with_review_notes
- Recovery selected attempt: text_cleanup
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
9. Prioritize OCR confidence proxies, mojibake/noise checks, and sparse-text detection
10. Plan OCR/VLM fallback before accepting low-evidence outputs
11. Apply task intent `structured_extraction` with schema-aware extraction and verification

## Planning Rationale
- scan/OCR/low-quality keywords or explicit profile require OCR/noise checks and recovery readiness
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
- Intents: structured_extraction
- Target schema keys: recognized_text, noise_signal, critical_field, recovery_action, evidence
- Quality thresholds: {"min_quality_score": 80, "require_tables": false, "require_numeric_facts": false, "prefer_page_provenance": false}
- Recovery strategy:
  - text_cleanup on mojibake_or_encoding_noise (normal)

## Agent Action Plan
- Subtasks: 6
- Selected tools: native_extractor, structured_extractor, text_cleanup, retrieval_exporter
- understand_task: Classify the document task and identify intent-specific outputs.
- choose_parse_path: Pick the cheapest parser path that still preserves required provenance.
- extract_structure: Normalize sections, tables, key-values, numeric facts, and field evidence.
- validate_quality: Run profile and task-specific gates before accepting the result.
- replan_if_needed: Map quality issues to recovery actions and select the best attempt.
- export_artifacts: Write result, trace, summary, and retrieval artifacts.

## Runtime Recovery Plan
- Initial issue codes: possible_mojibake, document_level_provenance, expected_anomaly_signal_missing
- text_cleanup: executed for possible_mojibake (agent_action_plan.replan_triggers)

## Agent Replan After Quality
- Issue codes: document_level_provenance, expected_anomaly_signal_missing
- Attempted actions: initial, text_cleanup
- Selected reason: text_cleanup had quality_status=pass_with_warnings and score=92

## Extracted Fields
- 合同编号: NOISE-001
- 签署日期: 2026-05-24

## Field Evidence
- 合同编号: confidence=0.86, location=3, evidence=合同编号：NOISE-001
- 签署日期: confidence=0.86, location=5, evidence=签署日期：2026-05-24

## Recovery Decision
- Decision: recovered_with_review_notes
- Executed 1 automatic recovery attempt(s); selected `text_cleanup`.
- Native extractor result has document/slide-level provenance; use PDF/MinerU path for page-layout audit.
- Initial quality issues were preserved for audit: possible_mojibake, document_level_provenance, expected_anomaly_signal_missing.

Attempts:
- initial: pass_with_warnings (84/100), not selected
- text_cleanup: pass_with_warnings (92/100), selected

## Issues
- [info] document_level_provenance: Native document input has document-level provenance rather than page-level provenance.
- [warning] expected_anomaly_signal_missing: Task asks for anomalies/risks, but no anomaly-like evidence was extracted.

## Markdown Preview

# OCR 噪声合同

合同编号：NOISE-001

签署日期：2026-05-24

需要清理的合同正文。 需要清理的合同正文。 需要清理的合同正文。 需要清理的合同正文。 需要清理的合同正文。 需要清理的合同正文。 需要清理的合同正文。 需要清理的合同正文。 需要清理的合同正文。 需要清理的合同正文。 需要清理的合同正文。 需要清理的合同正文。 需要清理的合同正文。 需要清理的合同正文。 需要清理的合同正文。 需要清理的合同正文。 需要清理的合同正文。 需要清理的合同正文。 需要清理的合同正文。 需要清理的合同正文。 需要清理的合同正文。 需要清理的合同正文。 需要清理的合同正文。 需要清理的合同正文。 需要清理的合同正文。 需要清理的合同正文。 需要清理的合同正文。 需要清理的合同正文。 需要清理的合同正文。 需要清理的合同正文。 需要清理的合同正文。 需要清理的合同正文。 需要清理的合同正文。 需要清理的合同正文。 需要清理的合同正文。 需要清理的合同正文。
