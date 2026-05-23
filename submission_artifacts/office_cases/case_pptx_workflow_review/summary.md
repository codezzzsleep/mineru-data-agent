# MinerU Data Agent Run d8eea5507bd5

- Task: Parse a PowerPoint workflow review deck, extract slide-level text, execution matrix, risks, recommendations, quality logs, recovery decision, and retrieval chunks.
- Profile: workflow_or_diagram
- Input: `<PROJECT_ROOT>\examples\office_files\workflow_agent_review.pptx`
- Quality: pass (100/100)
- Content blocks: 7
- Pages with provenance: 3
- Provenance level: page
- Sections: 3
- Tables: 1
- Key-values: 5
- Numeric facts: 6
- Dates detected: 1
- Recommendation signals: 2
- Anomaly signals: 2
- Retrieval chunks: 4
- Recovery decision: accept
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
- Inspection Date: 2026-05-23
- Goal: verify slide-level provenance, execution matrices, and recovery notes.
- Anomaly: slide decks often lose section order during plain text extraction.
- Recommendation: preserve slide index and table rows in content blocks.
- Risk: charts still require a visual model follow-up.

## Recommendation Evidence
- Recommendation: preserve slide index and table rows in content blocks.
- Anomaly: slide decks often lose section order during plain text extraction.

## Recovery Decision
- Decision: accept
- Native extractor result has document/slide-level provenance; use PDF/MinerU path for page-layout audit.

## Issues
- No blocking issues detected.

## Markdown Preview

# Slide 1

Workflow Agent Review
Inspection Date: 2026-05-23
Goal: verify slide-level provenance, execution matrices, and recovery notes.

# Slide 2

Execution Matrix

| Step | Tool | Output | Recovery |
| --- | --- | --- | --- |
| 1 | Native PPTX extractor | slide text | keep slide index |
| 2 | Validator | quality report | flag warnings |
| 3 | Retrieval exporter | jsonl chunks | skip noise |

# Slide 3

Findings
Anomaly: slide decks often lose section order during plain text extraction.
Recommendation: preserve slide index and table rows in content blocks.
Risk: charts still require a visual model follow-up.
