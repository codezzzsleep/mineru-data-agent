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