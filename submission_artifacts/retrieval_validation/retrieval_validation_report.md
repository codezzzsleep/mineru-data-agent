# Retrieval Validation Report

Retrieval chunk format and lightweight lexical query validation over saved artifacts.

## Aggregate

- Chunk files: 39
- Total chunks: 255
- Schema errors: 0
- Empty text chunks: 0
- Duplicate text chunks: 1 (0.39%)
- Label lexical top-3 hit rate: 92.11% (70/76)

## Chunk Files

| Chunks | Errors | Duplicates | Empty | Avg Chars | Types | Path |
| ---: | ---: | ---: | ---: | ---: | --- | --- |
| 3 | 0 | 0 | 0 | 144.0 | `{"table": 1, "text": 2}` | `submission_artifacts/adaptive_cases/case_financial_anomaly_evidence_query/retrieval/retrieval_chunks.jsonl` |
| 3 | 0 | 0 | 0 | 144.0 | `{"table": 1, "text": 2}` | `submission_artifacts/adaptive_cases/case_financial_growth_query/retrieval/retrieval_chunks.jsonl` |
| 6 | 0 | 0 | 0 | 224.8 | `{"text": 6}` | `submission_artifacts/agent_api_cases/case_agent_api_contract_pdf/retrieval/retrieval_chunks.jsonl` |
| 5 | 0 | 0 | 0 | 183.0 | `{"table": 2, "text": 3}` | `submission_artifacts/agent_decision_cases/cross_page_table_agent_plan/retrieval/retrieval_chunks.jsonl` |
| 3 | 0 | 0 | 0 | 144.0 | `{"table": 1, "text": 2}` | `submission_artifacts/agent_decision_cases/financial_growth_agent_plan/retrieval/retrieval_chunks.jsonl` |
| 4 | 0 | 0 | 0 | 177.0 | `{"table": 1, "text": 3}` | `submission_artifacts/agent_decision_cases/noisy_contract_recovery_plan/retrieval/retrieval_chunks.jsonl` |
| 5 | 0 | 0 | 0 | 49.2 | `{"text": 5}` | `submission_artifacts/agent_decision_cases/standard_clause_entity_plan/retrieval/retrieval_chunks.jsonl` |
| 2 | 0 | 0 | 0 | 133.0 | `{"text": 2}` | `submission_artifacts/agent_decision_cases/workflow_diagram_agent_plan/retrieval/retrieval_chunks.jsonl` |
| 2 | 0 | 0 | 0 | 115.0 | `{"table": 1, "text": 1}` | `submission_artifacts/api_smoke/run_2478fc60f3b2/retrieval/retrieval_chunks.jsonl` |
| 6 | 0 | 0 | 0 | 224.8 | `{"table": 1, "text": 5}` | `submission_artifacts/api_smoke/run_pdf_e1354b67a7d7/retrieval/retrieval_chunks.jsonl` |
| 3 | 0 | 0 | 0 | 144.0 | `{"table": 1, "text": 2}` | `submission_artifacts/cases/case_1_financial_report/retrieval/retrieval_chunks.jsonl` |
| 2 | 0 | 0 | 0 | 126.5 | `{"text": 2}` | `submission_artifacts/cases/case_2_low_quality_ocr/retrieval/retrieval_chunks.jsonl` |
| 5 | 0 | 0 | 0 | 49.2 | `{"text": 5}` | `submission_artifacts/cases/case_3_standard_contract/retrieval/retrieval_chunks.jsonl` |
| 2 | 0 | 0 | 0 | 133.0 | `{"text": 2}` | `submission_artifacts/cases/case_4_workflow_diagram/retrieval/retrieval_chunks.jsonl` |
| 3 | 0 | 0 | 0 | 81.0 | `{"table": 1, "text": 2}` | `submission_artifacts/cases/case_5_web_inspection_report/retrieval/retrieval_chunks.jsonl` |
| 5 | 0 | 0 | 0 | 183.0 | `{"table": 2, "text": 3}` | `submission_artifacts/challenge_cases/case_6_cross_page_financial_table/retrieval/retrieval_chunks.jsonl` |
| 4 | 0 | 0 | 0 | 177.0 | `{"table": 1, "text": 3}` | `submission_artifacts/challenge_cases/case_7_noisy_contract_scan/retrieval/retrieval_chunks.jsonl` |
| 4 | 0 | 0 | 0 | 208.8 | `{"table": 1, "text": 3}` | `submission_artifacts/challenge_cases/case_8_industry_standard_matrix/retrieval/retrieval_chunks.jsonl` |
| 4 | 0 | 0 | 0 | 206.2 | `{"table": 1, "text": 3}` | `submission_artifacts/challenge_cases/case_9_incident_workflow_report/retrieval/retrieval_chunks.jsonl` |
| 2 | 0 | 0 | 0 | 57.0 | `{"table": 1, "text": 1}` | `submission_artifacts/failure_recovery_cases/numeric_total_mismatch_html/retrieval/retrieval_chunks.jsonl` |
| 1 | 0 | 0 | 0 | 9.0 | `{"text": 1}` | `submission_artifacts/failure_recovery_cases/ocr_retry_failure_controlled/retrieval/retrieval_chunks.jsonl` |
| 1 | 0 | 0 | 0 | 968.0 | `{"text": 1}` | `submission_artifacts/failure_recovery_cases/ocr_retry_success_controlled/retrieval/retrieval_chunks.jsonl` |
| 1 | 0 | 0 | 0 | 797.0 | `{"text": 1}` | `submission_artifacts/failure_recovery_cases/strict_provenance_failure_controlled/retrieval/retrieval_chunks.jsonl` |
| 1 | 0 | 0 | 0 | 426.0 | `{"text": 1}` | `submission_artifacts/failure_recovery_cases/text_cleanup_mojibake/retrieval/retrieval_chunks.jsonl` |
| 3 | 0 | 0 | 0 | 144.0 | `{"table": 1, "text": 2}` | `submission_artifacts/llm_cases/case_llm_financial_review/retrieval/retrieval_chunks.jsonl` |
| 23 | 0 | 0 | 0 | 2094.7 | `{"table": 1, "text": 22}` | `submission_artifacts/long_document_chunks/public_nist_ai_rmf_full_chunked/chunks/p001_020/retrieval/retrieval_chunks.jsonl` |
| 26 | 0 | 1 | 0 | 1754.2 | `{"table": 9, "text": 17}` | `submission_artifacts/long_document_chunks/public_nist_ai_rmf_full_chunked/chunks/p021_040/retrieval/retrieval_chunks.jsonl` |
| 9 | 0 | 0 | 0 | 1934.1 | `{"text": 9}` | `submission_artifacts/long_document_chunks/public_nist_ai_rmf_full_chunked/chunks/p041_048/retrieval/retrieval_chunks.jsonl` |
| 2 | 0 | 0 | 0 | 331.5 | `{"text": 2}` | `submission_artifacts/mineru_cases/case_mineru_cli_contract_pdf/retrieval/retrieval_chunks.jsonl` |
| 2 | 0 | 0 | 0 | 324.5 | `{"text": 2}` | `submission_artifacts/mineru_cases/case_mineru_cli_financial_pdf/retrieval/retrieval_chunks.jsonl` |
| 3 | 0 | 0 | 0 | 1806.0 | `{"text": 3}` | `submission_artifacts/mineru_cases/case_mineru_cli_low_quality_pdf/retrieval/retrieval_chunks.jsonl` |
| 3 | 0 | 0 | 0 | 142.7 | `{"text": 3}` | `submission_artifacts/mineru_cases/case_mineru_cli_workflow_pdf/retrieval/retrieval_chunks.jsonl` |
| 3 | 0 | 0 | 0 | 220.3 | `{"table": 1, "text": 2}` | `submission_artifacts/office_cases/case_docx_standard_review/retrieval/retrieval_chunks.jsonl` |
| 4 | 0 | 0 | 0 | 144.8 | `{"table": 1, "text": 3}` | `submission_artifacts/office_cases/case_pptx_workflow_review/retrieval/retrieval_chunks.jsonl` |
| 5 | 0 | 0 | 0 | 629.2 | `{"text": 5}` | `submission_artifacts/public_real_cases/public_cdc_vis_instructions/retrieval/retrieval_chunks.jsonl` |
| 22 | 0 | 0 | 0 | 1775.7 | `{"table": 10, "text": 12}` | `submission_artifacts/public_real_cases/public_irs_w4_form/retrieval/retrieval_chunks.jsonl` |
| 48 | 0 | 0 | 0 | 1243.5 | `{"table": 3, "text": 45}` | `submission_artifacts/public_real_cases/public_microsoft_annual_report/retrieval/retrieval_chunks.jsonl` |
| 23 | 0 | 0 | 0 | 2094.7 | `{"table": 1, "text": 22}` | `submission_artifacts/public_real_cases/public_nist_ai_rmf/retrieval/retrieval_chunks.jsonl` |
| 2 | 0 | 0 | 0 | 331.5 | `{"text": 2}` | `submission_artifacts/recovery_cases/case_pdf_llm_api_to_cli_fallback/retrieval/retrieval_chunks.jsonl` |

## Label Query Smoke

| Case | Queries | Top-3 Hits |
| --- | ---: | ---: |
| html_financial_report | 3 | 3 |
| html_low_quality_ocr | 3 | 3 |
| html_contract | 3 | 3 |
| html_workflow | 3 | 3 |
| mineru_cli_financial_pdf | 3 | 3 |
| mineru_cli_contract_pdf | 3 | 3 |
| office_docx_standard | 3 | 3 |
| office_pptx_workflow | 3 | 3 |
| pdf_llm_api_to_cli_fallback | 3 | 3 |
| challenge_cross_page_financial | 3 | 3 |
| challenge_noisy_contract_scan | 3 | 3 |
| challenge_industry_standard_matrix | 3 | 3 |
| challenge_incident_workflow_report | 3 | 3 |
| public_irs_w4_form | 8 | 6 |
| public_nist_ai_rmf | 11 | 9 |
| public_microsoft_annual_report | 10 | 10 |
| public_cdc_vis_instructions | 8 | 6 |

## Notes

- This is a schema, de-duplication, density, and lexical top-k smoke test.
- It does not run an embedding model and should not be presented as a vector database benchmark.
- A production retrieval benchmark should add a fixed embedding model, query set, and human relevance labels.
