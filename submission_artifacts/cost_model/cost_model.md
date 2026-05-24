# Cost Model

Cost and latency projection from saved artifacts and optional price environment variables.

## Pricing Inputs

- `MINERU_DATA_AGENT_GPU_CNY_PER_HOUR`: `None`
- `MINERU_DATA_AGENT_AGENT_API_CNY_PER_PAGE`: `None`
- `MINERU_DATA_AGENT_ASSUMED_PAGES_PER_PDF`: `20`
- `MINERU_DATA_AGENT_LLM_CNY_PER_MILLION_TOKENS`: `None`

## Scenarios

| Scenario | Saved cases | Avg tool seconds | Labeled checks | Estimated CNY / 100 docs | Formula |
| --- | ---: | ---: | ---: | ---: | --- |
| Native HTML/Office/challenge fixtures without LLM | 10 | 0.0 | 1.0 | 0.0 | `no external parser or LLM price` |
| Local MinerU CLI PDF | 2 | 86.03 | 1.0 | None | `average_tool_seconds * 100 * MINERU_DATA_AGENT_GPU_CNY_PER_HOUR / 3600` |
| MinerU online Agent API PDF | 4 | 14.917 | 1.0 | None | `100 * MINERU_DATA_AGENT_AGENT_API_CNY_PER_PAGE * MINERU_DATA_AGENT_ASSUMED_PAGES_PER_PDF` |
| LLM preplanning and post-parse review | 1 | - | - | None | `tokens_per_saved_doc * 100 * MINERU_DATA_AGENT_LLM_CNY_PER_MILLION_TOKENS / 1_000_000` |

## Decision Tree

- If HTML, DOCX, PPTX, or trusted text-like input: use **native extractor without LLM**. No external parser seconds in saved artifacts; enough for structure, field evidence, and retrieval export.
- If PDF requiring page-level provenance or full MinerU artifacts: use **local MinerU CLI**. Saved CLI PDF cases provide page provenance and intermediate artifacts, with higher runtime.
- If CPU-only environment or quick PDF smoke: use **MinerU online Agent API**. Runs without local GPU but can lack page provenance; fallback to CLI when audit requires it.
- If Ambiguous task, custom schema, or high-risk review: use **enable LLM preplanning and post-parse review**. Adds target schema, verification focus, and recovery suggestions; token cost should be tracked.

## Notes

- Prices are not hard-coded because competition/cloud prices can change.
- Set the listed environment variables to turn formulas into currency estimates.
- Saved quality metrics are lightweight label checks, not full OCR or table-cell benchmarks.
