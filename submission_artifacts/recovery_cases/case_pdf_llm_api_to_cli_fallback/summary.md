# MinerU Data Agent Run 52c948b82c48

- Task: Parse the contract PDF, let the LLM preplanner define schema and recovery policy, use online API first, and automatically fallback to local CLI when page provenance is missing.
- Profile: standard_or_contract
- Execution method: auto
- Execution backend: pipeline
- LLM preplan applied changes: 1
- Input: `<PROJECT_ROOT>\examples\real_pdfs\standard_contract_cross_page.pdf`
- Quality: pass (100/100)
- Content blocks: 15
- Pages with provenance: 2
- Provenance level: page
- Sections: 6
- Tables: 1
- Key-values: 6
- Numeric facts: 1
- Dates detected: 1
- Recommendation signals: 1
- Anomaly signals: 2
- Retrieval chunks: 2
- Recovery decision: recovered_accept
- Recovery selected attempt: cli_fallback
- Recovery attempts: 2
- LLM analysis: enabled/completed

## Plan
1. Inspect input type and task objective
2. Parse document with MinerU or native HTML extractor
3. Normalize content blocks with page-level or document-level provenance
4. Build markdown, section, key-value, table, and numeric views
5. Run quality checks and produce traceable logs
6. Prioritize section hierarchy and clause-like paragraph extraction
7. Preserve source page or document heading evidence for each clause
8. LLM preplan: Use online Agent API as the first low-cost parser.
9. LLM preplan: Validate page-level provenance before accepting the result.
10. LLM preplan: Fallback to local MinerU CLI if page provenance is missing.
11. LLM preplan: Build structured JSON, retrieval chunks, and trace evidence.

## LLM Agent Analysis

Pre-execution control: profile=standard_or_contract, runner=cli, method=auto, backend=pipeline
Applied LLM control changes:
- lang: ch -> en

Fallback selected the page-level CLI artifact after online API provenance warning.

Suggested execution plan:
1. Review selected attempt and retrieval chunks.

## Extracted Fields
- Contract No: STD-2026-MINERU-07
- Effective Date: 2026-05-20
- Parties: Corpus Producer A and Processing Vendor B
- Risk: missing page provenance must be reported as a quality issue instead of being hidden.
- Recommendation: the reviewer should inspect trace.json and retrieval\_quality.json.
- Signed by: Data Governance Office / Vendor Engineering Lead

## Recommendation Evidence
- Recommendation: the reviewer should inspect trace.json and retrieval\_quality.json.

## Recovery Decision
- Decision: recovered_accept
- Executed 1 automatic recovery attempt(s); selected `cli_fallback`.
- Initial quality issues were preserved for audit: no_page_provenance.

Attempts:
- initial: pass_with_warnings (92/100), not selected
- cli_fallback: pass (100/100), selected

## Issues
- No blocking issues detected.

## Markdown Preview

# Data Processing Service Agreement

Contract No: STD-2026-MINERU-07

Effective Date: 2026-05-20

Parties: Corpus Producer A and Processing Vendor B

## 1. Scope

The vendor provides a traceable document parsing agent for PDF, scanned files, web pages, and structured exports.

## 2. Compliance Clauses

<table><tr><td rowspan=1 colspan=1>Clause</td><td rowspan=1 colspan=1>Requirement</td><td rowspan=1 colspan=1>Evidence Field</td></tr><tr><td rowspan=1 colspan=1>2.1</td><td rowspan=1 colspan=1>Supplier must keep trace logs for every parsing run.</td><td rowspan=1 colspan=1>trace_path</td></tr><tr><td rowspan=1 colspan=1>2.2</td><td rowspan=1 colspan=1>Output JSON must include structured sections and tables.</td><td rowspan=1 colspan=1>result.json</td></tr><tr><td rowspan=1 colspan=1>3.1</td><td rowspan=1 colspan=1>Failures must be recoverable without stopping the batch.</td><td rowspan=1 colspan=1>batch_report.json</td></tr><tr><td rowspan=1 colspan=1>4.1</td><td rowspan=1 colspan=1>Keys and tokens must not be written to public artifacts.</td><td rowspan=1 colspan=1>secret_scan</td></tr></table>

## 3. Service Level

Batch tasks must continue after a single item failure and must record the error message.

## 4. Exception Handling

Risk: missing page provenance must be reported as a quality issue instead of being hidden.

Recommendation: the reviewer should inspect trace.json and retrieval\_quality.json.

## 5. Signature

Signed by: Data Governance Office / Vendor Engineering Lead
