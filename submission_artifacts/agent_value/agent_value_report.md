# Agent Value Report

Saved-artifact report of what the Agent layer adds on top of parser Markdown/content_list artifacts.

## Aggregate

- Cases: 37
- Decision modes: `{"controlled_fault_injection": 5, "deterministic_rules": 25, "llm_enabled_saved_result_without_live_trace": 1, "offline_scripted_decision_regression": 5, "saved_live_llm_trace": 1}`
- Parser runners: `{"-": 12, "agent-api": 8, "cli": 3, "native": 14}`
- With state machine: 11
- With runtime recovery plan: 11
- With task_result: 13
- With field evidence: 14
- With quality issues: 31
- With recovery attempts beyond initial: 8
- Selected non-initial recovery: 6
- With retrieval chunks: 37
- With live LLM trace calls: 1

## Agent-Layer Fields Checked

- `execution_control.planning_rationale`
- `execution_control.adaptive_decision`
- `execution_control.agent_action_plan`
- `execution_control.agent_action_plan.state_machine`
- `execution_control.runtime_recovery_plan`
- `execution_control.replan_after_quality`
- `quality.issues`
- `recovery_decision`
- `extracted.field_evidence`
- `extracted.task_result`
- `retrieval_export`
- `trace.json`
- `summary.md`

## Case Rows

