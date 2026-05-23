# MinerU Data Agent Run 591a12766ed6

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
- Key-values: 8
- Numeric facts: 3
- Dates detected: 1
- Recommendation signals: 2
- Anomaly signals: 1
- Retrieval chunks: 4
- Recovery decision: accept
- Recovery selected attempt: initial
- Recovery attempts: 1
- LLM analysis: disabled

## Plan
1. Inspect input type and task objective
2. Parse document with MinerU or native HTML extractor
3. Normalize content blocks with page-level or document-level provenance
4. Build markdown, section, key-value, table, and numeric views
5. Run quality checks and produce traceable logs
6. Prioritize figure/image references and ordered procedural statements
7. Flag pages that need visual model follow-up

## Extracted Fields
- Incident ID: OPS-INC-2026-0519
- Report Date: 2026-05-23
- System: document ingestion and validation pipeline
- | 09: 10 | API parser returned document-level provenance | Agent | trigger fallback policy |
- | 09: 12 | CLI artifact restored page-level evidence | Parser | select cli_fallback attempt |
- | 09: 15 | quality gate passed | Validator | archive result and trace |
- Risk: online API Markdown can be structurally useful but insufficient for page-level audit.
- Recommendation: route no_page_provenance to CLI fallback when a CLI environment is available.

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
