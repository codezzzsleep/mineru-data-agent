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