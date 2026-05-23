# MinerU Data Agent Run 58d40cd48116

- Task: Parse a cross-page-style financial control pack, extract document id, owner, tables, subtotal/total evidence, risks, recommendations, trace, and retrieval chunks.
- Profile: financial_report
- Execution method: auto
- Execution backend: pipeline
- LLM preplan applied changes: 0
- Input: `<PROJECT_ROOT>\examples\challenge_cases\case_6_cross_page_financial_table.html`
- Quality: pass_with_warnings (92/100)
- Content blocks: 12
- Pages with provenance: 0
- Provenance level: document
- Sections: 4
- Tables: 2
- Key-values: 6
- Numeric facts: 10
- Dates detected: 2
- Recommendation signals: 1
- Anomaly signals: 1
- Retrieval chunks: 5
- Recovery decision: manual_numeric_review
- Recovery selected attempt: initial
- Recovery attempts: 1
- LLM analysis: disabled

## Plan
1. Inspect input type and task objective
2. Parse document with MinerU or native HTML extractor
3. Normalize content blocks with page-level or document-level provenance
4. Build markdown, section, key-value, table, and numeric views
5. Run quality checks and produce traceable logs
6. Prioritize dense table extraction and numeric consistency checks
7. Flag subtotal/total rows and suspicious numeric cells

## Extracted Fields
- Document ID: FIN-CROSS-2026-06
- Reporting Period: 2026-01-01 to 2026-03-31
- Owner: Finance Shared Service Center
- Scenario: the table is designed to mimic a PDF where the header and subtotal continue across pages.
- Risk: subtotal and total rows are separated by a page break in the source PDF.
- Recommendation: verify that retrieval chunks preserve both page labels and table context.

## Recommendation Evidence
- Recommendation: verify that retrieval chunks preserve both page labels and table context.

## Recovery Decision
- Decision: manual_numeric_review
- Route total/subtotal mismatches to numeric review before downstream use.
- Native extractor result has document/slide-level provenance; use PDF/MinerU path for page-layout audit.

Attempts:
- initial: pass_with_warnings (92/100), selected

## Issues
- [info] document_level_provenance: Native document input has document-level provenance rather than page-level provenance.
- [info] numeric_total_verified: A total/subtotal row matched the sum of comparable numeric rows.
- [warning] numeric_total_mismatch: A total/subtotal row does not match the sum of comparable numeric rows.

## Markdown Preview

# Cross Page Financial Control Pack

Document ID: FIN-CROSS-2026-06

Reporting Period: 2026-01-01 to 2026-03-31

Owner: Finance Shared Service Center

## Page 1 - Revenue Detail

Scenario: the table is designed to mimic a PDF where the header and subtotal continue across pages.

| Line Item | Q1 Amount | Evidence Note |
| --- | --- | --- |
| Hardware Subscription | 18400 | invoice batch A17 |
| Maintenance Service | 7250 | invoice batch B04 |
| Channel Rebate | -1380 | manual confirmation required |
| Subtotal Revenue | 24270 | first-page subtotal |

## Page 2 - Cost Detail

| Line Item | Q1 Amount | Evidence Note |
| --- | --- | --- |
| Cloud Cost | -6410 | usage statement U23 |
| Delivery Labor | -3890 | timesheet rollup |
| Support Expense | -2160 | ticket group S11 |
| Total Operating Result | 11810 | 24270 - 6410 - 3890 - 2160 |

## Audit Notes

Risk: subtotal and total rows are separated by a page break in the source PDF.

Recommendation: verify that retrieval chunks preserve both page labels and table context.
