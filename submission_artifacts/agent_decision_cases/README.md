# Agent Decision Case Pack

Five deterministic local cases that exercise task decomposition, dynamic tool selection, quality-triggered replanning, and LLM-compatible pre/post decision hooks.

Boundary: these cases use a scripted local LLM client so they are reproducible without API keys. They do not replace the saved live ModelScope case in `submission_artifacts/llm_cases/`.

| Case | Profile | Intents | Selected Tools | Replan Issues | LLM Tokens |
| --- | --- | --- | --- | --- | ---: |
| financial_growth_agent_plan | financial_report | comparison, ranking, growth_analysis, evidence_trace | native_extractor, llm_preplanner, structured_extractor, numeric_validator, text_cleanup, llm_post_review, retrieval_exporter | document_level_provenance, numeric_total_verified | 1460 |
| noisy_contract_recovery_plan | low_quality_ocr | structured_extraction | native_extractor, llm_preplanner, structured_extractor, text_cleanup, llm_post_review, retrieval_exporter | document_level_provenance | 1460 |
| standard_clause_entity_plan | standard_or_contract | entity_resolution, evidence_trace | native_extractor, llm_preplanner, structured_extractor, contract_validator, text_cleanup, llm_post_review, retrieval_exporter | document_level_provenance | 1460 |
| workflow_diagram_agent_plan | workflow_or_diagram | anomaly_detection | native_extractor, llm_preplanner, structured_extractor, workflow_validator, text_cleanup, llm_post_review, retrieval_exporter | document_level_provenance | 1460 |
| cross_page_table_agent_plan | financial_report | aggregation, cross_page_reasoning | native_extractor, llm_preplanner, structured_extractor, numeric_validator, text_cleanup, llm_post_review, retrieval_exporter | document_level_provenance, numeric_total_verified, numeric_total_mismatch | 1460 |
