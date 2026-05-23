# Stability Report

This report checks saved submission artifacts referenced by `examples/evaluation/labels.json`.
It verifies result/trace presence and summarizes execution evidence. It is not a high-concurrency load test.

## Aggregate

- Cases checked: 17
- Completed or inferred-completed traces: 17/17
- Result files checked: 17
- Trace files checked: 17
- Total trace steps: 106
- Total tool calls: 11
- Total tool elapsed seconds: 240.107
- Max single-tool elapsed seconds: 89.128
- Recovery executed cases: 4
- Quality status counts: `{"pass": 12, "pass_with_warnings": 5}`
- Provenance level counts: `{"document": 13, "page": 4}`
- Tool counts: `{"cached-mineru-cli-fallback": 1, "mineru-agent-api": 6, "mineru-cli": 2, "offline-llm": 1, "offline-llm-preplan": 1}`

## Cases

| Case | Trace | Quality | Provenance | Steps | Tools | Recovery | Tool Seconds |
| --- | --- | --- | --- | ---: | ---: | --- | ---: |
| html_financial_report | completed | pass (100) | document | 6 | 0 | false / initial | 0 |
| html_low_quality_ocr | completed | pass (100) | document | 7 | 0 | true / text_cleanup | 0 |
| html_contract | completed | pass (100) | document | 6 | 0 | false / initial | 0 |
| html_workflow | completed | pass (100) | document | 6 | 0 | false / initial | 0 |
| mineru_cli_financial_pdf | completed_inferred | pass (100) | page | 5 | 1 | false / initial | 89.128 |
| mineru_cli_contract_pdf | completed_inferred | pass (100) | page | 5 | 1 | false / initial | 82.932 |
| office_docx_standard | completed_inferred | pass (100) | document | 6 | 0 | false / initial | 0 |
| office_pptx_workflow | completed_inferred | pass (100) | page | 6 | 0 | false / initial | 0 |
| pdf_llm_api_to_cli_fallback | completed | pass (100) | page | 9 | 4 | true / cli_fallback | 8.38 |
| challenge_cross_page_financial | completed | pass_with_warnings (92) | document | 6 | 0 | false / initial | 0 |
| challenge_noisy_contract_scan | completed | pass (100) | document | 7 | 0 | true / text_cleanup | 0 |
| challenge_industry_standard_matrix | completed | pass (100) | document | 6 | 0 | false / initial | 0 |
| challenge_incident_workflow_report | completed | pass (100) | document | 6 | 0 | false / initial | 0 |
| public_irs_w4_form | completed | pass_with_warnings (76) | document | 6 | 1 | false / initial | 16.277 |
| public_nist_ai_rmf | completed | pass_with_warnings (92) | document | 6 | 1 | false / initial | 11.934 |
| public_microsoft_annual_report | completed | pass_with_warnings (76) | document | 6 | 1 | false / initial | 16.17 |
| public_cdc_vis_instructions | completed | pass_with_warnings (84) | document | 7 | 2 | true / initial | 15.286 |

## Boundary

- This report summarizes saved artifact stability and trace completeness.
- It does not prove high-concurrency behavior; a separate live load test is still recommended before a production claim.
