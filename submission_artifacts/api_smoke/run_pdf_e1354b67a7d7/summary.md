# MinerU Data Agent Run e1354b67a7d7

- Task: API smoke: parse contract PDF and return structured result, trace, summary, and retrieval files
- Profile: standard_or_contract
- Execution method: auto
- Execution backend: pipeline
- LLM preplan applied changes: 0
- Input: `<PROJECT_ROOT>\runs\api_pdf_smoke\_uploads\8828ab01efa846f98d524719bb9d8b69.pdf`
- Quality: pass_with_warnings (92/100)
- Content blocks: 15
- Pages with provenance: 0
- Provenance level: document
- Sections: 6
- Tables: 1
- Key-values: 6
- Numeric facts: 1
- Dates detected: 1
- Recommendation signals: 1
- Anomaly signals: 2
- Retrieval chunks: 6
- Recovery decision: accept_with_review_notes
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

## Extracted Fields
- Contract No: STD-2026-MINERU-07
- Effective Date: 2026-05-20
- Parties: Corpus Producer A and Processing Vendor B
- Risk: missing page provenance must be reported as a quality issue instead of being hidden.
- Recommendation: the reviewer should inspect trace.json and retrieval_quality.json.
- Signed by: Data Governance Office / Vendor Engineering Lead

## Recommendation Evidence
- Recommendation: the reviewer should inspect trace.json and retrieval_quality.json.

## Recovery Decision
- Decision: accept_with_review_notes
- Use local MinerU CLI when page-level provenance is required.

Attempts:
- initial: pass_with_warnings (92/100), selected

## Issues
- [warning] no_page_provenance: Content blocks were extracted, but no page-level provenance is available.

## Markdown Preview

# Data Processing Service Agreement

Contract No: STD-2026-MINERU-07

Effective Date: 2026-05-20

Parties: Corpus Producer A and Processing Vendor B

## 1. Scope

The vendor provides a traceable document parsing agent for PDF, scanned files, web pages, and structured exports.

## 2. Compliance Clauses

<table><tr><td rowspan=1 colspan=1>Clause</td><td rowspan=1 colspan=1> Requirement</td><td rowspan=1 colspan=1>Evidence Field</td></tr><tr><td rowspan=1 colspan=1>2.1</td><td rowspan=1 colspan=1>Supplier must keep trace logs for every parsing run.</td><td rowspan=1 colspan=1>trace_path</td></tr><tr><td rowspan=1 colspan=1>2.2</td><td rowspan=1 colspan=1>Output JSON must include structured sections and tables.</td><td rowspan=1 colspan=1>result.json</td></tr><tr><td rowspan=1 colspan=1>3.1</td><td rowspan=1 colspan=1>Failures must be recoverable without stopping the batch.</td><td rowspan=1 colspan=1>batch_report.json</td></tr><tr><td rowspan=1 colspan=1>4.1</td><td rowspan=1 colspan=1>Keys and tokens must not be writen to public artifacts.</td><td rowspan=1 colspan=1>secret_scan</td></tr></table>

## 3. Service Level

Batch tasks must continue after a single item failure and must record the error message.

## 4. Exception Handling

Risk: missing page provenance must be reported as a quality issue instead of being hidden.

Recommendation: the reviewer should inspect trace.json and retrieval_quality.json.

## 5. Signature

Signed by: Data Governance Office / Vendor Engineering Lead
