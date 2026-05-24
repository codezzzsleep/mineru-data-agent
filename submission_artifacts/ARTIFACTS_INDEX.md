# Artifact Index

This file is a single navigation page for saved submission artifacts.

## Quick Metrics

- `evaluation`: `{"cases": 17, "expected_fields": 45, "field_precision": 1.0, "field_recall": 1.0, "field_f1": 1.0}`
- `stability`: `{"cases": 17, "tool_calls": 11, "tool_elapsed_seconds": 240.107, "recovery_executed_cases": 4}`
- `http_load_test_100`: `{"requests": 100, "success": 100, "failed": 0, "p95_seconds": 4.205352}`
- `llm_cost`: `{"llm_enabled_results": 2, "llm_trace_tool_calls": 4, "total_tokens": 4309, "estimated_cost_usd": null}`
- `agent_decision_cases`: `{"cases": 5, "selected_tool_names": ["contract_validator", "llm_post_review", "llm_preplanner", "native_extractor", "numeric_validator", "retrieval_exporter", "structured_extractor", "text_cleanup", "workflow_validator"], "boundary": "offline scripted decision regression; token counts are synthetic; live provider case remains in llm_cases"}`
- `llm_impact`: `{"compared_pairs": 1, "llm_enabled_pairs": 1, "pairs_with_applied_controls": 0, "pairs_with_recovery_suggestions": 1}`
- `cost_model`: `{"scenarios": 4, "pricing_inputs": {"gpu_cny_per_hour": null, "agent_api_cny_per_page": null, "assumed_pages_per_pdf": 20, "llm_cny_per_million_tokens": null, "env_vars": ["MINERU_DATA_AGENT_GPU_CNY_PER_HOUR", "MINERU_DATA_AGENT_AGENT_API_CNY_PER_PAGE", "MINERU_DATA_AGENT_ASSUMED_PAGES_PER_PDF", "MINERU_DATA_AGENT_LLM_CNY_PER_MILLION_TOKENS"]}}`
- `recovery_effectiveness`: `{"results_with_recovery": 39, "recovery_executed": 8, "selected_non_initial": 6, "executed_rate": 0.20512820512820512, "selected_non_initial_rate": 0.15384615384615385, "average_non_initial_tool_seconds_when_executed": 2.936, "attempt_counts": {"cli_fallback": 1, "initial": 39, "ocr_retry": 3, "text_cleanup": 4}, "selected_attempt_counts": {"cli_fallback": 1, "initial": 33, "ocr_retry": 1, "text_cleanup": 4}, "initial_issue_counts": {"document_level_provenance": 21, "expected_anomaly_signal_missing": 2, "no_page_provenance": 11, "numeric_total_mismatch": 6, "numeric_total_needs_review": 1, "numeric_total_verified": 9, "possible_mojibake": 4, "short_text": 2, "weak_clause_structure": 1}, "failed_attempt_counts": {"ocr_retry": 1}}`
- `long_document_risk`: `{"page_count": 48, "chunk_size": 20, "total_chunks": 3, "completed_chunks": 3, "failed_chunks": 0, "success_rate": 1.0, "elapsed_seconds": 42.418, "total_retrieval_chunks": 58, "quality_status_counts": {"pass_with_warnings": 3}, "issue_counts": {"no_page_provenance": 3}, "provenance_level_counts": {"document": 3}}`
- `retrieval_validation`: `{"chunk_files": 39, "total_chunks": 255, "schema_error_count": 0, "duplicate_text_rate": 0.00392156862745098, "label_query_checks": {"queries": 76, "hits_top3": 70, "hit_rate_top3": 0.9210526315789473}}`
- `agent_value`: `{"cases": 37, "decision_modes": {"controlled_fault_injection": 5, "deterministic_rules": 25, "llm_enabled_saved_result_without_live_trace": 1, "offline_scripted_decision_regression": 5, "saved_live_llm_trace": 1}, "parser_runners": {"-": 12, "agent-api": 8, "cli": 3, "native": 14}, "with_state_machine": 17, "with_runtime_recovery_plan": 17, "with_task_result": 17, "with_field_evidence": 19, "with_cross_page_references": 2, "with_quality_issues": 31, "with_recovery_attempts": 8, "selected_non_initial": 6, "with_retrieval_chunks": 37, "with_live_llm_trace": 1}`
- `code_quality`: `{"python_files": 57, "physical_lines": 15411, "code_lines": 13671, "classes": 38, "functions": 635, "test_functions": 88, "test_files": 13, "workflow_files": [".github/workflows/tests.yml"], "coverage_measured": true, "line_coverage_percent": 82.24, "coverage_report": "submission_artifacts/coverage/coverage_report.md"}`
- `coverage`: `{"measured": true, "line_coverage_percent": 82.24, "num_statements": 3548, "missing_lines": 630}`

