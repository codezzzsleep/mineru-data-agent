# Evaluation Metrics

This report compares saved submission artifacts against lightweight human labels.

## Aggregate

- Cases: 17
- Expected-field accuracy: 100.0% (39/39)
- Text evidence accuracy: 100.0% (22/22)
- Profile accuracy: 100.0% (17/17)
- Structure gate pass rate: 100.0% (17/17)
- Quality gate pass rate: 100.0% (17/17)
- Provenance gate pass rate: 100.0% (17/17)
- Recovery gate pass rate: 100.0% (2/2)

## Cases

| Case | Field Accuracy | Text Evidence | Profile | Structure | Quality | Provenance | Recovery | Result |
| --- | ---: | ---: | --- | --- | --- | --- | --- | --- |
| html_financial_report | 100.0% | 100.0% | pass | pass | pass | pass | pass | `submission_artifacts\cases\case_1_financial_report\result.json` |
| html_low_quality_ocr | 100.0% | 100.0% | pass | pass | pass | pass | pass | `submission_artifacts\cases\case_2_low_quality_ocr\result.json` |
| html_contract | 100.0% | 100.0% | pass | pass | pass | pass | pass | `submission_artifacts\cases\case_3_standard_contract\result.json` |
| html_workflow | 100.0% | 100.0% | pass | pass | pass | pass | pass | `submission_artifacts\cases\case_4_workflow_diagram\result.json` |
| mineru_cli_financial_pdf | 100.0% | 100.0% | pass | pass | pass | pass | pass | `submission_artifacts\mineru_cases\case_mineru_cli_financial_pdf\result.json` |
| mineru_cli_contract_pdf | 100.0% | 100.0% | pass | pass | pass | pass | pass | `submission_artifacts\mineru_cases\case_mineru_cli_contract_pdf\result.json` |
| office_docx_standard | 100.0% | 100.0% | pass | pass | pass | pass | pass | `submission_artifacts\office_cases\case_docx_standard_review\result.json` |
| office_pptx_workflow | 100.0% | 100.0% | pass | pass | pass | pass | pass | `submission_artifacts\office_cases\case_pptx_workflow_review\result.json` |
| pdf_llm_api_to_cli_fallback | 100.0% | 100.0% | pass | pass | pass | pass | pass | `submission_artifacts\recovery_cases\case_pdf_llm_api_to_cli_fallback\result.json` |
| challenge_cross_page_financial | 100.0% | 100.0% | pass | pass | pass | pass | pass | `submission_artifacts\challenge_cases\case_6_cross_page_financial_table\result.json` |
| challenge_noisy_contract_scan | 100.0% | 100.0% | pass | pass | pass | pass | pass | `submission_artifacts\challenge_cases\case_7_noisy_contract_scan\result.json` |
| challenge_industry_standard_matrix | 100.0% | 100.0% | pass | pass | pass | pass | pass | `submission_artifacts\challenge_cases\case_8_industry_standard_matrix\result.json` |
| challenge_incident_workflow_report | 100.0% | 100.0% | pass | pass | pass | pass | pass | `submission_artifacts\challenge_cases\case_9_incident_workflow_report\result.json` |
| public_irs_w4_form | 100.0% | 100.0% | pass | pass | pass | pass | pass | `submission_artifacts\public_real_cases\public_irs_w4_form\result.json` |
| public_nist_ai_rmf | 100.0% | 100.0% | pass | pass | pass | pass | pass | `submission_artifacts\public_real_cases\public_nist_ai_rmf\result.json` |
| public_microsoft_annual_report | 100.0% | 100.0% | pass | pass | pass | pass | pass | `submission_artifacts\public_real_cases\public_microsoft_annual_report\result.json` |
| public_cdc_vis_instructions | 100.0% | 100.0% | pass | pass | pass | pass | pass | `submission_artifacts\public_real_cases\public_cdc_vis_instructions\result.json` |

## Notes

- Field accuracy here measures labeled key-value expectations, not full OCR character accuracy.
- Text evidence accuracy checks whether lightweight human-labeled facts appear anywhere in the structured output.
- Structure gates check minimum sections, tables, numeric facts, retrieval chunks, and issue codes where labels define them.
- Recovery gates check executed recovery decisions, selected attempts, final decisions, and preserved initial issue codes when labels define them.
- This complements the trace/artifact evidence and gives reviewers a reproducible scoring surface.
