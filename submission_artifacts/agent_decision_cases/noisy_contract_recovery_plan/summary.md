# MinerU Data Agent Run 297caca18acf

- Task: 解析 OCR 噪声合同，抽取合同编号、双方和日期；如果有乱码，先清理后再接受。
- Profile: low_quality_ocr
- Execution method: auto
- Execution backend: pipeline
- LLM preplan applied changes: 1
- Input: `<PROJECT_ROOT>\examples\challenge_cases\case_7_noisy_contract_scan.html`
- Quality: pass (100/100)
- Content blocks: 11
- Pages with provenance: 0
- Provenance level: document
- Sections: 3
- Tables: 1
- Key-values: 4
- Field evidence records: 4
- Numeric facts: 2
- Dates detected: 1
- Recommendation signals: 1
- Anomaly signals: 3
- Retrieval chunks: 4
- Recovery decision: recovered_accept
- Recovery selected attempt: text_cleanup
- Recovery attempts: 2
- Task intents: structured_extraction
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
9. Prioritize OCR confidence proxies, mojibake/noise checks, and sparse-text detection
10. Plan OCR/VLM fallback before accepting low-evidence outputs
11. Apply task intent `structured_extraction` with schema-aware extraction and verification
12. LLM preplan: Decompose task into extraction, validation, and recovery decisions
13. LLM preplan: Select tools based on profile, provenance need, and quality risks

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
- Target schema keys: recognized_text, noise_signal, critical_field, recovery_action, evidence, 合同编号, 双方, 签署日期
- Quality thresholds: {"min_quality_score": 80, "require_tables": false, "require_numeric_facts": false, "prefer_page_provenance": false}
- Recovery strategy:
  - text_cleanup on mojibake_or_encoding_noise (normal)
  - llm_suggested_review on run text_cleanup when possible_mojibake appears (advisory)

## Agent Action Plan
- Subtasks: 7
- Selected tools: native_extractor, llm_preplanner, structured_extractor, text_cleanup, llm_post_review, retrieval_exporter
- understand_task: Classify the document task and identify intent-specific outputs.
- choose_parse_path: Pick the cheapest parser path that still preserves required provenance.
- extract_structure: Normalize sections, tables, key-values, numeric facts, and field evidence.
- validate_quality: Run profile and task-specific gates before accepting the result.
- llm_review: Review parse output against task-specific risks and propose follow-up actions.
- replan_if_needed: Map quality issues to recovery actions and select the best attempt.

## Agent Replan After Quality
- Issue codes: document_level_provenance
- Attempted actions: initial, text_cleanup
- Selected reason: text_cleanup had quality_status=pass and score=100

## LLM Agent Analysis

Pre-execution control: profile=low_quality_ocr, runner=native, method=ocr, backend=pipeline
Applied LLM control changes:
- profile: standard_or_contract -> low_quality_ocr

解析 OCR 噪声合同，抽取合同编号、双方和日期；如果有乱码，先清理后再接受。

LLM usage: 1460 tokens across 2 call(s); estimated cost=None

Suggested execution plan:
1. Review quality issues
2. Map issue codes to replan actions

## Extracted Fields
- Contract No: OCR-NOISE-2026-17
- Effective Date: 2026-05-21
- Parties: North Data Plant / Edge Review Vendor
- Recommendation: run cleanup first, then preserve the initial issues in recovery_decision.initial_issue_codes.

## Field Evidence
- Contract No: confidence=0.86, location=3, evidence=Contract No: OCR-NOISE-2026-17
- Effective Date: confidence=0.86, location=5, evidence=Effective Date: 2026-05-21
- Parties: confidence=0.86, location=7, evidence=Parties: North Data Plant / Edge Review Vendor
- Recommendation: confidence=0.86, location=25, evidence=Recommendation: run cleanup first, then preserve the initial issues in recovery_decision.initial_issue_codes.

## Recommendation Evidence
- Recommendation: run cleanup first, then preserve the initial issues in recovery_decision.initial_issue_codes.

## Recovery Decision
- Decision: recovered_accept
- Executed 1 automatic recovery attempt(s); selected `text_cleanup`.
- Native extractor result has document/slide-level provenance; use PDF/MinerU path for page-layout audit.
- Initial quality issues were preserved for audit: possible_mojibake, document_level_provenance.
- LLM suggested: run text_cleanup when possible_mojibake appears

Attempts:
- initial: pass_with_warnings (92/100), not selected
- text_cleanup: pass (100/100), selected

## Issues
- [info] document_level_provenance: Native document input has document-level provenance rather than page-level provenance.

## Markdown Preview

# Noisy Contract Scan Review

Contract No: OCR-NOISE-2026-17

Effective Date: 2026-05-21

Parties: North Data Plant / Edge Review Vendor

## 1. OCR Observations

Scanned source has skewed stamp overlap, repeated watermark text, and several mojibake-like fragments: ®.

Clause 2.1 requires every page to keep parse logs and reviewer notes.

Clause 2.2 requires recovery suggestions when provenance is weak.

## 2. Risk Table

| Risk ID | Description | Expected Handling |
| --- | --- | --- |
| R-01 | stamp overlaps signature field | manual review |
| R-02 | encoding noise appears in clause text | text cleanup recovery |
| R-03 | watermark repeated in footer | noise filtering |

Recommendation: run cleanup first, then preserve the initial issues in recovery_decision.initial_issue_codes.
