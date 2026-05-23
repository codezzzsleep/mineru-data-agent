# MinerU Data Agent Run ee0d71622431

- Task: Parse an OCR-noisy contract scan review, clean mojibake fragments, preserve initial quality issues, extract contract metadata, risk table, recommendations, trace, and retrieval chunks.
- Profile: low_quality_ocr
- Execution method: auto
- Execution backend: pipeline
- LLM preplan applied changes: 0
- Input: `<PROJECT_ROOT>\examples\challenge_cases\case_7_noisy_contract_scan.html`
- Quality: pass (100/100)
- Content blocks: 11
- Pages with provenance: 0
- Provenance level: document
- Sections: 3
- Tables: 1
- Key-values: 4
- Numeric facts: 2
- Dates detected: 1
- Recommendation signals: 1
- Anomaly signals: 3
- Retrieval chunks: 4
- Recovery decision: recovered_accept
- Recovery selected attempt: text_cleanup
- Recovery attempts: 2
- LLM analysis: disabled

## Plan
1. Inspect input type and task objective
2. Parse document with MinerU or native HTML extractor
3. Normalize content blocks with page-level or document-level provenance
4. Build markdown, section, key-value, table, and numeric views
5. Run quality checks and produce traceable logs
6. Prioritize OCR confidence proxies and mojibake/noise checks
7. Flag pages with sparse extracted text for manual or VLM fallback

## Extracted Fields
- Contract No: OCR-NOISE-2026-17
- Effective Date: 2026-05-21
- Parties: North Data Plant / Edge Review Vendor
- Recommendation: run cleanup first, then preserve the initial issues in recovery_decision.initial_issue_codes.

## Recommendation Evidence
- Recommendation: run cleanup first, then preserve the initial issues in recovery_decision.initial_issue_codes.

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
