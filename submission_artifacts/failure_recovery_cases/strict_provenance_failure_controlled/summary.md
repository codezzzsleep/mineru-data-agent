> Boundary: controlled fake online-API runner; validates strict provenance gate without claiming live API behavior.

# MinerU Data Agent Run 5d9be5a86a3b

- Task: 解析 PDF，并要求字段能追溯到页级来源。
- Profile: standard_or_contract
- Execution method: auto
- Execution backend: pipeline
- LLM preplan applied changes: 0
- Input: `<PROJECT_ROOT>\runs\failure_recovery_cases\_inputs\strict_provenance_failure_controlled.pdf`
- Quality: needs_review (54/100)
- Content blocks: 3
- Pages with provenance: 0
- Provenance level: document
- Sections: 1
- Tables: 0
- Key-values: 1
- Field evidence records: 1
- Numeric facts: 0
- Dates detected: 0
- Recommendation signals: 0
- Anomaly signals: 0
- Retrieval chunks: 1
- Recovery decision: strict_page_provenance_failed
- Recovery selected attempt: initial
- Recovery attempts: 1
- Task intents: evidence_trace
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
11. Apply task intent `evidence_trace` with schema-aware extraction and verification

## Planning Rationale
- standard/contract keywords or explicit profile require section and clause preservation
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
- Intents: evidence_trace
- Target schema keys: document_title, parties, clause_id, obligation, effective_date, evidence
- Quality thresholds: {"min_quality_score": 88, "require_tables": false, "require_numeric_facts": false, "prefer_page_provenance": true}
- Recovery strategy:
  - cli_fallback on online_api_missing_page_provenance (high)
  - ocr_retry on empty_or_sparse_text_or_ocr_quality_issue (normal)
  - text_cleanup on mojibake_or_encoding_noise (normal)

## Agent Action Plan
- Subtasks: 6
- Selected tools: mineru_cli, structured_extractor, contract_validator, text_cleanup, ocr_retry, retrieval_exporter
- understand_task: Classify the document task and identify intent-specific outputs.
- choose_parse_path: Pick the cheapest parser path that still preserves required provenance.
- extract_structure: Normalize sections, tables, key-values, numeric facts, and field evidence.
- validate_quality: Run profile and task-specific gates before accepting the result.
- replan_if_needed: Map quality issues to recovery actions and select the best attempt.
- export_artifacts: Write result, trace, summary, and retrieval artifacts.

## Agent Replan After Quality
- Issue codes: no_page_provenance, weak_clause_structure, strict_page_provenance_failed
- Attempted actions: initial
- Selected reason: initial result remained the best accepted quality attempt

## Task-Specific Answers

## Extracted Fields
- Contract No: STRICT-001

## Field Evidence
- Contract No: confidence=0.86, location=3, evidence=Contract No: STRICT-001

## Recovery Decision
- Decision: strict_page_provenance_failed
- Use local MinerU CLI when page-level provenance is required.
- Strict page provenance was requested; treat this as a partial result until a CLI/provider path emits page evidence.

Attempts:
- initial: pass_with_warnings (84/100), selected

## Issues
- [warning] no_page_provenance: Content blocks were extracted, but no page-level provenance is available.
- [warning] weak_clause_structure: Standard/contract profile expects clearer section hierarchy.
- [error] strict_page_provenance_failed: Strict page provenance was requested, but the selected result still lacks page-level provenance.

## Markdown Preview

# Contract

Contract No: STRICT-001

Document-level text without page evidence. Document-level text without page evidence. Document-level text without page evidence. Document-level text without page evidence. Document-level text without page evidence. Document-level text without page evidence. Document-level text without page evidence. Document-level text without page evidence. Document-level text without page evidence. Document-level text without page evidence. Document-level text without page evidence. Document-level text without page evidence. Document-level text without page evidence. Document-level text without page evidence. Document-level text without page evidence. Document-level text without page evidence. Document-level text without page evidence. Document-level text without page evidence.
