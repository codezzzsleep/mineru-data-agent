# MinerU Data Agent Run 4a46b742ae8c

- Task: Parse a Word standard review packet, extract clauses, compliance table, dates, risks, recommendations, quality logs, recovery decision, and retrieval chunks.
- Profile: standard_or_contract
- Input: `<PROJECT_ROOT>\examples\office_files\industry_standard_review.docx`
- Quality: pass (100/100)
- Content blocks: 10
- Pages with provenance: 0
- Provenance level: document
- Sections: 3
- Tables: 1
- Key-values: 6
- Numeric facts: 3
- Dates detected: 1
- Recommendation signals: 2
- Anomaly signals: 4
- Retrieval chunks: 3
- Recovery decision: accept
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
- Document ID: DOCX-2026-STD-02
- Effective Date: 2026-05-23
- Purpose: evaluate Word document structure extraction, clause tables, risk fields, recommendations, and document-level provenance.
- Risk: missing provenance should trigger review instead of silent pass.
- Recommendation: inspect recovery_decision before exporting downstream chunks.
- Owner: Data Governance Office

## Recommendation Evidence
- Recommendation: inspect recovery_decision before exporting downstream chunks.
- Purpose: evaluate Word document structure extraction, clause tables, risk fields, recommendations, and document-level provenance.

## Recovery Decision
- Decision: accept
- Native extractor result has document/slide-level provenance; use PDF/MinerU path for page-layout audit.

## Issues
- [info] document_level_provenance: Native document input has document-level provenance rather than page-level provenance.

## Markdown Preview

# Industry Standard Review Packet

Document ID: DOCX-2026-STD-02

Effective Date: 2026-05-23

Purpose: evaluate Word document structure extraction, clause tables, risk fields, recommendations, and document-level provenance.

## 1. Compliance Matrix

| Clause | Requirement | Evidence | Risk |
| --- | --- | --- | --- |
| 1.1 | Every run must keep trace logs. | trace.json | low |
| 1.2 | Structured outputs must include tables and key-values. | result.json | medium |
| 1.3 | Warnings must not be hidden from reviewers. | quality.issues | medium |

## 2. Exception Handling

Risk: missing provenance should trigger review instead of silent pass.

Recommendation: inspect recovery_decision before exporting downstream chunks.

Owner: Data Governance Office