## Directories

| Area | Path | Result JSON | Trace JSON | Main reports |
| --- | --- | ---: | ---: | --- |
| HTML/Web fixtures | `submission_artifacts/cases` | 5 | 5 | `submission_artifacts/cases/case_1_financial_report/summary.md`, `submission_artifacts/cases/case_2_low_quality_ocr/summary.md`, `submission_artifacts/cases/case_3_standard_contract/summary.md` |
| MinerU CLI PDFs | `submission_artifacts/mineru_cases` | 4 | 4 | `submission_artifacts/mineru_cases/case_mineru_cli_contract_pdf/mineru/standard_contract_cross_page/auto/standard_contract_cross_page.md`, `submission_artifacts/mineru_cases/case_mineru_cli_contract_pdf/summary.md`, `submission_artifacts/mineru_cases/case_mineru_cli_financial_pdf/human_spot_check.md` |
| MinerU Agent API PDF | `submission_artifacts/agent_api_cases` | 1 | 1 | `submission_artifacts/agent_api_cases/case_agent_api_contract_pdf/mineru/standard_contract_cross_page/agent_api/standard_contract_cross_page.md`, `submission_artifacts/agent_api_cases/case_agent_api_contract_pdf/summary.md` |
| Recovery | `submission_artifacts/recovery_cases` | 1 | 1 | `submission_artifacts/recovery_cases/case_pdf_llm_api_to_cli_fallback/mineru/standard_contract_cross_page/agent_api/standard_contract_cross_page.md`, `submission_artifacts/recovery_cases/case_pdf_llm_api_to_cli_fallback/mineru_fallback_cli/standard_contract_cross_page/auto/standard_contract_cross_page.md`, `submission_artifacts/recovery_cases/case_pdf_llm_api_to_cli_fallback/summary.md` |
| Failure/recovery fault injection | `submission_artifacts/failure_recovery_cases` | 5 | 5 | `submission_artifacts/failure_recovery_cases/numeric_total_mismatch_html/html/numeric_total_mismatch_html.md`, `submission_artifacts/failure_recovery_cases/numeric_total_mismatch_html/summary.md`, `submission_artifacts/failure_recovery_cases/ocr_retry_failure_controlled/mineru/ocr_retry_failure_controlled/auto/ocr_retry_failure_controlled.md` |
| Office files | `submission_artifacts/office_cases` | 2 | 2 | `submission_artifacts/office_cases/case_docx_standard_review/office/industry_standard_review.md`, `submission_artifacts/office_cases/case_docx_standard_review/summary.md`, `submission_artifacts/office_cases/case_pptx_workflow_review/office/workflow_agent_review.md` |
| Challenge fixtures | `submission_artifacts/challenge_cases` | 4 | 4 | `submission_artifacts/challenge_cases/case_6_cross_page_financial_table/html/case_6_cross_page_financial_table.md`, `submission_artifacts/challenge_cases/case_6_cross_page_financial_table/summary.md`, `submission_artifacts/challenge_cases/case_7_noisy_contract_scan/html/case_7_noisy_contract_scan.md` |
| Adaptive planning | `submission_artifacts/adaptive_cases` | 2 | 2 | `submission_artifacts/adaptive_cases/case_financial_anomaly_evidence_query/html/case_1_financial_report.md`, `submission_artifacts/adaptive_cases/case_financial_anomaly_evidence_query/summary.md`, `submission_artifacts/adaptive_cases/case_financial_growth_query/html/case_1_financial_report.md` |
| Agent decision regression | `submission_artifacts/agent_decision_cases` | 5 | 5 | `submission_artifacts/agent_decision_cases/cross_page_table_agent_plan/html/case_6_cross_page_financial_table.md`, `submission_artifacts/agent_decision_cases/cross_page_table_agent_plan/summary.md`, `submission_artifacts/agent_decision_cases/financial_growth_agent_plan/html/case_1_financial_report.md` |
| Cross-run memory | `submission_artifacts/memory_cases` | 3 | 3 | `submission_artifacts/memory_cases/cross_run_text_cleanup_memory/first_run/html/input.md`, `submission_artifacts/memory_cases/cross_run_text_cleanup_memory/first_run/recovery/text_cleanup/input.md`, `submission_artifacts/memory_cases/cross_run_text_cleanup_memory/first_run/summary.md` |
| Public real PDFs | `submission_artifacts/public_real_cases` | 4 | 4 | `submission_artifacts/public_real_cases/human_annotation_table.md`, `submission_artifacts/public_real_cases/public_cdc_vis_instructions/mineru/cdc_vis_instructions/agent_api/cdc_vis_instructions.md`, `submission_artifacts/public_real_cases/public_cdc_vis_instructions/mineru_retry_ocr/cdc_vis_instructions/agent_api/cdc_vis_instructions.md` |
| Long document chunks | `submission_artifacts/long_document_chunks` | 3 | 3 | `submission_artifacts/long_document_chunks/public_nist_ai_rmf_full_chunked/chunks/p001_020/mineru/nist_ai_rmf_1_0/agent_api/nist_ai_rmf_1_0.md`, `submission_artifacts/long_document_chunks/public_nist_ai_rmf_full_chunked/chunks/p001_020/summary.md`, `submission_artifacts/long_document_chunks/public_nist_ai_rmf_full_chunked/chunks/p021_040/mineru/nist_ai_rmf_1_0/agent_api/nist_ai_rmf_1_0.md` |
| LLM cases | `submission_artifacts/llm_cases` | 1 | 1 | `submission_artifacts/llm_cases/case_llm_financial_review/html/case_1_financial_report.md`, `submission_artifacts/llm_cases/case_llm_financial_review/summary.md` |
| Evaluation metrics | `submission_artifacts/evaluation` | 0 | 0 | `submission_artifacts/evaluation/evaluation_metrics.md` |
| Stability report | `submission_artifacts/stability` | 0 | 0 | `submission_artifacts/stability/stability_report.md` |
| API smoke | `submission_artifacts/api_smoke` | 2 | 2 | `submission_artifacts/api_smoke/run_2478fc60f3b2/html/0436b28901264e3c8a5b26273ac3e49f.md`, `submission_artifacts/api_smoke/run_2478fc60f3b2/summary.md`, `submission_artifacts/api_smoke/run_pdf_e1354b67a7d7/mineru/8828ab01efa846f98d524719bb9d8b69/agent_api/8828ab01efa846f98d524719bb9d8b69.md` |
| API load smoke | `submission_artifacts/api_load_smoke` | 8 | 8 | `submission_artifacts/api_load_smoke/api_load_smoke_report.md` |
| HTTP load test | `submission_artifacts/http_load_test` | 12 | 12 | `submission_artifacts/http_load_test/http_load_test_report.md` |
| HTTP load test 100 | `submission_artifacts/http_load_test_100` | 0 | 0 | `submission_artifacts/http_load_test_100/http_load_test_report.md` |
| Tradeoff comparison | `submission_artifacts/baseline_comparison` | 0 | 0 | `submission_artifacts/baseline_comparison/baseline_comparison.md` |
| Agent value report | `submission_artifacts/agent_value` | 0 | 0 | `submission_artifacts/agent_value/agent_value_report.md` |
| Cost model | `submission_artifacts/cost_model` | 0 | 0 | `submission_artifacts/cost_model/cost_model.md` |
| LLM cost | `submission_artifacts/llm_cost` | 0 | 0 | `submission_artifacts/llm_cost/llm_cost_report.md` |
| LLM impact | `submission_artifacts/llm_impact` | 0 | 0 | `submission_artifacts/llm_impact/llm_impact_report.md` |
| Recovery effectiveness | `submission_artifacts/recovery_effectiveness` | 0 | 0 | `submission_artifacts/recovery_effectiveness/recovery_effectiveness_report.md` |
| Long-document risk | `submission_artifacts/long_document_risk` | 0 | 0 | `submission_artifacts/long_document_risk/long_document_risk_report.md` |
| Retrieval validation | `submission_artifacts/retrieval_validation` | 0 | 0 | `submission_artifacts/retrieval_validation/retrieval_validation_report.md` |
| Code quality | `submission_artifacts/code_quality` | 0 | 0 | `submission_artifacts/code_quality/code_quality_report.md` |
| Coverage | `submission_artifacts/coverage` | 0 | 0 | `submission_artifacts/coverage/coverage_report.md` |

## Notes

- `result.json` is the machine-readable output.
- `trace.json` is the execution log with steps, tools, elapsed time, and errors.
- Report files summarize saved artifacts; they do not replace rerunning the scripts in a target environment.
