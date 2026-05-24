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