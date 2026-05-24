# Evaluation Guide

This is the shortest path for reviewing the submission.

## 1. What This Project Does

MinerU Data Agent takes PDF, HTML, DOCX, PPTX, or image-like document inputs, runs MinerU or a native extractor, builds structured JSON, writes a trace log, checks quality risks, exports retrieval chunks, and records recovery attempts.

The Agent layer adds task planning, schema selection, field evidence, quality checks, recovery decisions, API/CLI entry points, and optional LLM preplanning/post-parse review.

## 2. Three-Step Reproduction

```bash
pip install -e ".[dev]"
python scripts/build_evaluation_report.py
python scripts/build_coverage_report.py
python scripts/build_artifacts_index.py
```

For API reproduction:

```bash
docker compose up --build
curl http://127.0.0.1:8080/health
```

For LLM reproduction, set a provider key through the environment and run:

```bash
python scripts/run_live_llm_case.py --provider deepseek
python scripts/build_llm_cost_report.py
python scripts/build_llm_impact_report.py
```

## 3. Scoring Map

| Official Dimension | What To Check First | File |
| --- | --- | --- |
| Complex document understanding and structured processing | 17-case labeled metrics, field precision/recall/F1, public PDF cases, PDF CLI cases | `submission_artifacts/evaluation/evaluation_metrics.md`, `submission_artifacts/public_real_cases/`, `submission_artifacts/mineru_cases/` |
| Hard scenario and technical value | Cross-page financial fixture, OCR-noise contract, PDF recovery, long-document chunking and risk notes | `submission_artifacts/challenge_cases/`, `submission_artifacts/recovery_cases/`, `submission_artifacts/long_document_chunks/`, `submission_artifacts/long_document_risk/long_document_risk_report.md` |
| Agent planning and automatic execution | Adaptive planning, offline Agent decision regression cases, LLM preplanning/post-parse review, recovery attempts, batch behavior, recovery aggregate | `submission_artifacts/adaptive_cases/`, `submission_artifacts/agent_decision_cases/README.md`, `submission_artifacts/llm_impact/llm_impact_report.md`, `submission_artifacts/recovery_effectiveness/recovery_effectiveness_report.md` |
| Stability and reproducibility | Docker, API contract, trace aggregation, HTTP loopback load test, coverage, code/test summary | `docs/API_CONTRACT.md`, `submission_artifacts/stability/stability_report.md`, `submission_artifacts/http_load_test_100/http_load_test_report.md`, `submission_artifacts/coverage/coverage_report.md`, `submission_artifacts/code_quality/code_quality_report.md` |
| Open-source and ecosystem value | Repo structure, license, contribution guide, originality notes, artifact index | `README.md`, `LICENSE`, `CONTRIBUTING.md`, `docs/ORIGINALITY_AND_COMPLIANCE.md`, `submission_artifacts/ARTIFACTS_INDEX.md` |

## 4. Key Numbers

| Metric | Current Saved Result | Source |
| --- | --- | --- |
| Labeled cases | 17 | `submission_artifacts/evaluation/evaluation_metrics.md` |
| Expected fields | 45 | `submission_artifacts/evaluation/evaluation_metrics.md` |
| Text evidence checks | 22 | `submission_artifacts/evaluation/evaluation_metrics.md` |
| Numeric evidence checks | 11 | `submission_artifacts/evaluation/evaluation_metrics.md` |
| Table evidence checks | 6 | `submission_artifacts/evaluation/evaluation_metrics.md` |
| HTTP loopback load | 100 requests, concurrency 20, 100/100 success, P95 about 4.21s | `submission_artifacts/http_load_test_100/http_load_test_report.md` |
| Long document chunking | NIST AI RMF 48 pages, 3 chunks, 3/3 success, 58 retrieval chunks | `submission_artifacts/long_document_chunks/public_nist_ai_rmf_full_chunked/long_document_chunk_report.md` |
| LLM usage | 2 calls, 4309 tokens in saved ModelScope case | `submission_artifacts/llm_cost/llm_cost_report.md` |
| Agent decision regression cases | 5 offline local cases with subtask graph, selected tools, quality replan, and scripted decision hooks | `submission_artifacts/agent_decision_cases/README.md` |
| Cost model | 4 mode estimates: native text-like, MinerU CLI, online API, LLM; prices supplied by env vars | `submission_artifacts/cost_model/cost_model.md` |
| Recovery aggregate | 29 saved results with recovery records, 4 executed recovery, 3 selected non-initial | `submission_artifacts/recovery_effectiveness/recovery_effectiveness_report.md` |
| Coverage | Local pytest line coverage for `src/mineru_data_agent` | `submission_artifacts/coverage/coverage_report.md` |
| Code/test scale | Python files, test functions, GitHub Actions workflow present | `submission_artifacts/code_quality/code_quality_report.md` |

## 5. Artifact Navigation

Use `submission_artifacts/ARTIFACTS_INDEX.md` as the directory map. It lists each artifact family, counts result/trace files, and links the main reports.

## 6. Current Limits

The saved submission does not include a public internet load test, a GPU long-document benchmark, or an OCR character/table-cell benchmark. The Agent decision case pack is offline regression evidence with a scripted decision client; it does not count as live LLM evidence. The saved live provider evidence remains the single ModelScope case. The cost model uses formulas unless price environment variables are provided. The repository includes scripts and label schemas to add those measurements without changing the output contract.
