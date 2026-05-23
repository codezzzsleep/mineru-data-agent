# MinerU Data Agent Run 42db2610f372

- Task: Parse a complex financial PDF, extract tables, numeric facts, total rows, audit notes, quality logs, and retrieval chunks.
- Profile: financial_report
- Input: `<PROJECT_ROOT>\examples\real_pdfs\complex_financial_report.pdf`
- Quality: pass (100/100)
- Content blocks: 12
- Pages with provenance: 3
- Provenance level: page
- Sections: 4
- Tables: 1
- Key-values: 7
- Numeric facts: 1
- Dates detected: 2
- Recommendation signals: 2
- Anomaly signals: 2
- Retrieval chunks: 2
- Recovery decision: accept
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
- Document ID: FIN-2026-CASE-01
- Reporting Period: 2024-01-01 to 2024-12-31
- Purpose: test dense numeric extraction, total-row validation, and provenance logging.
- Review note: totals must be checked against comparable numeric rows.
- Risk: channel rebate values require manual confirmation against the source ledger.
- Recommendation: re-run OCR if any comma-separated amount is fragmented by layout analysis.
- Owner: Finance Data Office

## Recommendation Evidence
- Recommendation: re-run OCR if any comma-separated amount is fragmented by layout analysis.
- Purpose: test dense numeric extraction, total-row validation, and provenance logging.

## Recovery Decision
- Decision: accept
- No automatic retry required; keep artifacts and trace for audit.

## Issues
- [info] numeric_total_verified: A total/subtotal row matched the sum of comparable numeric rows.

## Markdown Preview

# Complex Financial Report Fixture

Document ID: FIN-2026-CASE-01

Reporting Period: 2024-01-01 to 2024-12-31

Purpose: test dense numeric extraction, total-row validation, and provenance logging.

## 1. Executive Summary

The report contains quarterly financial data, negative adjustments, cross-page notes, and a final total row.
The agent should preserve table structure, numeric facts, dates, and warning signals.

## 2. Operating Result Table

<table><tr><td rowspan=1 colspan=1>Line Item</td><td rowspan=1 colspan=1>2024 Q1</td><td rowspan=1 colspan=1>2024 Q2</td><td rowspan=1 colspan=1>2024 Q3</td><td rowspan=1 colspan=1>2024 Q4</td><td rowspan=1 colspan=1>FY 2024</td></tr><tr><td rowspan=1 colspan=1>Product revenue</td><td rowspan=1 colspan=1>12,340</td><td rowspan=1 colspan=1>13,110</td><td rowspan=1 colspan=1>14,220</td><td rowspan=1 colspan=1>15,680</td><td rowspan=1 colspan=1>55,350</td></tr><tr><td rowspan=1 colspan=1>Service revenue</td><td rowspan=1 colspan=1>5,220</td><td rowspan=1 colspan=1>5,480</td><td rowspan=1 colspan=1>6,040</td><td rowspan=1 colspan=1>6,330</td><td rowspan=1 colspan=1>23,070</td></tr><tr><td rowspan=1 colspan=1>Channel rebate</td><td rowspan=1 colspan=1>-740</td><td rowspan=1 colspan=1>-810</td><td rowspan=1 colspan=1>-860</td><td rowspan=1 colspan=1>-910</td><td rowspan=1 colspan=1>-3,320</td></tr><tr><td rowspan=1 colspan=1>Cloud cost</td><td rowspan=1 colspan=1>-3,180</td><td rowspan=1 colspan=1>-3,440</td><td rowspan=1 colspan=1>-3,720</td><td rowspan=1 colspan=1>-3,990</td><td rowspan=1 colspan=1>-14,330</td></tr><tr><td rowspan=1 colspan=1>Sales expense</td><td rowspan=1 colspan=1>-2,280</td><td rowspan=1 colspan=1>-2,440</td><td rowspan=1 colspan=1>-2,510</td><td rowspan=1 colspan=1>-2,690</td><td rowspan=1 colspan=1>-9,920</td></tr><tr><td rowspan=1 colspan=1>R&amp;D expense</td><td rowspan=1 colspan=1>-3,100</td><td rowspan=1 colspan=1>-3,260</td><td rowspan=1 colspan=1>-3,490</td><td rowspan=1 colspan=1>-3,710</td><td r
