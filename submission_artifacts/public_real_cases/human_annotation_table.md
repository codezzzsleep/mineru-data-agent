# Public Real Document Human Annotation Table

These cases use official public documents to complement synthetic fixtures and challenge cases.
They are intended to test external generalization at a lightweight, sample-labeled level.

| Case | Public Source | Type | Labels | Quality | Chunks |
| --- | --- | --- | --- | --- | ---: |
| public_irs_w4_form | Internal Revenue Service | official public PDF form | document_title=Employee's Withholding Certificate; issuer=Department of the Treasury Internal Revenue Service; year=2026; document_family=Form W-4 | pass_with_warnings (76/100) | 22 |
| public_nist_ai_rmf | National Institute of Standards and Technology | official public framework PDF | document_title=Artificial Intelligence Risk Management Framework (AI RMF 1.0); publication_id=NIST AI 100-1; issuer=National Institute of Standards and Technology; publication_date=January 2023 | pass_with_warnings (92/100) | 23 |
| public_microsoft_annual_report | U.S. Securities and Exchange Commission | official SEC annual report PDF exhibit | company=Microsoft Corporation; report_title=2024 Annual Report; filing_source=SEC EDGAR; fiscal_year=2024 | pass_with_warnings (76/100) | 48 |
| public_cdc_vis_instructions | Centers for Disease Control and Prevention | official public health instruction PDF | document_topic=Vaccine Information Statements; issuer=Centers for Disease Control and Prevention; legal_context=federal law requires VIS distribution | pass_with_warnings (84/100) | 5 |
