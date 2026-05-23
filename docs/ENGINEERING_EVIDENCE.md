# Engineering Evidence Matrix

This matrix responds directly to high-probability review deductions for Track 2.

| Risk | Current Evidence | Remaining Boundary |
| --- | --- | --- |
| Task planning explainability is weak | `result.json.execution_control` records requested/initial/resolved controls, applied/ignored LLM recommendations, and planning rationale. `summary.md` now includes planning rationale for new runs. | Older saved artifacts may not include the newest `planning_rationale`; rerun important demos before final live presentation. |
| Recovery chain is incomplete | `recovery_decision.attempts` records initial, text cleanup, OCR retry, and CLI fallback attempts. Evidence includes `case_pdf_llm_api_to_cli_fallback` and `case_7_noisy_contract_scan`. | API-to-CLI fallback evidence currently uses cached CLI artifact in this environment; live full-chain evidence needs a real MinerU CLI executable. |
| Cost/speed/quality tradeoff is not quantified | `submission_artifacts/stability/stability_report.md` summarizes 17 saved cases, tool calls, tool elapsed seconds, recovery count, quality status, and provenance distribution. `submission_artifacts/api_load_smoke/api_load_smoke_report.md` adds an 8-request, concurrency-4 local FastAPI smoke result. `submission_artifacts/evaluation/evaluation_metrics.md` summarizes labeled accuracy gates. | The API load smoke is local and in-process; it is not an external network/GPU/cloud-cost load test. |
| Complex scenarios are not covered | Evidence covers public real PDFs, challenge fixtures, local MinerU CLI PDFs, Office files, API smoke, recovery, and LLM-enabled analysis. | More real scanned documents and figure-heavy engineering drawings would still strengthen the submission. |
| Output schema is not fixed | `docs/API_CONTRACT.md` defines stable top-level response fields. `result.json` uses consistent sections/tables/key-values/numeric facts/semantic signals/quality/recovery/retrieval/trace fields. | Extracted domain fields remain document-dependent by design; downstream consumers should use `key_value_map`, evidence checks, and retrieval chunks. |
| Missing confidence/source evidence | New runs write `extracted.field_evidence` and `field_evidence_map` with key, value, confidence proxy, evidence text, and line/page/block provenance. Quality issues include evidence payloads; retrieval chunks include page/document provenance; numeric/table evaluation checks exact evidence fragments. | Confidence is a deterministic evidence proxy, not a calibrated ML confidence score. Bbox is only preserved when the upstream parser provides it; online API path can still lack page-level provenance. |
| Logs are not verifiable | `trace.json` records input, steps, tool calls, timing, status, error summaries, result path, and summary path. Failure tests verify failed traces are written. | Some older collected artifacts infer completion from completed steps because older trace writers did not set top-level `status`. |
| Reproducibility material is incomplete | `README.md`, `docs/DEPLOYMENT_AND_API.md`, `docs/API_CONTRACT.md`, `pyproject.toml`, tests, and artifact scripts document install, run, API, testing, logs, and evidence generation. | No Docker image is included; HeyWhale/MinerU image setup is documented rather than containerized here. |
| API is not evaluation-friendly | `docs/API_CONTRACT.md` defines request fields, response schema, async `/v1/jobs`, polling `/v1/jobs/{job_id}`, and structured error codes. API persists trace/result/summary paths after response. | Public auth/rate limiting is expected at deployment gateway; this repo does not ship a permanent hosted endpoint. |
| Technical report is too feature-oriented | `docs/TECHNICAL_REPORT.md`, `docs/CASE_STUDIES.md`, `docs/EVALUATION_STRATEGY.md`, and this matrix point to evidence artifacts, failures, boundaries, and metrics. | A short PPT or demo video would improve reviewer scanning speed. |
| Open-source quality is weak | MIT license, README, `CONTRIBUTING.md`, issue templates, tests, GitHub Actions, docs, scripts, examples, and submission artifacts are included. | A longer-term community roadmap is not included because this is a competition submission repo. |

## Key Artifact Pointers

- Evaluation metrics: `submission_artifacts/evaluation/evaluation_metrics.md`
- Stability report: `submission_artifacts/stability/stability_report.md`
- API load smoke: `submission_artifacts/api_load_smoke/api_load_smoke_report.md`
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
6. `docs/CASE_STUDIES.md`
