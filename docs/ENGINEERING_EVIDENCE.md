# Engineering Evidence Matrix

This matrix maps likely Track 2 review questions to local files that can be checked.

| Risk | Current Evidence | Remaining Boundary |
| --- | --- | --- |
| Task planning explainability is weak | `result.json.execution_control` records requested/initial/resolved controls, applied/ignored LLM recommendations, planning rationale, and `adaptive_decision` with task intents, target schema, post-processors, quality thresholds, and recovery strategy. `submission_artifacts/adaptive_cases/` shows the same input document producing different plans and `task_result` for growth ranking vs anomaly-evidence review. | It is deterministic adaptive planning plus optional LLM merge, not a full multi-turn conversation planner. |
| Recovery chain is incomplete | `recovery_decision.attempts` records initial, text cleanup, OCR retry, and CLI fallback attempts. Evidence includes `case_pdf_llm_api_to_cli_fallback` and `case_7_noisy_contract_scan`. | API-to-CLI fallback evidence currently uses cached CLI artifact in this environment; live full-chain evidence needs a real MinerU CLI executable. |
| Cost/speed/quality tradeoff is not quantified | `submission_artifacts/stability/stability_report.md` summarizes 17 saved cases, tool calls, tool elapsed seconds, recovery count, quality status, and provenance distribution. `submission_artifacts/baseline_comparison/baseline_comparison.md` groups saved artifacts by runner/scenario and compares labeled checks, quality, tool seconds, page provenance, and recovery. `submission_artifacts/http_load_test/http_load_test_report.md` and `submission_artifacts/http_load_test_100/http_load_test_report.md` add 12-request/concurrency-6 and 100-request/concurrency-20 live HTTP loopback results. `submission_artifacts/long_document_chunks/public_nist_ai_rmf_full_chunked/long_document_chunk_report.md` adds a 48-page, 3-chunk live online API long-document run. `submission_artifacts/llm_cost/llm_cost_report.md` audits live LLM token usage. | The comparison is based on saved artifacts and lightweight labels; the HTTP tests are local loopback, not public network/GPU/cloud-cost benchmarks. Cost remains unset unless official token prices are configured. |
| Complex scenarios are not covered | Evidence covers public real PDFs, a chunked long public PDF, challenge fixtures, local MinerU CLI PDFs, Office files, API smoke, recovery, and LLM-enabled analysis. | More real scanned documents and figure-heavy engineering drawings would still strengthen the submission. |
| Output schema is not fixed | `docs/API_CONTRACT.md` defines stable top-level response fields. `result.json` uses consistent sections/tables/key-values/numeric facts/semantic signals/quality/recovery/retrieval/trace fields. New runs add `execution_control.adaptive_decision.target_schema` and `extracted.task_result` so task-specific schemas are explicit rather than implicit. | Extracted domain fields remain document-dependent by design; downstream consumers should use `key_value_map`, task_result, evidence checks, and retrieval chunks. |
| Missing confidence/source evidence | New runs write `extracted.field_evidence` and `field_evidence_map` with key, value, confidence proxy, evidence text, and line/page/block provenance. Quality issues include evidence payloads; retrieval chunks include page/document provenance; numeric/table evaluation checks exact evidence fragments. | Confidence is a deterministic evidence proxy, not a calibrated ML confidence score. Bbox is only preserved when the upstream parser provides it; online API path can still lack page-level provenance. |
| Logs are not verifiable | `trace.json` records input, steps, tool calls, timing, status, error summaries, result path, and summary path. Failure tests verify failed traces are written. | Some older collected artifacts infer completion from completed steps because older trace writers did not set top-level `status`. |
| Reproducibility material is incomplete | `Dockerfile`, `docker-compose.yml`, `README.md`, `docs/DEPLOYMENT_AND_API.md`, `docs/API_CONTRACT.md`, `pyproject.toml`, tests, and artifact scripts document install, run, API, testing, logs, and evidence generation. | Docker covers CPU API reproduction; full MinerU CLI/GPU pipeline still depends on HeyWhale MinerU image or a local MinerU installation. |
| API is not evaluation-friendly | `docs/API_CONTRACT.md` defines request fields, response schema, async `/v1/jobs`, polling `/v1/jobs/{job_id}`, and structured error codes. API persists trace/result/summary paths after response. | Public auth/rate limiting is expected at deployment gateway; this repo does not ship a permanent hosted endpoint. |
| Technical report is too feature-oriented | `docs/TECHNICAL_REPORT.md`, `docs/CASE_STUDIES.md`, `docs/EVALUATION_STRATEGY.md`, and this matrix point to evidence artifacts, failures, boundaries, and metrics. | A short PPT or demo video would improve reviewer scanning speed. |
| Open-source quality is weak | MIT license, README, `CONTRIBUTING.md`, issue templates, tests, GitHub Actions, docs, scripts, examples, submission artifacts, and `docs/BENCHMARK_AND_ROADMAP.md` are included. | The roadmap is documented, but external baselines and larger public benchmark labels are still future work. |

## Key Artifact Pointers

- Evaluation metrics: `submission_artifacts/evaluation/evaluation_metrics.md`
- Adaptive planning evidence: `submission_artifacts/adaptive_cases/`
- Stability report: `submission_artifacts/stability/stability_report.md`
- API load smoke: `submission_artifacts/api_load_smoke/api_load_smoke_report.md`
- Live HTTP load smoke: `submission_artifacts/http_load_test/http_load_test_report.md`
- 100-request HTTP load smoke: `submission_artifacts/http_load_test_100/http_load_test_report.md`
- Long-document chunked API smoke: `submission_artifacts/long_document_chunks/public_nist_ai_rmf_full_chunked/long_document_chunk_report.md`
- Baseline/tradeoff comparison: `submission_artifacts/baseline_comparison/baseline_comparison.md`
- LLM cost audit: `submission_artifacts/llm_cost/llm_cost_report.md`
- Benchmark roadmap: `docs/BENCHMARK_AND_ROADMAP.md`
- Public real-document evidence: `submission_artifacts/public_real_cases/`
- Recovery evidence: `submission_artifacts/recovery_cases/case_pdf_llm_api_to_cli_fallback/`
- API smoke evidence: `submission_artifacts/api_smoke/`
- API contract: `docs/API_CONTRACT.md`

## Recommended Reviewer Reading Order

1. `README.md`
2. `docs/COMPETITION_ALIGNMENT.md`
3. `docs/API_CONTRACT.md`
4. `submission_artifacts/evaluation/evaluation_metrics.md`
5. `submission_artifacts/stability/stability_report.md`
6. `submission_artifacts/baseline_comparison/baseline_comparison.md`
7. `submission_artifacts/http_load_test/http_load_test_report.md`
8. `docs/CASE_STUDIES.md`
