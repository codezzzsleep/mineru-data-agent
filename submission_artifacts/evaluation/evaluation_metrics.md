# Evaluation Metrics

This report compares saved submission artifacts against lightweight human labels.

## Aggregate

- Cases: 8
- Expected-field accuracy: 100.0% (24/24)
- Profile accuracy: 100.0% (8/8)
- Structure gate pass rate: 100.0% (8/8)
- Quality gate pass rate: 100.0% (8/8)
- Provenance gate pass rate: 100.0% (8/8)

## Cases

| Case | Field Accuracy | Profile | Structure | Quality | Provenance | Result |
| --- | ---: | --- | --- | --- | --- | --- |
| html_financial_report | 100.0% | pass | pass | pass | pass | `submission_artifacts\cases\case_1_financial_report\result.json` |
| html_low_quality_ocr | 100.0% | pass | pass | pass | pass | `submission_artifacts\cases\case_2_low_quality_ocr\result.json` |
| html_contract | 100.0% | pass | pass | pass | pass | `submission_artifacts\cases\case_3_standard_contract\result.json` |
| html_workflow | 100.0% | pass | pass | pass | pass | `submission_artifacts\cases\case_4_workflow_diagram\result.json` |
| mineru_cli_financial_pdf | 100.0% | pass | pass | pass | pass | `submission_artifacts\mineru_cases\case_mineru_cli_financial_pdf\result.json` |
| mineru_cli_contract_pdf | 100.0% | pass | pass | pass | pass | `submission_artifacts\mineru_cases\case_mineru_cli_contract_pdf\result.json` |
| office_docx_standard | 100.0% | pass | pass | pass | pass | `submission_artifacts\office_cases\case_docx_standard_review\result.json` |
| office_pptx_workflow | 100.0% | pass | pass | pass | pass | `submission_artifacts\office_cases\case_pptx_workflow_review\result.json` |

## Notes

- Field accuracy here measures labeled key-value expectations, not full OCR character accuracy.
- Structure gates check minimum sections, tables, numeric facts, retrieval chunks, and issue codes where labels define them.
- This complements the trace/artifact evidence and gives reviewers a reproducible scoring surface.
