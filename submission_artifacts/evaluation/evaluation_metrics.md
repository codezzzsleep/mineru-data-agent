# Evaluation Metrics

This report compares saved submission artifacts against lightweight human labels.

## Aggregate

- Cases: 13
- Expected-field accuracy: 100.0% (39/39)
- Profile accuracy: 100.0% (13/13)
- Structure gate pass rate: 100.0% (13/13)
- Quality gate pass rate: 100.0% (13/13)
- Provenance gate pass rate: 100.0% (13/13)
- Recovery gate pass rate: 100.0% (2/2)

## Cases

| Case | Field Accuracy | Profile | Structure | Quality | Provenance | Recovery | Result |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| html_financial_report | 100.0% | pass | pass | pass | pass | pass | `submission_artifacts\cases\case_1_financial_report\result.json` |
| html_low_quality_ocr | 100.0% | pass | pass | pass | pass | pass | `submission_artifacts\cases\case_2_low_quality_ocr\result.json` |
| html_contract | 100.0% | pass | pass | pass | pass | pass | `submission_artifacts\cases\case_3_standard_contract\result.json` |
| html_workflow | 100.0% | pass | pass | pass | pass | pass | `submission_artifacts\cases\case_4_workflow_diagram\result.json` |
| mineru_cli_financial_pdf | 100.0% | pass | pass | pass | pass | pass | `submission_artifacts\mineru_cases\case_mineru_cli_financial_pdf\result.json` |
| mineru_cli_contract_pdf | 100.0% | pass | pass | pass | pass | pass | `submission_artifacts\mineru_cases\case_mineru_cli_contract_pdf\result.json` |
| office_docx_standard | 100.0% | pass | pass | pass | pass | pass | `submission_artifacts\office_cases\case_docx_standard_review\result.json` |
| office_pptx_workflow | 100.0% | pass | pass | pass | pass | pass | `submission_artifacts\office_cases\case_pptx_workflow_review\result.json` |
| pdf_llm_api_to_cli_fallback | 100.0% | pass | pass | pass | pass | pass | `submission_artifacts\recovery_cases\case_pdf_llm_api_to_cli_fallback\result.json` |
| challenge_cross_page_financial | 100.0% | pass | pass | pass | pass | pass | `submission_artifacts\challenge_cases\case_6_cross_page_financial_table\result.json` |
| challenge_noisy_contract_scan | 100.0% | pass | pass | pass | pass | pass | `submission_artifacts\challenge_cases\case_7_noisy_contract_scan\result.json` |
| challenge_industry_standard_matrix | 100.0% | pass | pass | pass | pass | pass | `submission_artifacts\challenge_cases\case_8_industry_standard_matrix\result.json` |
| challenge_incident_workflow_report | 100.0% | pass | pass | pass | pass | pass | `submission_artifacts\challenge_cases\case_9_incident_workflow_report\result.json` |

## Notes

- Field accuracy here measures labeled key-value expectations, not full OCR character accuracy.
- Structure gates check minimum sections, tables, numeric facts, retrieval chunks, and issue codes where labels define them.
- Recovery gates check executed recovery decisions, selected attempts, final decisions, and preserved initial issue codes when labels define them.
- This complements the trace/artifact evidence and gives reviewers a reproducible scoring surface.
