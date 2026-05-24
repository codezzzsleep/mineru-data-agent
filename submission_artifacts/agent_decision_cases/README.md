# Offline Agent Decision Regression Pack

Five deterministic local cases that exercise task decomposition, tool selection, quality-triggered replanning, and the LLM-compatible decision hook schema.

Boundary: these are offline regression cases. They use a scripted local decision client, token counts are synthetic, and they do not count as live LLM evidence. The saved live provider case remains `submission_artifacts/llm_cases/`.

| Case | Profile | Intents | Selected Tools | Replan Issues | Scripted Tokens |
| --- | --- | --- | --- | --- | ---: |
| financial_growth_agent_plan | financial_report | comparison, ranking, growth_analysis, evidence_trace | native_extractor, llm_preplanner, structured_extractor, numeric_validator, text_cleanup, llm_post_review, retrieval_exporter | document_level_provenance, numeric_total_verified | 1460 |
| noisy_contract_recovery_plan | low_quality_ocr | structured_extraction | native_extractor, llm_preplanner, structured_extractor, text_cleanup, llm_post_review, retrieval_exporter | document_level_provenance | 1460 |
| standard_clause_entity_plan | standard_or_contract | entity_resolution, evidence_trace | native_extractor, llm_preplanner, structured_extractor, contract_validator, text_cleanup, llm_post_review, retrieval_exporter | document_level_provenance | 1460 |
| workflow_diagram_agent_plan | workflow_or_diagram | anomaly_detection | native_extractor, llm_preplanner, structured_extractor, workflow_validator, text_cleanup, llm_post_review, retrieval_exporter | document_level_provenance | 1460 |
| cross_page_table_agent_plan | financial_report | aggregation, cross_page_reasoning | native_extractor, llm_preplanner, structured_extractor, numeric_validator, text_cleanup, llm_post_review, retrieval_exporter | document_level_provenance, numeric_total_verified, numeric_total_mismatch | 1460 |
