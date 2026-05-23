# Adaptive Planning Case Pack

Same input document, different natural-language tasks. The evidence checks whether the Agent changes task intents, target schema, post-processors, and task-specific answers.

- Input: `examples/cases/case_1_financial_report.html`

| Case | Task Intents | Schema Keys | Answer Keys | Top Growth |
| --- | --- | --- | --- | --- |
| case_financial_growth_query | comparison, ranking, growth_analysis, evidence_trace | company_name, report_period, line_item, current_value, previous_value, unit, evidence, comparison_base | comparisons, top_growth_candidate, field_evidence | 利润总额 (15.3232%) |
| case_financial_anomaly_evidence_query | anomaly_detection, evidence_trace | company_name, report_period, line_item, current_value, previous_value, unit, evidence, risk_reason | anomaly_candidates, field_evidence |  |
