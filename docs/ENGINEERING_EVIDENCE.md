# Engineering Evidence Matrix

This matrix maps likely Track 2 review questions to local files that can be checked.

| Risk | Current Evidence | Remaining Boundary |
| --- | --- | --- |
| Task planning explainability is weak | `result.json.execution_control` records requested/initial/resolved controls, applied/ignored LLM recommendations, planning rationale, and `adaptive_decision` with task intents, target schema, post-processors, quality thresholds, and recovery strategy. `submission_artifacts/adaptive_cases/` shows the same input document producing different plans and `task_result` for growth ranking vs anomaly-evidence review. | It is deterministic adaptive planning plus optional LLM merge, not a full multi-turn conversation planner. |
| The contribution beyond MinerU is unclear | `submission_artifacts/agent_value/agent_value_report.md` scans 37 saved results and counts the Agent-layer fields added around parser artifacts: adaptive schema, action plan, state machine, quality issues, recovery decisions, field evidence, task result, retrieval export, trace, and summary. It also separates deterministic rules, offline scripted decision regression, controlled fault injection, and saved live LLM traces. | This is an Agent-layer value report, not proof that the underlying OCR/parser is more accurate than raw MinerU. |
| The system looks like a pipeline rather than an Agent | New runs write `execution_control.agent_action_plan` with subtask graph, selected tool registry, dynamic choices, replan triggers, and single-run memory policy. `trace.json` now includes `agent_task_decomposition` and `agent_replan_after_quality` steps. `submission_artifacts/agent_decision_cases/` contains 5 local cases covering financial ranking, OCR cleanup, clause/entity extraction, workflow review, and cross-page table review. | The 5-case pack is offline regression evidence using a scripted decision client. It checks output structure and replan fields, not live model autonomy. Live external LLM evidence is still limited to the saved ModelScope case unless a provider key is used to rerun live cases. |
| Planner branching is not visible | New runs add `execution_control.agent_action_plan.state_machine`, a single-run conditional DAG with dependency edges, quality-triggered recovery edges, runner/method changes, and loop policy. Runtime recovery also writes `execution_control.runtime_recovery_plan`, which is built from action-plan replan triggers plus validator fallback policies and is consumed before text cleanup/OCR retry/CLI fallback attempts run. `execution_control.replan_after_quality.quality_triggered_replan` records which quality issues triggered which candidate actions and what attempt was selected. | This is still a deterministic planner, not a general multi-turn planner with cross-run learning. |
| LLM only suggests but does not affect decisions | LLM preplanning can change whitelisted profile/backend/method/lang controls. New runs also write post-parse `risk_findings` and `recovery_suggestions` into `recovery_decision.llm_quality_decision`, and warning/error findings can change the final recovery decision. `submission_artifacts/llm_impact/llm_impact_report.md` compares saved rule and LLM-enabled runs. | Current saved live LLM comparison has one pair; a larger 10-case on/off run is still the next useful benchmark. |
| Recovery chain is incomplete | `recovery_decision.attempts` records initial, text cleanup, OCR retry, and CLI fallback attempts. Evidence includes `case_pdf_llm_api_to_cli_fallback`, `case_7_noisy_contract_scan`, and controlled fault-injection cases. `submission_artifacts/recovery_effectiveness/recovery_effectiveness_report.md` scans saved results and reports recovery records, executed recoveries, selected non-initial results, issue-code distribution, and extra tool seconds. | API-to-CLI fallback evidence currently uses cached CLI artifact in this environment; live full-chain evidence needs a real MinerU CLI executable. |
| Negative/failure evidence is missing | `submission_artifacts/failure_recovery_cases/` adds controlled fault-injection cases for text cleanup, OCR retry success, OCR retry failure, strict page-provenance failure, and numeric total mismatch. | These are controlled fixtures/fake runners and should not be presented as live OCR, live network, or GPU evidence. |
| Cost/speed/quality tradeoff is not quantified | `submission_artifacts/stability/stability_report.md` summarizes 17 saved cases, tool calls, tool elapsed seconds, recovery count, quality status, and provenance distribution. `submission_artifacts/baseline_comparison/baseline_comparison.md` groups saved artifacts by runner/scenario and compares labeled checks, quality, tool seconds, page provenance, and recovery. `submission_artifacts/http_load_test/http_load_test_report.md` and `submission_artifacts/http_load_test_100/http_load_test_report.md` add 12-request/concurrency-6 and 100-request/concurrency-20 local HTTP loopback results. `submission_artifacts/long_document_chunks/public_nist_ai_rmf_full_chunked/long_document_chunk_report.md` adds a 48-page, 3-chunk live online API long-document run. `submission_artifacts/cost_model/cost_model.md` adds a price-parameterized cost model for native, CLI, online API, and LLM modes. `submission_artifacts/llm_cost/llm_cost_report.md` audits live LLM token usage. | The comparison is based on saved artifacts and lightweight labels; the HTTP tests are local loopback, not public network/GPU/cloud-cost benchmarks. Cost formulas produce currency values only when price environment variables are configured. |
| Complex scenarios are not covered | Evidence covers public real PDFs, a chunked long public PDF, challenge fixtures, local MinerU CLI PDFs, Office files, API smoke, recovery, and LLM-enabled analysis. | More real scanned documents and figure-heavy engineering drawings would still strengthen the submission. |
| Output schema is not fixed | `docs/API_CONTRACT.md` defines stable top-level response fields. `result.json` uses consistent sections/tables/key-values/numeric facts/semantic signals/quality/recovery/retrieval/trace fields. New runs add `execution_control.adaptive_decision.target_schema` and `extracted.task_result` so task-specific schemas are explicit rather than implicit. | Extracted domain fields remain document-dependent by design; downstream consumers should use `key_value_map`, task_result, evidence checks, and retrieval chunks. |
| Retrieval chunks are not validated | `submission_artifacts/retrieval_validation/retrieval_validation_report.md` checks chunk schema, empty text, duplicate text rate, per-type counts, density, and a lightweight lexical top-3 smoke over labeled queries. | This is not an embedding or vector database benchmark; it is a format and lexical retrieval smoke test. |
| Missing confidence/source evidence | New runs write `extracted.field_evidence` and `field_evidence_map` with key, value, confidence proxy, evidence text, and line/page/block provenance. Quality issues include evidence payloads; retrieval chunks include page/document provenance; numeric/table evaluation checks exact evidence fragments. `--strict-page-provenance` marks PDF/image outputs as `needs_review` with `strict_page_provenance_failed` if fallback still cannot provide page evidence. | Confidence is a deterministic evidence proxy, not a calibrated ML confidence score. Bbox is only preserved when the upstream parser provides it; online API path can still lack page-level provenance unless a CLI/provider path supplies it. |
| Long-document chunking hides risk | `submission_artifacts/long_document_chunks/public_nist_ai_rmf_full_chunked/long_document_chunk_report.md` records the 48-page NIST run, page ranges, chunk status, elapsed time, quality, and retrieval chunk counts. `submission_artifacts/long_document_risk/long_document_risk_report.md` separates orchestration success from remaining risks: document-level provenance, cross-chunk context, single-sample coverage, and no GPU CLI long run. | The saved long-document artifact validates the split/execute/aggregate path, not a full 100+ page financial-report benchmark. |
| Logs are not verifiable | `trace.json` records input, steps, tool calls, timing, status, error summaries, result path, and summary path. Failure tests verify failed traces are written. | Some older collected artifacts infer completion from completed steps because older trace writers did not set top-level `status`. |
| Reproducibility material is incomplete | `Dockerfile`, `docker-compose.yml`, `README.md`, `docs/DEPLOYMENT_AND_API.md`, `docs/API_CONTRACT.md`, `pyproject.toml`, tests, and artifact scripts document install, run, API, testing, logs, and evidence generation. | Docker covers CPU API reproduction; full MinerU CLI/GPU pipeline still depends on HeyWhale MinerU image or a local MinerU installation. |
| API is not evaluation-friendly | `docs/API_CONTRACT.md` defines request fields, response schema, async `/v1/jobs`, polling `/v1/jobs/{job_id}`, and structured error codes. API persists trace/result/summary paths after response. | Public auth/rate limiting is expected at deployment gateway; this repo does not ship a permanent hosted endpoint. |
| Technical report is too feature-oriented | `docs/TECHNICAL_REPORT.md`, `docs/CASE_STUDIES.md`, `docs/EVALUATION_STRATEGY.md`, and this matrix point to evidence artifacts, failures, boundaries, and metrics. | A short PPT or demo video would improve reviewer scanning speed. |
| Open-source quality is weak | MIT license, README, `CONTRIBUTING.md`, issue templates, tests, GitHub Actions, docs, scripts, examples, submission artifacts, and `docs/BENCHMARK_AND_ROADMAP.md` are included. `submission_artifacts/code_quality/code_quality_report.md` reports repository size and test count; `submission_artifacts/coverage/coverage_report.md` records local pytest line coverage. | The roadmap is documented, but external baselines and larger public benchmark labels are still future work. Coverage is local unit/integration coverage, not live MinerU/LLM/GPU coverage. |

