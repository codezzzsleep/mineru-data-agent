# MinerU Data Agent Run e4de9c3c7280

- Schema version: 2026-05-24
- Task: Parse an industry standard compliance matrix, extract standard id, owner, requirements, severity, exception rules, quality logs, and retrieval chunks.
- Profile: standard_or_contract
- Execution method: auto
- Execution backend: pipeline
- LLM preplan applied changes: 0
- Input: `<PROJECT_ROOT>\examples\challenge_cases\case_8_industry_standard_matrix.html`
- Quality: pass (100/100)
- Content blocks: 11
- Pages with provenance: 0
- Provenance level: document
- Sections: 4
- Tables: 1
- Key-values: 6
- Field evidence records: 6
- Numeric facts: 0
- Dates detected: 1
- Recommendation signals: 1
- Anomaly signals: 1
- Retrieval chunks: 4
- Recovery decision: accept
- Recovery selected attempt: initial
- Recovery attempts: 1
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
9. Prioritize section hierarchy, clause-like paragraphs, parties, obligations, and dates
10. Preserve source page or document heading evidence for each clause
11. Apply task intent `structured_extraction` with schema-aware extraction and verification

## Planning Rationale
- standard/contract keywords or explicit profile require section and clause preservation
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
- Target schema keys: document_title, parties, clause_id, obligation, effective_date, evidence
- Quality thresholds: {"min_quality_score": 80, "require_tables": false, "require_numeric_facts": false, "prefer_page_provenance": false}
- Recovery strategy:
  - text_cleanup on mojibake_or_encoding_noise (normal)

## Agent Action Plan
- Subtasks: 6
- Selected tools: native_extractor, structured_extractor, contract_validator, text_cleanup, retrieval_exporter
- understand_task: Classify the document task and identify intent-specific outputs.
- choose_parse_path: Pick the cheapest parser path that still preserves required provenance.
- extract_structure: Normalize sections, tables, key-values, numeric facts, and field evidence.
- validate_quality: Run profile and task-specific gates before accepting the result.
- replan_if_needed: Map quality issues to recovery actions and select the best attempt.
- export_artifacts: Write result, trace, summary, and retrieval artifacts.

## Runtime Recovery Plan
- Initial issue codes: document_level_provenance

## Agent Replan After Quality
- Issue codes: document_level_provenance
- Attempted actions: initial
- Selected reason: initial result remained the best accepted quality attempt

## Extracted Fields
- Standard ID: STD-MATRIX-2026-09
- Review Date: 2026-05-22
- Owner: Quality Engineering Office
- Risk: if an online parser lacks page provenance, the agent must either fallback to CLI or mark the result as review-only.
- Recommendation: link this standard check to the PDF recovery evidence where executed=true is already recorded.
- 1. Scope: This standard defines traceability requirements for document parsing agents used in corpus production.

## Field Evidence
- Standard ID: confidence=0.86, location=3, evidence=Standard ID: STD-MATRIX-2026-09
- Review Date: confidence=0.86, location=5, evidence=Review Date: 2026-05-22
- Owner: confidence=0.86, location=7, evidence=Owner: Quality Engineering Office
- Risk: confidence=0.86, location=24, evidence=Risk: if an online parser lacks page provenance, the agent must either fallback to CLI or mark the result as review-only.
- Recommendation: confidence=0.86, location=26, evidence=Recommendation: link this standard check to the PDF recovery evidence where executed=true is already recorded.

## Recommendation Evidence
- Recommendation: link this standard check to the PDF recovery evidence where executed=true is already recorded.

## Recovery Decision
- Decision: accept
- Native extractor result has document/slide-level provenance; use PDF/MinerU path for page-layout audit.

Attempts:
- initial: pass (100/100), selected

## Issues
- [info] document_level_provenance: Native document input has document-level provenance rather than page-level provenance.

## Markdown Preview

# Industry Standard Compliance Matrix

Standard ID: STD-MATRIX-2026-09

Review Date: 2026-05-22

Owner: Quality Engineering Office

## 1. Scope

This standard defines traceability requirements for document parsing agents used in corpus production.

## 2. Compliance Matrix

| Requirement | Mandatory Evidence | Severity | Review Note |
| --- | --- | --- | --- |
| REQ-1 | trace.json includes every tool call | high | must include retries |
| REQ-2 | result.json includes structured sections | high | must include tables |
| REQ-3 | retrieval manifest includes page coverage | medium | pages field required |
| REQ-4 | secret scan excludes API keys | critical | block release if failed |

## 3. Exception Rule

Risk: if an online parser lacks page provenance, the agent must either fallback to CLI or mark the result as review-only.

Recommendation: link this standard check to the PDF recovery evidence where executed=true is already recorded.
