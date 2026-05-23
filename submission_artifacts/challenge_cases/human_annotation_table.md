# Challenge Case Human Annotation Table

These four fixtures add more adversarial and realistic document shapes to the submission evidence.
They are synthetic and public-submission-safe; they are not external customer data.

| Case | Main Challenge | Human Labels | Quality | Recovery |
| --- | --- | --- | --- | --- |
| case_6_cross_page_financial_table | cross-page-style financial subtotal and total | Document ID=FIN-CROSS-2026-06; Reporting Period=2026-01-01 to 2026-03-31; Owner=Finance Shared Service Center; Expected risk=subtotal and total rows are separated by a page break | pass_with_warnings (92/100) | executed=false, selected=initial |
| case_7_noisy_contract_scan | OCR noise and cleanup recovery | Contract No=OCR-NOISE-2026-17; Effective Date=2026-05-21; Expected recovery=text cleanup recovery; Expected issue=possible_mojibake | pass (100/100) | executed=true, selected=text_cleanup |
| case_8_industry_standard_matrix | industry standard compliance matrix | Standard ID=STD-MATRIX-2026-09; Review Date=2026-05-22; Owner=Quality Engineering Office; Critical requirement=secret scan excludes API keys; Recovery linkage=PDF recovery evidence records executed=true | pass (100/100) | executed=false, selected=initial |
| case_9_incident_workflow_report | workflow recovery evidence and timeline | Incident ID=OPS-INC-2026-0519; Report Date=2026-05-23; Referenced selected attempt=cli_fallback in the separate PDF recovery case; Referenced action=route no_page_provenance to CLI fallback when a CLI environment is available | pass (100/100) | executed=false, selected=initial |
