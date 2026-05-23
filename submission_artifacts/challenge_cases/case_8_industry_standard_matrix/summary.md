# MinerU Data Agent Run c62b72d418ea

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
- Key-values: 5
- Numeric facts: 0
- Dates detected: 1
- Recommendation signals: 1
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
6. Prioritize section hierarchy and clause-like paragraph extraction
7. Preserve source page or document heading evidence for each clause

## Extracted Fields
- Standard ID: STD-MATRIX-2026-09
- Review Date: 2026-05-22
- Owner: Quality Engineering Office
- Risk: if an online parser lacks page provenance, the agent must either fallback to CLI or mark the result as review-only.
- Recommendation: link this standard check to the PDF recovery evidence where executed=true is already recorded.

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
