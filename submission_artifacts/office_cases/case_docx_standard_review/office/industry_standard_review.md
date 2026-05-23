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