| Case | Mode | Runner | Schema | State | Quality | Recovery | Evidence | Retrieval |
| --- | --- | --- | ---: | --- | --- | --- | ---: | ---: |
| `submission_artifacts/adaptive_cases/case_financial_anomaly_evidence_query/result.json` | `deterministic_rules` | `native` | 8 | - | pass (100) | accept / initial | 5 | 3 |
| `submission_artifacts/adaptive_cases/case_financial_growth_query/result.json` | `deterministic_rules` | `native` | 12 | - | pass (100) | accept / initial | 5 | 3 |
| `submission_artifacts/agent_api_cases/case_agent_api_contract_pdf/result.json` | `deterministic_rules` | `-` | 0 | - | pass_with_warnings (92) | accept_with_review_notes / initial | 0 | 6 |
| `submission_artifacts/agent_decision_cases/cross_page_table_agent_plan/result.json` | `offline_scripted_decision_regression` | `native` | 12 | yes | pass_with_warnings (92) | manual_numeric_review / initial | 6 | 5 |
| `submission_artifacts/agent_decision_cases/financial_growth_agent_plan/result.json` | `offline_scripted_decision_regression` | `native` | 14 | yes | pass (100) | accept / initial | 5 | 3 |
| `submission_artifacts/agent_decision_cases/noisy_contract_recovery_plan/result.json` | `offline_scripted_decision_regression` | `native` | 8 | yes | pass (100) | recovered_accept / text_cleanup | 4 | 4 |
| `submission_artifacts/agent_decision_cases/standard_clause_entity_plan/result.json` | `offline_scripted_decision_regression` | `native` | 10 | yes | pass (100) | accept / initial | 4 | 5 |
| `submission_artifacts/agent_decision_cases/workflow_diagram_agent_plan/result.json` | `offline_scripted_decision_regression` | `native` | 10 | yes | pass (100) | accept / initial | 5 | 2 |
| `submission_artifacts/cases/case_1_financial_report/result.json` | `deterministic_rules` | `-` | 0 | - | pass (100) | accept / initial | 0 | 3 |
| `submission_artifacts/cases/case_2_low_quality_ocr/result.json` | `deterministic_rules` | `-` | 0 | - | pass (100) | recovered_accept / text_cleanup | 0 | 2 |
| `submission_artifacts/cases/case_3_standard_contract/result.json` | `deterministic_rules` | `-` | 0 | - | pass (100) | accept / initial | 0 | 5 |
| `submission_artifacts/cases/case_4_workflow_diagram/result.json` | `deterministic_rules` | `-` | 0 | - | pass (100) | accept / initial | 0 | 2 |
| `submission_artifacts/cases/case_5_web_inspection_report/result.json` | `deterministic_rules` | `-` | 0 | - | pass (100) | accept / initial | 0 | 3 |
| `submission_artifacts/challenge_cases/case_6_cross_page_financial_table/result.json` | `deterministic_rules` | `native` | 0 | - | pass_with_warnings (92) | manual_numeric_review / initial | 0 | 5 |
| `submission_artifacts/challenge_cases/case_7_noisy_contract_scan/result.json` | `deterministic_rules` | `native` | 0 | - | pass (100) | recovered_accept / text_cleanup | 0 | 4 |
| `submission_artifacts/challenge_cases/case_8_industry_standard_matrix/result.json` | `deterministic_rules` | `native` | 0 | - | pass (100) | accept / initial | 0 | 4 |
| `submission_artifacts/challenge_cases/case_9_incident_workflow_report/result.json` | `deterministic_rules` | `native` | 0 | - | pass (100) | accept / initial | 0 | 4 |
| `submission_artifacts/failure_recovery_cases/numeric_total_mismatch_html/result.json` | `controlled_fault_injection` | `native` | 7 | yes | pass_with_warnings (92) | manual_numeric_review / initial | 0 | 2 |
| `submission_artifacts/failure_recovery_cases/ocr_retry_failure_controlled/result.json` | `controlled_fault_injection` | `cli` | 3 | yes | pass_with_warnings (92) | retry_or_manual_review / initial | 0 | 1 |
| `submission_artifacts/failure_recovery_cases/ocr_retry_success_controlled/result.json` | `controlled_fault_injection` | `cli` | 3 | yes | pass (100) | recovered_accept / ocr_retry | 1 | 1 |
| `submission_artifacts/failure_recovery_cases/strict_provenance_failure_controlled/result.json` | `controlled_fault_injection` | `cli` | 6 | yes | needs_review (54) | strict_page_provenance_failed / initial | 1 | 1 |
| `submission_artifacts/failure_recovery_cases/text_cleanup_mojibake/result.json` | `controlled_fault_injection` | `native` | 5 | yes | pass_with_warnings (92) | recovered_with_review_notes / text_cleanup | 2 | 1 |
| `submission_artifacts/llm_cases/case_llm_financial_review/result.json` | `saved_live_llm_trace` | `native` | 0 | - | pass (100) | accept / initial | 5 | 3 |
| `submission_artifacts/long_document_chunks/public_nist_ai_rmf_full_chunked/chunks/p001_020/result.json` | `deterministic_rules` | `agent-api` | 0 | - | pass_with_warnings (92) | accept_with_review_notes / initial | 9 | 23 |
| `submission_artifacts/long_document_chunks/public_nist_ai_rmf_full_chunked/chunks/p021_040/result.json` | `deterministic_rules` | `agent-api` | 0 | - | pass_with_warnings (92) | accept_with_review_notes / initial | 8 | 26 |
| `submission_artifacts/long_document_chunks/public_nist_ai_rmf_full_chunked/chunks/p041_048/result.json` | `deterministic_rules` | `agent-api` | 0 | - | pass_with_warnings (92) | accept_with_review_notes / initial | 0 | 9 |
| `submission_artifacts/mineru_cases/case_mineru_cli_contract_pdf/result.json` | `deterministic_rules` | `-` | 0 | - | pass (100) | accept / initial | 0 | 2 |
| `submission_artifacts/mineru_cases/case_mineru_cli_financial_pdf/result.json` | `deterministic_rules` | `-` | 0 | - | pass (100) | accept / initial | 0 | 2 |
| `submission_artifacts/mineru_cases/case_mineru_cli_low_quality_pdf/result.json` | `deterministic_rules` | `-` | 0 | - | pass (100) | accept / initial | 0 | 3 |
| `submission_artifacts/mineru_cases/case_mineru_cli_workflow_pdf/result.json` | `deterministic_rules` | `-` | 0 | - | pass (100) | accept / initial | 0 | 3 |
| `submission_artifacts/office_cases/case_docx_standard_review/result.json` | `deterministic_rules` | `-` | 0 | - | pass (100) | accept / initial | 0 | 3 |
| `submission_artifacts/office_cases/case_pptx_workflow_review/result.json` | `deterministic_rules` | `-` | 0 | - | pass (100) | accept / initial | 0 | 4 |
| `submission_artifacts/public_real_cases/public_cdc_vis_instructions/result.json` | `deterministic_rules` | `agent-api` | 0 | - | pass_with_warnings (84) | accept_with_review_notes / initial | 0 | 5 |
| `submission_artifacts/public_real_cases/public_irs_w4_form/result.json` | `deterministic_rules` | `agent-api` | 0 | - | pass_with_warnings (76) | manual_numeric_review / initial | 0 | 22 |
| `submission_artifacts/public_real_cases/public_microsoft_annual_report/result.json` | `deterministic_rules` | `agent-api` | 0 | - | pass_with_warnings (76) | manual_numeric_review / initial | 0 | 48 |
| `submission_artifacts/public_real_cases/public_nist_ai_rmf/result.json` | `deterministic_rules` | `agent-api` | 0 | - | pass_with_warnings (92) | accept_with_review_notes / initial | 0 | 23 |
| `submission_artifacts/recovery_cases/case_pdf_llm_api_to_cli_fallback/result.json` | `llm_enabled_saved_result_without_live_trace` | `agent-api` | 10 | yes | pass (100) | recovered_accept / cli_fallback | 6 | 2 |

## Boundaries

- This is not a third-party parser benchmark and does not claim higher OCR/parser accuracy than raw MinerU.
- It compares saved parser artifacts against saved Agent-layer audit, validation, recovery, and export fields.
- Offline agent_decision_cases are counted separately from live LLM traces.
- Controlled failure_recovery_cases are fault-injection evidence, not live OCR/network/GPU evidence.
