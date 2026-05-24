# Artifact Index

This file is a single navigation page for saved submission artifacts.

## Quick Metrics

- `evaluation`: `{"cases": 17, "expected_fields": 45, "field_precision": 1.0, "field_recall": 1.0, "field_f1": 1.0}`
- `stability`: `{"cases": 17, "tool_calls": 11, "tool_elapsed_seconds": 240.107, "recovery_executed_cases": 4}`
- `http_load_test_100`: `{"requests": 100, "success": 100, "failed": 0, "p95_seconds": 4.205352}`
- `llm_cost`: `{"llm_enabled_results": 2, "llm_trace_tool_calls": 4, "total_tokens": 4309, "estimated_cost_usd": null}`
- `llm_impact`: `{"compared_pairs": 1, "llm_enabled_pairs": 1, "pairs_with_applied_controls": 0, "pairs_with_recovery_suggestions": 1}`

## Directories

| Area | Path | Result JSON | Trace JSON | Main reports |
| --- | --- | ---: | ---: | --- |
| HTML/Web fixtures | `submission_artifacts/cases` | 5 | 5 | `submission_artifacts/cases/case_1_financial_report/summary.md`, `submission_artifacts/cases/case_2_low_quality_ocr/summary.md`, `submission_artifacts/cases/case_3_standard_contract/summary.md` |
| MinerU CLI PDFs | `submission_artifacts/mineru_cases` | 4 | 4 | `submission_artifacts/mineru_cases/case_mineru_cli_contract_pdf/mineru/standard_contract_cross_page/auto/standard_contract_cross_page.md`, `submission_artifacts/mineru_cases/case_mineru_cli_contract_pdf/summary.md`, `submission_artifacts/mineru_cases/case_mineru_cli_financial_pdf/human_spot_check.md` |
| MinerU Agent API PDF | `submission_artifacts/agent_api_cases` | 1 | 1 | `submission_artifacts/agent_api_cases/case_agent_api_contract_pdf/mineru/standard_contract_cross_page/agent_api/standard_contract_cross_page.md`, `submission_artifacts/agent_api_cases/case_agent_api_contract_pdf/summary.md` |
| Recovery | `submission_artifacts/recovery_cases` | 1 | 1 | `submission_artifacts/recovery_cases/case_pdf_llm_api_to_cli_fallback/mineru/standard_contract_cross_page/agent_api/standard_contract_cross_page.md`, `submission_artifacts/recovery_cases/case_pdf_llm_api_to_cli_fallback/mineru_fallback_cli/standard_contract_cross_page/auto/standard_contract_cross_page.md`, `submission_artifacts/recovery_cases/case_pdf_llm_api_to_cli_fallback/summary.md` |
| Office files | `submission_artifacts/office_cases` | 2 | 2 | `submission_artifacts/office_cases/case_docx_standard_review/office/industry_standard_review.md`, `submission_artifacts/office_cases/case_docx_standard_review/summary.md`, `submission_artifacts/office_cases/case_pptx_workflow_review/office/workflow_agent_review.md` |
| Challenge fixtures | `submission_artifacts/challenge_cases` | 4 | 4 | `submission_artifacts/challenge_cases/case_6_cross_page_financial_table/html/case_6_cross_page_financial_table.md`, `submission_artifacts/challenge_cases/case_6_cross_page_financial_table/summary.md`, `submission_artifacts/challenge_cases/case_7_noisy_contract_scan/html/case_7_noisy_contract_scan.md` |
| Adaptive planning | `submission_artifacts/adaptive_cases` | 2 | 2 | `submission_artifacts/adaptive_cases/case_financial_anomaly_evidence_query/html/case_1_financial_report.md`, `submission_artifacts/adaptive_cases/case_financial_anomaly_evidence_query/summary.md`, `submission_artifacts/adaptive_cases/case_financial_growth_query/html/case_1_financial_report.md` |
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
| LLM cost | `submission_artifacts/llm_cost` | 0 | 0 | `submission_artifacts/llm_cost/llm_cost_report.md` |
| LLM impact | `submission_artifacts/llm_impact` | 0 | 0 | `submission_artifacts/llm_impact/llm_impact_report.md` |

## Notes

- `result.json` is the machine-readable output.
- `trace.json` is the execution log with steps, tools, elapsed time, and errors.
- Report files summarize saved artifacts; they do not replace rerunning the scripts in a target environment.
