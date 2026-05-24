# Recovery Effectiveness Report

Recovery effectiveness summary over saved submission artifacts.

## Aggregate

- Results with recovery records: 39
- Recovery executed: 8
- Selected non-initial result: 6
- Executed rate: 20.51%
- Selected non-initial rate: 15.38%
- Avg non-initial tool seconds when executed: 2.963
- Attempt counts: `{"cli_fallback": 1, "initial": 39, "ocr_retry": 3, "text_cleanup": 4}`
- Selected attempt counts: `{"cli_fallback": 1, "initial": 33, "ocr_retry": 1, "text_cleanup": 4}`
- Initial issue counts: `{"document_level_provenance": 21, "expected_anomaly_signal_missing": 2, "no_page_provenance": 11, "numeric_total_mismatch": 6, "numeric_total_needs_review": 1, "numeric_total_verified": 9, "possible_mojibake": 4, "short_text": 2, "weak_clause_structure": 1}`
- Failed attempt counts: `{"ocr_retry": 1}`

## Cases

| Result | Decision | Executed | Selected | Initial Issues | Final Quality | LLM Decision |
| --- | --- | --- | --- | --- | --- | --- |
| submission_artifacts/adaptive_cases/case_financial_anomaly_evidence_query/result.json | accept | false | initial | document_level_provenance, numeric_total_verified | pass (100) | false |
| submission_artifacts/adaptive_cases/case_financial_growth_query/result.json | accept | false | initial | document_level_provenance, numeric_total_verified | pass (100) | false |
| submission_artifacts/agent_api_cases/case_agent_api_contract_pdf/result.json | accept_with_review_notes | false | initial | no_page_provenance | pass_with_warnings (92) | false |
| submission_artifacts/agent_decision_cases/cross_page_table_agent_plan/result.json | manual_numeric_review | false | initial | document_level_provenance, numeric_total_verified, numeric_total_mismatch | pass_with_warnings (92) | true |
| submission_artifacts/agent_decision_cases/financial_growth_agent_plan/result.json | accept | false | initial | document_level_provenance, numeric_total_verified | pass (100) | true |
| submission_artifacts/agent_decision_cases/noisy_contract_recovery_plan/result.json | recovered_accept | true | text_cleanup | possible_mojibake, document_level_provenance | pass (100) | true |
| submission_artifacts/agent_decision_cases/standard_clause_entity_plan/result.json | accept | false | initial | document_level_provenance | pass (100) | true |
| submission_artifacts/agent_decision_cases/workflow_diagram_agent_plan/result.json | accept | false | initial | document_level_provenance | pass (100) | true |
| submission_artifacts/api_smoke/run_2478fc60f3b2/result.json | accept | false | initial | document_level_provenance | pass (100) | false |
| submission_artifacts/api_smoke/run_pdf_e1354b67a7d7/result.json | accept_with_review_notes | false | initial | no_page_provenance | pass_with_warnings (92) | false |
| submission_artifacts/cases/case_1_financial_report/result.json | accept | false | initial | document_level_provenance, numeric_total_verified | pass (100) | false |
| submission_artifacts/cases/case_2_low_quality_ocr/result.json | recovered_accept | true | text_cleanup | possible_mojibake, document_level_provenance | pass (100) | false |
| submission_artifacts/cases/case_3_standard_contract/result.json | accept | false | initial | document_level_provenance | pass (100) | false |
| submission_artifacts/cases/case_4_workflow_diagram/result.json | accept | false | initial | document_level_provenance | pass (100) | false |
| submission_artifacts/cases/case_5_web_inspection_report/result.json | accept | false | initial | document_level_provenance | pass (100) | false |
| submission_artifacts/challenge_cases/case_6_cross_page_financial_table/result.json | manual_numeric_review | false | initial | document_level_provenance, numeric_total_verified, numeric_total_mismatch | pass_with_warnings (92) | false |
| submission_artifacts/challenge_cases/case_7_noisy_contract_scan/result.json | recovered_accept | true | text_cleanup | possible_mojibake, document_level_provenance | pass (100) | false |
| submission_artifacts/challenge_cases/case_8_industry_standard_matrix/result.json | accept | false | initial | document_level_provenance | pass (100) | false |
| submission_artifacts/challenge_cases/case_9_incident_workflow_report/result.json | accept | false | initial | document_level_provenance | pass (100) | false |
| submission_artifacts/failure_recovery_cases/numeric_total_mismatch_html/result.json | manual_numeric_review | false | initial | document_level_provenance, numeric_total_mismatch | pass_with_warnings (92) | false |
| submission_artifacts/failure_recovery_cases/ocr_retry_failure_controlled/result.json | retry_or_manual_review | true | initial | short_text | pass_with_warnings (92) | false |
| submission_artifacts/failure_recovery_cases/ocr_retry_success_controlled/result.json | recovered_accept | true | ocr_retry | short_text | pass (100) | false |
| submission_artifacts/failure_recovery_cases/strict_provenance_failure_controlled/result.json | strict_page_provenance_failed | false | initial | no_page_provenance, weak_clause_structure | needs_review (54) | false |
| submission_artifacts/failure_recovery_cases/text_cleanup_mojibake/result.json | recovered_with_review_notes | true | text_cleanup | possible_mojibake, document_level_provenance, expected_anomaly_signal_missing | pass_with_warnings (92) | false |
| submission_artifacts/llm_cases/case_llm_financial_review/result.json | accept | false | initial | document_level_provenance, numeric_total_verified | pass (100) | false |
| submission_artifacts/long_document_chunks/public_nist_ai_rmf_full_chunked/chunks/p001_020/result.json | accept_with_review_notes | false | initial | no_page_provenance | pass_with_warnings (92) | false |
| submission_artifacts/long_document_chunks/public_nist_ai_rmf_full_chunked/chunks/p021_040/result.json | accept_with_review_notes | false | initial | no_page_provenance | pass_with_warnings (92) | false |
| submission_artifacts/long_document_chunks/public_nist_ai_rmf_full_chunked/chunks/p041_048/result.json | accept_with_review_notes | false | initial | no_page_provenance | pass_with_warnings (92) | false |
| submission_artifacts/mineru_cases/case_mineru_cli_contract_pdf/result.json | accept | false | initial | - | pass (100) | false |
| submission_artifacts/mineru_cases/case_mineru_cli_financial_pdf/result.json | accept | false | initial | numeric_total_verified | pass (100) | false |
| submission_artifacts/mineru_cases/case_mineru_cli_low_quality_pdf/result.json | accept | false | initial | - | pass (100) | false |
| submission_artifacts/mineru_cases/case_mineru_cli_workflow_pdf/result.json | accept | false | initial | - | pass (100) | false |
| submission_artifacts/office_cases/case_docx_standard_review/result.json | accept | false | initial | document_level_provenance | pass (100) | false |
| submission_artifacts/office_cases/case_pptx_workflow_review/result.json | accept | false | initial | - | pass (100) | false |
| submission_artifacts/public_real_cases/public_cdc_vis_instructions/result.json | accept_with_review_notes | true | initial | no_page_provenance, expected_anomaly_signal_missing | pass_with_warnings (84) | false |
| submission_artifacts/public_real_cases/public_irs_w4_form/result.json | manual_numeric_review | false | initial | no_page_provenance, numeric_total_needs_review, numeric_total_mismatch | pass_with_warnings (76) | false |
| submission_artifacts/public_real_cases/public_microsoft_annual_report/result.json | manual_numeric_review | false | initial | no_page_provenance, numeric_total_mismatch, numeric_total_verified, numeric_total_mismatch | pass_with_warnings (76) | false |
| submission_artifacts/public_real_cases/public_nist_ai_rmf/result.json | accept_with_review_notes | false | initial | no_page_provenance | pass_with_warnings (92) | false |
| submission_artifacts/recovery_cases/case_pdf_llm_api_to_cli_fallback/result.json | recovered_accept | true | cli_fallback | no_page_provenance | pass (100) | false |

## Interpretation

- Executed recovery means the Agent attempted a second path such as text cleanup, OCR retry, or CLI fallback.
- Selected non-initial means the recovered result replaced the first attempt.
- Cached CLI fallback is counted separately in tool names and should not be presented as live CLI/GPU evidence.
