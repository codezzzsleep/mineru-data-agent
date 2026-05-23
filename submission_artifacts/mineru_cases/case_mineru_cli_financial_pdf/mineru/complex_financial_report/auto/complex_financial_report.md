# Complex Financial Report Fixture

Document ID: FIN-2026-CASE-01

Reporting Period: 2024-01-01 to 2024-12-31

Purpose: test dense numeric extraction, total-row validation, and provenance logging.

## 1. Executive Summary

The report contains quarterly financial data, negative adjustments, cross-page notes, and a final total row.
The agent should preserve table structure, numeric facts, dates, and warning signals.

## 2. Operating Result Table

<table><tr><td rowspan=1 colspan=1>Line Item</td><td rowspan=1 colspan=1>2024 Q1</td><td rowspan=1 colspan=1>2024 Q2</td><td rowspan=1 colspan=1>2024 Q3</td><td rowspan=1 colspan=1>2024 Q4</td><td rowspan=1 colspan=1>FY 2024</td></tr><tr><td rowspan=1 colspan=1>Product revenue</td><td rowspan=1 colspan=1>12,340</td><td rowspan=1 colspan=1>13,110</td><td rowspan=1 colspan=1>14,220</td><td rowspan=1 colspan=1>15,680</td><td rowspan=1 colspan=1>55,350</td></tr><tr><td rowspan=1 colspan=1>Service revenue</td><td rowspan=1 colspan=1>5,220</td><td rowspan=1 colspan=1>5,480</td><td rowspan=1 colspan=1>6,040</td><td rowspan=1 colspan=1>6,330</td><td rowspan=1 colspan=1>23,070</td></tr><tr><td rowspan=1 colspan=1>Channel rebate</td><td rowspan=1 colspan=1>-740</td><td rowspan=1 colspan=1>-810</td><td rowspan=1 colspan=1>-860</td><td rowspan=1 colspan=1>-910</td><td rowspan=1 colspan=1>-3,320</td></tr><tr><td rowspan=1 colspan=1>Cloud cost</td><td rowspan=1 colspan=1>-3,180</td><td rowspan=1 colspan=1>-3,440</td><td rowspan=1 colspan=1>-3,720</td><td rowspan=1 colspan=1>-3,990</td><td rowspan=1 colspan=1>-14,330</td></tr><tr><td rowspan=1 colspan=1>Sales expense</td><td rowspan=1 colspan=1>-2,280</td><td rowspan=1 colspan=1>-2,440</td><td rowspan=1 colspan=1>-2,510</td><td rowspan=1 colspan=1>-2,690</td><td rowspan=1 colspan=1>-9,920</td></tr><tr><td rowspan=1 colspan=1>R&amp;D expense</td><td rowspan=1 colspan=1>-3,100</td><td rowspan=1 colspan=1>-3,260</td><td rowspan=1 colspan=1>-3,490</td><td rowspan=1 colspan=1>-3,710</td><td rowspan=1 colspan=1>-13,560</td></tr><tr><td rowspan=1 colspan=1>General expense</td><td rowspan=1 colspan=1>-1,420</td><td rowspan=1 colspan=1>-1,500</td><td rowspan=1 colspan=1>-1,605</td><td rowspan=1 colspan=1>-1,710</td><td rowspan=1 colspan=1>-6,235</td></tr><tr><td rowspan=1 colspan=1>Tax adjustment</td><td rowspan=1 colspan=1>-260</td><td rowspan=1 colspan=1>-280</td><td rowspan=1 colspan=1>-310</td><td rowspan=1 colspan=1>-330</td><td rowspan=1 colspan=1>-1,180</td></tr><tr><td rowspan=1 colspan=1>Total operating result</td><td rowspan=1 colspan=1>6,580</td><td rowspan=1 colspan=1>6,860</td><td rowspan=1 colspan=1>7,765</td><td rowspan=1 colspan=1>8,670</td><td rowspan=1 colspan=1>29,875</td></tr></table>

Review note: totals must be checked against comparable numeric rows.

## 3. Audit Notes

Risk: channel rebate values require manual confirmation against the source ledger.

Recommendation: re-run OCR if any comma-separated amount is fragmented by layout analysis.

Owner: Finance Data Office
