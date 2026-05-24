# LLM Impact Report

Saved-artifact comparison of LLM-enabled runs against deterministic runs.

## Aggregate

- compared_pairs: 1
- llm_enabled_pairs: 1
- pairs_with_applied_controls: 0
- pairs_with_recovery_suggestions: 1

## Compared Pairs

| Pair | Baseline quality | LLM quality | Applied controls | Recovery suggestions | Tokens |
| --- | --- | --- | ---: | ---: | ---: |
| financial_html_llm_vs_rules | pass (100) | pass (100) | 0 | 5 | 4309 |

## Decision Details

### financial_html_llm_vs_rules

- Baseline: `submission_artifacts/cases/case_1_financial_report/result.json`
- LLM: `submission_artifacts/llm_cases/case_llm_financial_review/result.json`
- Recommended profile: `financial_report`
- Recommended runner: `cli`
- Recommended method: `auto`
- Quality decision status: `not_present_in_saved_artifact`
- Quality decision: `{}`

## Rerun Plan

Use scripts/run_live_llm_matrix.py with a real provider key for a 5-case live rerun, then run the same manifest without LLM for a larger on/off comparison.

Metrics:
- quality status and score
- field precision/recall/F1
- trace steps and tool calls
- LLM applied/ignored recommendations
- token usage and estimated cost
- recovery decision changes

Minimum next set: 10 cases: 4 financial, 2 noisy OCR, 2 contract/standard, 1 workflow, 1 long document chunk.
