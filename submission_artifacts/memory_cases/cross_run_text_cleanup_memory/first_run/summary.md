# MinerU Data Agent Run 43589089cb7d

- Schema version: 2026-05-24
- Task: 清理网页巡检日报并输出结构化结果
- Profile: general_document
- Execution method: auto
- Execution backend: pipeline
- LLM preplan applied changes: 0
- Input: `<PROJECT_ROOT>\submission_artifacts\memory_cases\cross_run_text_cleanup_memory\input.html`
- Quality: pass (100/100)
- Content blocks: 3
- Pages with provenance: 0
- Provenance level: document
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
9. Apply task intent `structured_extraction` with schema-aware extraction and verification

## Planning Rationale
- no specialized profile signal was strong enough; use general structured extraction
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
- Target schema keys: title, key_fact, evidence
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
- Initial issue codes: possible_mojibake, document_level_provenance
- text_cleanup: executed for possible_mojibake (agent_action_plan.replan_triggers)

## Agent Replan After Quality
- Issue codes: document_level_provenance
- Attempted actions: initial, text_cleanup
- Selected reason: text_cleanup had quality_status=pass and score=100

## Extracted Fields
- 报告日期: 2026-05-23

## Field Evidence
- 报告日期: confidence=0.86, location=3, evidence=报告日期：2026-05-23

## Recovery Decision
- Decision: recovered_accept
- Executed 1 automatic recovery attempt(s); selected `text_cleanup`.
- Native extractor result has document/slide-level provenance; use PDF/MinerU path for page-layout audit.
- Initial quality issues were preserved for audit: possible_mojibake, document_level_provenance.

Attempts:
- initial: pass_with_warnings (92/100), not selected
- text_cleanup: pass (100/100), selected

## Issues
- [info] document_level_provenance: Native document input has document-level provenance rather than page-level provenance.

## Markdown Preview

# 巡检日报

报告日期：2026-05-23

这是一段需要清理但仍可结构化的巡检文本。这是一段需要清理但仍可结构化的巡检文本。这是一段需要清理但仍可结构化的巡检文本。这是一段需要清理但仍可结构化的巡检文本。这是一段需要清理但仍可结构化的巡检文本。这是一段需要清理但仍可结构化的巡检文本。这是一段需要清理但仍可结构化的巡检文本。这是一段需要清理但仍可结构化的巡检文本。这是一段需要清理但仍可结构化的巡检文本。这是一段需要清理但仍可结构化的巡检文本。这是一段需要清理但仍可结构化的巡检文本。这是一段需要清理但仍可结构化的巡检文本。这是一段需要清理但仍可结构化的巡检文本。这是一段需要清理但仍可结构化的巡检文本。这是一段需要清理但仍可结构化的巡检文本。这是一段需要清理但仍可结构化的巡检文本。这是一段需要清理但仍可结构化的巡检文本。这是一段需要清理但仍可结构化的巡检文本。这是一段需要清理但仍可结构化的巡检文本。这是一段需要清理但仍可结构化的巡检文本。
