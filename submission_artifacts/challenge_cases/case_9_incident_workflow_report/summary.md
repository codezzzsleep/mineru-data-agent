# MinerU Data Agent Run 849d14871926

- Task: Parse an incident workflow report, extract incident id, timeline, fallback actions, risks, recommendations, recovery verification targets, trace, and retrieval chunks.
- Profile: workflow_or_diagram
- Execution method: auto
- Execution backend: pipeline
- LLM preplan applied changes: 0
- Input: `<PROJECT_ROOT>\examples\challenge_cases\case_9_incident_workflow_report.html`
- Quality: pass (100/100)
- Content blocks: 13
- Pages with provenance: 0
- Provenance level: document
- Sections: 4
- Tables: 1
- Key-values: 9
- Field evidence records: 9
- Numeric facts: 3
- Dates detected: 1
- Recommendation signals: 2
- Anomaly signals: 1
- Retrieval chunks: 4
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
9. Prioritize figure/image references, ordered procedural statements, actors, inputs, and outputs
10. Flag pages that need visual model follow-up
11. Apply task intent `anomaly_detection` with schema-aware extraction and verification
12. Apply task intent `evidence_trace` with schema-aware extraction and verification

## Planning Rationale
- workflow/diagram keywords or explicit profile require procedural and figure evidence
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
- Target schema keys: process_name, step, actor, input_output, risk, evidence, risk_reason
- Quality thresholds: {"min_quality_score": 88, "require_tables": false, "require_numeric_facts": false, "prefer_page_provenance": false}
- Recovery strategy:
  - text_cleanup on mojibake_or_encoding_noise (normal)

## Agent Action Plan
- Subtasks: 6
- Selected tools: native_extractor, structured_extractor, workflow_validator, text_cleanup, retrieval_exporter
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

## Task-Specific Answers
- Anomaly candidates: 1

## Extracted Fields
- Incident ID: OPS-INC-2026-0519
- Report Date: 2026-05-23
- System: document ingestion and validation pipeline
- | 09: 10 | API parser returned document-level provenance | Agent | trigger fallback policy |
- | 09: 12 | CLI artifact restored page-level evidence | Parser | select cli_fallback attempt |
- | 09: 15 | quality gate passed | Validator | archive result and trace |
- Risk: online API Markdown can be structurally useful but insufficient for page-level audit.
- Recommendation: route no_page_provenance to CLI fallback when a CLI environment is available.

## Field Evidence
- Incident ID: confidence=0.86, location=3, evidence=Incident ID: OPS-INC-2026-0519
- Report Date: confidence=0.86, location=5, evidence=Report Date: 2026-05-23
- System: confidence=0.86, location=7, evidence=System: document ingestion and validation pipeline
- | 09: confidence=0.86, location=13, evidence=| Time | Event | Owner | Action | | --- | --- | --- | --- | | 09:10 | API parser returned document-level provenance | Agent | trigger fallback policy | | 09:12 | CLI artifact restored page-level evidence | Parser | select cli_fallback attempt | | 09:15 | quality gate passed | Validator | archive res
- | 09: confidence=0.86, location=14, evidence=| Time | Event | Owner | Action | | --- | --- | --- | --- | | 09:10 | API parser returned document-level provenance | Agent | trigger fallback policy | | 09:12 | CLI artifact restored page-level evidence | Parser | select cli_fallback attempt | | 09:15 | quality gate passed | Validator | archive res

## Recommendation Evidence
- Recommendation: route no_page_provenance to CLI fallback when a CLI environment is available.
- | Time | Event | Owner | Action |

## Recovery Decision
- Decision: accept
- Native extractor result has document/slide-level provenance; use PDF/MinerU path for page-layout audit.

Attempts:
- initial: pass (100/100), selected

## Issues
- [info] document_level_provenance: Native document input has document-level provenance rather than page-level provenance.

## Markdown Preview

# Incident Workflow Report

Incident ID: OPS-INC-2026-0519

Report Date: 2026-05-23

System: document ingestion and validation pipeline

## 1. Timeline

| Time | Event | Owner | Action |
| --- | --- | --- | --- |
| 09:10 | API parser returned document-level provenance | Agent | trigger fallback policy |
| 09:12 | CLI artifact restored page-level evidence | Parser | select cli_fallback attempt |
| 09:15 | quality gate passed | Validator | archive result and trace |

## 2. Root Cause

Risk: online API Markdown can be structurally useful but insufficient for page-level audit.

Recommendation: route no_page_provenance to CLI fallback when a CLI environment is available.

## 3. Verification Targets

- the separate PDF recovery evidence must show recovery_decision.executed=true

- the separate PDF recovery evidence must show selected_attempt=cli_fallback

- the separate PDF recovery trace must keep both parser attempts
