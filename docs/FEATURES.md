# Detailed Feature List

This document was extracted from the README to keep it concise.

## Core Capabilities

- Task intent recognition, adaptive execution plans, dynamic schema
- Configurable profile inference: keyword + deterministic similarity scoring
- Agent action plan with sub-task decomposition and replan triggers
- PDF/Office/HTML structured parsing adapters
- Markdown, tables, key-value pairs, numeric facts, semantic signal extraction
- Text quality, page provenance, financial figure, contract/structure validators
- Optional DeepSeek/ModelScope LLM pre-execution planning
- Auto-recovery: encoding noise cleanup, OCR retry, CLI fallback
- Cross-run local memory (SQLite) for recovery path reuse
- Retrieval chunks export (JSONL) for downstream RAG
- CLI-first execution and batch orchestration
- Optional FastAPI sync + async job/polling wrapper for local integration tests

## Live LLM Agent Evidence

`agent_live.py` provides a real OpenAI-compatible tool-calling harness exposed as the CLI command `data-agent agent-run`. The HTTP API is optional and intentionally does not expose a live-agent endpoint. The saved report in `submission_artifacts/agent_live_cases/agent_live_report.json` currently records 8 attempted ModelScope Qwen3-235B live runs: 4 reached `completed`, consumed provider tokens, and called `finalize`; after manual answer-quality review, 2 are semantic pass examples and 2 are retained only as live tool-call traces because their final answers are questionable.

| Trace | Turns | Tokens | Tool-call completed | Answer-quality pass | Key observation |
| --- | ---: | ---: | --- | --- | --- |
| Q3 mismatch decline | 7 | 13,230 | true | true | Correctly declined with `not_found` and cited available quarters |
| Low-quality OCR recovery | 10 | 17,708 | true | true | Autonomously triggered `clean_text` before final extraction |
| Financial total check | 8 | 15,724 | true | false | Tool chain completed, but the final numeric consistency statement is self-contradictory |
| Contract obligation analysis | 8 | 12,704 | true | false | Tool chain completed, but the final answer missed contract responsibility content |

Total attempted live-agent tokens: 61,890. Tool-call-completed tokens: 59,366. Answer-quality-pass tokens: 30,938.

## Submission Artifacts Summary

- 17 labeled cases with field-level precision/recall/F1
- 4 public real PDFs (IRS W-4, NIST AI RMF, Microsoft 10-K, CDC VIS)
- Public real-document evidence in `submission_artifacts/public_real_cases/` and long-document chunk evidence in `submission_artifacts/long_document_chunks/`
- 5 controlled failure/recovery negative cases
- 8 attempted live LLM agent traces, with 4 finalize/tool-call completions and 2 manually reviewed answer-quality pass examples
- Cost/speed/quality tradeoff model with replaceable May 2026 scenario assumptions, not contractual pricing claims
- Saved HTTP load evidence is retained as secondary engineering evidence; CI now uses CLI smoke commands as the primary regression gate
