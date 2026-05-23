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