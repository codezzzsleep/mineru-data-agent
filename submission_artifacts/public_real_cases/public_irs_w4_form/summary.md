# MinerU Data Agent Run ad440d103164

- Task: Parse a public IRS W-4 PDF form, extract form title, department, structured sections, form tables, quality issues, trace, and retrieval chunks.
- Profile: standard_or_contract
- Execution method: auto
- Execution backend: pipeline
- LLM preplan applied changes: 0
- Input: `<PROJECT_ROOT>\examples\public_real_documents\files\irs_w4.pdf`
- Quality: pass_with_warnings (76/100)
- Content blocks: 51
- Pages with provenance: 0
- Provenance level: document
- Sections: 6
- Tables: 9
- Key-values: 0
- Numeric facts: 23
- Dates detected: 0
- Recommendation signals: 0
- Anomaly signals: 1
- Retrieval chunks: 22
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
6. Prioritize section hierarchy and clause-like paragraph extraction
7. Preserve source page or document heading evidence for each clause

## Recovery Decision
- Decision: manual_numeric_review
- Use local MinerU CLI when page-level provenance is required.
- Route total/subtotal mismatches to numeric review before downstream use.

Attempts:
- initial: pass_with_warnings (76/100), selected

## Issues
- [warning] no_page_provenance: Content blocks were extracted, but no page-level provenance is available.
- [warning] numeric_total_needs_review: A total/subtotal row was found, but there were not enough comparable numeric rows.
- [warning] numeric_total_mismatch: A total/subtotal row does not match the sum of comparable numeric rows.

## Markdown Preview

# Employee’s Withholding Certificate

Department of the Treasury Internal Revenue Service

2026

<table><tr><td rowspan="6">Step 1: Enter Personal Information</td><td colspan="2">First name and middle initial</td><td>Last name</td><td>Social security number</td></tr><tr><td colspan="3">Address</td><td>Does your name match the name on your social security card? If not, to ensure you get</td></tr><tr><td colspan="3">City or town, state, and ZIP code</td><td>credit for your earnings, contact SSA at 800-772-1213 or go to www.ssa.gov.</td></tr><tr><td colspan="3">(c) Single or Married filing separately</td><td></td></tr><tr><td></td><td colspan="3">Married filing jointly or Qualifying surviving spouse</td></tr><tr><td colspan="3"></td></tr><tr><td colspan="2">number valid for employment. See page 2 for more information.</td><td colspan="2">Cation</td></tr></table>

TIP: Consider using the estimator at www.irs.gov/W4App to determine the most accurate withholding for the rest of the year if you: are completing this form after the beginning of the year; expect to work only part of the year; or have changes during the year in your marital status, number of jobs for you (and/or your spouse if married filing jointly), dependents, other income (not from jobs), deductions, or credits. Have your most recent pay stub(s) from this year available when using the estimator. At the beginning of next year, use the estimator again to recheck your withholding.

Complete Steps 2–4 ONLY if they apply to you; otherwise, skip to Step 5. See page 2 for more information on each step, who can claim exemption from withholding, and when to use the estimator at www.irs.gov/W4App.

<table><tr><td rowspan="5">Step 2: Multiple Jobs or Spouse Works</td><td>  also works. The correct amount of withholding depends on income earned from all of these jobs.</td></tr><tr><td>Do only one of the following.</td></tr><tr><td>Use he tato .o/W4A r heos cioirhise n e. you or your spouse have self-employment income,
