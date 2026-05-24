# Evaluation Guide

This is the shortest CLI-first path for reviewing the submission.

## 1. What This Project Does

MinerU Data Agent is submitted as a command-line tool. It takes PDF, HTML, DOCX,
PPTX, or image-like document inputs; runs MinerU or a native extractor; builds
structured JSON; writes a trace log; checks quality risks; exports retrieval
chunks; and records recovery attempts.

The Agent layer adds task planning, schema selection, field evidence, quality
checks, recovery decisions, local recovery memory, CLI batch execution, and
optional LLM preplanning/post-parse review. A separate `data-agent agent-run`
command provides live provider tool-calling evidence.

## 2. Three-Step CLI Reproduction

```bash
pip install -e ".[dev]"
data-agent run --input examples/cases/case_1_financial_report.html --out runs/review_cli --task "抽取财报关键字段并检查合计行" --profile auto
data-agent batch --manifest examples/batch_manifest.json --out runs/review_batch
```

The first command should write `result.json`, `trace.json`, `summary.md`, and a
`retrieval/` directory. The second command should write `batch_report.json` and
per-task run directories.

For PDF review in a CPU-only environment:

```bash
data-agent run --runner agent-api --input demo.pdf --out runs/review_pdf_api --task "解析 PDF 并输出结构化结果和质量日志"
```

For page-level provenance and full MinerU artifacts, use a local MinerU CLI
environment:

```bash
data-agent run --runner cli --input demo.pdf --out runs/review_pdf_cli --task "解析财报 PDF，抽取表格、关键数字并检查合计行" --backend pipeline --method auto
```

## 3. Live LLM Reproduction

Live tool-calling evidence requires a real provider key:

```bash
data-agent agent-run \
  --provider modelscope \
  --input examples/cases/case_2_low_quality_ocr.html \
  --out runs/agent_live \
  --task "发现乱码后先清理，再抽取设备 B-17 的异常温度"
```

Batch rerun harness:

```bash
python scripts/run_agent_live_cases.py --provider modelscope --min-completed-rate 0
```

Missing provider keys do not generate fake evidence.

## 4. Scoring Map

| Official Dimension | What To Check First | File |
| --- | --- | --- |
| Complex document understanding and structured processing | 17-case labeled metrics, field precision/recall/F1, public PDF cases, PDF CLI cases | `submission_artifacts/evaluation/evaluation_metrics.md`, `submission_artifacts/public_real_cases/`, `submission_artifacts/mineru_cases/` |
| Hard scenario and technical value | Cross-page financial fixture, OCR-noise contract, PDF recovery, controlled failure/recovery cases, long-document chunking and risk notes | `submission_artifacts/challenge_cases/`, `submission_artifacts/recovery_cases/`, `submission_artifacts/failure_recovery_cases/README.md`, `submission_artifacts/long_document_chunks/`, `submission_artifacts/long_document_risk/long_document_risk_report.md` |
| Agent planning and automatic execution | CLI action plan fields, runtime recovery plan, local recovery memory, live tool-calling traces, offline scripted regression boundaries | `docs/CLI_CONTRACT.md`, `submission_artifacts/memory_cases/`, `submission_artifacts/agent_live_cases/agent_live_report.md`, `submission_artifacts/agent_decision_cases/README.md`, `submission_artifacts/recovery_effectiveness/recovery_effectiveness_report.md` |
| Stability and reproducibility | CLI smoke in CI, trace aggregation, coverage, code/test summary, submission zip inventory | `.github/workflows/tests.yml`, `submission_artifacts/stability/stability_report.md`, `submission_artifacts/coverage/coverage_report.md`, `submission_artifacts/code_quality/code_quality_report.md`, `tests/test_submission_zip_inventory.py` |
| Open-source and ecosystem value | Repo structure, CLI contract, license, contribution guide, originality notes, artifact index | `README.md`, `docs/CLI_CONTRACT.md`, `LICENSE`, `CONTRIBUTING.md`, `docs/ORIGINALITY_AND_COMPLIANCE.md`, `submission_artifacts/ARTIFACTS_INDEX.md` |

## 5. Key Numbers

| Metric | Current Saved Result | Source |
| --- | --- | --- |
| Labeled cases | 17 | `submission_artifacts/evaluation/evaluation_metrics.md` |
| Expected fields | 45 | `submission_artifacts/evaluation/evaluation_metrics.md` |
| Text evidence checks | 22 | `submission_artifacts/evaluation/evaluation_metrics.md` |
| Numeric evidence checks | 11 | `submission_artifacts/evaluation/evaluation_metrics.md` |
| Table evidence checks | 6 | `submission_artifacts/evaluation/evaluation_metrics.md` |
| Live tool-calling Agent | 8 attempted, 4 tool-call completed, 2 answer-quality pass | `submission_artifacts/agent_live_cases/agent_live_report.md` |
| Long document chunking | NIST AI RMF 48 pages, 3 chunks, 3/3 success, 58 retrieval chunks | `submission_artifacts/long_document_chunks/public_nist_ai_rmf_full_chunked/long_document_chunk_report.md` |
| LLM preplan/review usage | 2 calls, 4309 tokens in saved ModelScope case | `submission_artifacts/llm_cost/llm_cost_report.md` |
| Agent decision regression cases | 5 offline local cases with subtask graph, selected tools, quality replan, and scripted decision hooks | `submission_artifacts/agent_decision_cases/README.md` |
| Recovery aggregate | Saved-result recovery records, executed recovery count, selected non-initial count, issue-code distribution | `submission_artifacts/recovery_effectiveness/recovery_effectiveness_report.md` |
| Controlled failure/recovery cases | Fault-injection cases for text cleanup, OCR retry success/failure, strict provenance failure, and numeric mismatch | `submission_artifacts/failure_recovery_cases/README.md` |
| Retrieval validation | Chunk schema errors, duplicate rate, empty chunks, and lightweight lexical top-3 query smoke | `submission_artifacts/retrieval_validation/retrieval_validation_report.md` |
| Coverage | Local pytest line coverage for `src/mineru_data_agent` | `submission_artifacts/coverage/coverage_report.md` |
| Code/test scale | Python files, test functions, GitHub Actions workflow present | `submission_artifacts/code_quality/code_quality_report.md` |

## 6. Artifact Navigation

Use `submission_artifacts/ARTIFACTS_INDEX.md` as the directory map. It lists each
artifact family, counts result/trace files, and links the main reports.

## 7. Current Limits

The saved submission does not include a public internet load test, a GPU
long-document benchmark, or an OCR character/table-cell benchmark. The Agent
decision case pack is offline regression evidence with a scripted decision
client; it does not count as live LLM evidence. Saved live-provider evidence is
split between one ModelScope LLM preplan/review case in
`submission_artifacts/llm_cases/` and the `submission_artifacts/agent_live_cases/`
tool-calling report: 8 attempted runs, 4 finalize/tool-call completions, and 2
manually reviewed answer-quality pass examples. The optional HTTP API and Docker
files are secondary integration materials, not the primary review surface.
