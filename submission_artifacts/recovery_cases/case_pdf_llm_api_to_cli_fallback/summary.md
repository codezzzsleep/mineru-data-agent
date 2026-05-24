# MinerU Data Agent Run 9cfdd736c9a1

- Schema version: 2026-05-24
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
- Key-values: 8
- Field evidence records: 8
- Numeric facts: 1
- Dates detected: 1
- Recommendation signals: 1
- Anomaly signals: 2
- Retrieval chunks: 2
- Recovery decision: recovered_accept
- Recovery selected attempt: cli_fallback
- Recovery attempts: 2
- Task intents: evidence_trace
- LLM analysis: enabled/completed

## Plan
1. Inspect input type, document metadata, and natural-language task objective
2. Infer task intents and generate a target extraction schema
3. Choose MinerU/native parsing path and record execution rationale
4. Normalize content blocks with page-level or document-level provenance
5. Build markdown, section, key-value, table, numeric, and field-evidence views
6. Run task-specific post-processing and quality checks
7. Select recovery action from issue codes, retry history, and task priorities
8. Produce traceable result, summary, retrieval chunks, and audit logs
9. Prioritize section hierarchy, clause-like paragraphs, parties, obligations, and dates
10. Preserve source page or document heading evidence for each clause
11. Apply task intent `evidence_trace` with schema-aware extraction and verification
12. LLM preplan: Use online Agent API as the first low-cost parser.
13. LLM preplan: Validate page-level provenance before accepting the result.
14. LLM preplan: Fallback to local MinerU CLI if page provenance is missing.
15. LLM preplan: Build structured JSON, retrieval chunks, and trace evidence.

## Planning Rationale
- standard/contract keywords or explicit profile require section and clause preservation
- online MinerU Agent API is selected for CPU-friendly PDF parsing and quick reproducibility
- backend=pipeline is used for MinerU parsing when the selected runner calls MinerU
- method=auto balances automatic parsing with OCR fallback when quality gates require it
- lang=en is passed to MinerU or recorded for native extraction audit
- Recovery policy:
  - text_cleanup if mojibake or encoding noise is detected
  - ocr_retry for PDF/image results with blocking extraction or OCR-related quality issues
  - cli_fallback when online API lacks page-level provenance and a local MinerU CLI is available
  - manual_numeric_review when subtotal/total consistency checks fail

## Adaptive Task Decision
- Intents: evidence_trace
- Target schema keys: document_title, parties, clause_id, obligation, effective_date, evidence, Contract No, Effective Date, Clause, Evidence Field
- Quality thresholds: {"min_quality_score": 88, "require_tables": false, "require_numeric_facts": false, "prefer_page_provenance": true}
- Recovery strategy:
  - cli_fallback on online_api_missing_page_provenance (high)
  - ocr_retry on empty_or_sparse_text_or_ocr_quality_issue (normal)
  - text_cleanup on mojibake_or_encoding_noise (normal)
  - llm_suggested_review on If no_page_provenance appears after online API parsing, fallback to local CLI artifacts. (advisory)

## Agent Action Plan
- Subtasks: 7
- Selected tools: mineru_agent_api, llm_preplanner, structured_extractor, contract_validator, text_cleanup, ocr_retry, cli_fallback, llm_post_review, retrieval_exporter
- understand_task: Classify the document task and identify intent-specific outputs.
- choose_parse_path: Pick the cheapest parser path that still preserves required provenance.
- extract_structure: Normalize sections, tables, key-values, numeric facts, and field evidence.
- validate_quality: Run profile and task-specific gates before accepting the result.
- llm_review: Review parse output against task-specific risks and propose follow-up actions.
- replan_if_needed: Map quality issues to recovery actions and select the best attempt.

## Runtime Recovery Plan
- Initial issue codes: no_page_provenance
- cli_fallback: executed for no_page_provenance (agent_action_plan.replan_triggers)
- llm_suggested_review: skipped for llm_suggested (llm_post_review.recovery_suggestions)

## Agent Replan After Quality
- Issue codes: none
- Attempted actions: initial, cli_fallback
- Selected reason: cli_fallback had quality_status=pass and score=100

## Task-Specific Answers

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
- 1. Scope: The vendor provides a traceable document parsing agent for PDF, scanned files, web pages, and structured exports.
- 3. Service Level: Batch tasks must continue after a single item failure and must record the error message.

## Field Evidence
- Contract No: confidence=0.95, location=1, evidence=Contract No: STD-2026-MINERU-07
- Effective Date: confidence=0.95, location=1, evidence=Effective Date: 2026-05-20
- Parties: confidence=0.95, location=1, evidence=Parties: Corpus Producer A and Processing Vendor B
- Risk: confidence=0.95, location=2, evidence=Risk: missing page provenance must be reported as a quality issue instead of being hidden.
- Recommendation: confidence=0.95, location=2, evidence=Recommendation: the reviewer should inspect trace.json and retrieval\_quality.json.

## Recommendation Evidence
- Recommendation: the reviewer should inspect trace.json and retrieval\_quality.json.

## Recovery Decision
- Decision: recovered_accept
- Executed 1 automatic recovery attempt(s); selected `cli_fallback`.
- Initial quality issues were preserved for audit: no_page_provenance.
- LLM suggested: Re-run with live ModelScope or DeepSeek key before final live-demo submission.

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