## Key Artifact Pointers

- Evaluation metrics: `submission_artifacts/evaluation/evaluation_metrics.md`
- Adaptive planning evidence: `submission_artifacts/adaptive_cases/`
- Agent decision regression cases: `submission_artifacts/agent_decision_cases/README.md`
- Agent value report: `submission_artifacts/agent_value/agent_value_report.md`
- Failure/recovery fault injection: `submission_artifacts/failure_recovery_cases/README.md`
- Stability report: `submission_artifacts/stability/stability_report.md`
- API load smoke: `submission_artifacts/api_load_smoke/api_load_smoke_report.md`
- Live HTTP load smoke: `submission_artifacts/http_load_test/http_load_test_report.md`
- 100-request HTTP load smoke: `submission_artifacts/http_load_test_100/http_load_test_report.md`
- Long-document chunked API smoke: `submission_artifacts/long_document_chunks/public_nist_ai_rmf_full_chunked/long_document_chunk_report.md`
- Long-document risk report: `submission_artifacts/long_document_risk/long_document_risk_report.md`
- Retrieval validation: `submission_artifacts/retrieval_validation/retrieval_validation_report.md`
- Baseline/tradeoff comparison: `submission_artifacts/baseline_comparison/baseline_comparison.md`
- Cost model: `submission_artifacts/cost_model/cost_model.md`
- LLM cost audit: `submission_artifacts/llm_cost/llm_cost_report.md`
- LLM impact comparison: `submission_artifacts/llm_impact/llm_impact_report.md`
- Recovery effectiveness: `submission_artifacts/recovery_effectiveness/recovery_effectiveness_report.md`
- Coverage: `submission_artifacts/coverage/coverage_report.md`
- Code quality: `submission_artifacts/code_quality/code_quality_report.md`
- Artifact index: `submission_artifacts/ARTIFACTS_INDEX.md`
- Benchmark roadmap: `docs/BENCHMARK_AND_ROADMAP.md`
- Public real-document evidence: `submission_artifacts/public_real_cases/`
- Recovery evidence: `submission_artifacts/recovery_cases/case_pdf_llm_api_to_cli_fallback/`
- API smoke evidence: `submission_artifacts/api_smoke/`
- API contract: `docs/API_CONTRACT.md`

## Recommended Reviewer Reading Order

1. `README.md`
2. `docs/EVALUATION_GUIDE.md`
3. `submission_artifacts/ARTIFACTS_INDEX.md`
4. `docs/COMPETITION_ALIGNMENT.md`
5. `docs/API_CONTRACT.md`
6. `submission_artifacts/evaluation/evaluation_metrics.md`
7. `submission_artifacts/stability/stability_report.md`
8. `submission_artifacts/agent_decision_cases/README.md`
9. `submission_artifacts/baseline_comparison/baseline_comparison.md`
10. `submission_artifacts/cost_model/cost_model.md`
11. `submission_artifacts/recovery_effectiveness/recovery_effectiveness_report.md`
12. `submission_artifacts/llm_impact/llm_impact_report.md`
13. `docs/CASE_STUDIES.md`
