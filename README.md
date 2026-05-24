# MinerU Data Agent

CLI-first MinerU document Data Agent for MDIC 2026 Track 2. The stable review
surface is the `data-agent` command, not an HTTP service.

The project uses MinerU for PDF/image parsing, native extractors for
HTML/DOCX/PPTX, and a deterministic Agent layer for task routing, structured
extraction, validation, recovery, trace logging, and retrieval export. A separate
`data-agent agent-run` command provides a real OpenAI-compatible tool-calling
LLM Agent path when a provider key is available.

## What To Review First

1. **CLI contract**: `docs/CLI_CONTRACT.md`
2. **Evaluation guide**: `docs/EVALUATION_GUIDE.md`
3. **Artifact index**: `submission_artifacts/ARTIFACTS_INDEX.md`
4. **Live tool-calling evidence**: `submission_artifacts/agent_live_cases/agent_live_report.md`
5. **Technical report**: `docs/TECHNICAL_REPORT.md`

## Key Capabilities

- `data-agent run`: one document in, structured JSON/trace/summary/retrieval chunks out.
- `data-agent batch`: manifest-driven batch execution; one failed task does not stop the batch.
- `data-agent agent-run`: live LLM tool-calling loop for dynamic tool choice and evidence traces.
- PDF paths through MinerU online Agent API or local MinerU CLI.
- Native HTML/DOCX/PPTX parsing for CPU-friendly review and regression tests.
- Quality checks for empty extraction, text noise, page provenance, financial totals, weak structure, and profile-specific risks.
- Recovery loop: text cleanup, OCR retry, and optional CLI fallback when page provenance is missing.
- Local SQLite recovery memory for repeated runs under the same output root.
- Retrieval export as JSONL for downstream RAG/search systems.

Detailed feature list: `docs/FEATURES.md`.

## Install

Base CLI install:

```bash
pip install -e .
```

Developer/test install:

```bash
pip install -e ".[dev]"
```

Local MinerU pipeline install, when the environment does not already provide
MinerU CLI:

```bash
pip install -e ".[mineru]"
```

Optional HTTP wrapper dependencies, only if you want to run the secondary API:

```bash
pip install -e ".[api]"
```

## Quick Start: CLI

HTML/Office smoke path, no MinerU required:

```bash
data-agent run \
  --input examples/cases/case_1_financial_report.html \
  --out runs/cli_demo \
  --task "抽取财报关键字段并检查合计行" \
  --profile auto
```

PDF through MinerU online Agent API, useful for CPU-only review:

```bash
data-agent run \
  --runner agent-api \
  --input demo.pdf \
  --out runs/pdf_api \
  --task "解析 PDF，输出结构化结果、质量日志和 retrieval chunks" \
  --method auto
```

PDF through local MinerU CLI, preferred when page-level provenance and MinerU
middle/layout/model artifacts are required:

```bash
data-agent run \
  --runner cli \
  --input demo.pdf \
  --out runs/pdf_cli \
  --task "解析财报 PDF，抽取表格、关键数字并检查合计行" \
  --backend pipeline \
  --method auto
```

Batch:

```bash
data-agent batch \
  --manifest examples/batch_manifest.json \
  --out runs/batch_demo
```

Live tool-calling Agent, requires a real provider key:

```bash
data-agent agent-run \
  --provider modelscope \
  --input examples/cases/case_2_low_quality_ocr.html \
  --out runs/agent_live \
  --task "发现乱码后先清理，再抽取设备 B-17 的异常温度"
```

Provider keys are read from environment variables only:

```bash
export MODELSCOPE_API_KEY="<your-modelscope-token>"
export MODELSCOPE_BASE_URL="https://api-inference.modelscope.cn/v1"
export MODELSCOPE_MODEL="Qwen/Qwen3-235B-A22B-Instruct-2507"
```

PowerShell:

```powershell
$env:MODELSCOPE_API_KEY="<your-modelscope-token>"
$env:MODELSCOPE_BASE_URL="https://api-inference.modelscope.cn/v1"
$env:MODELSCOPE_MODEL="Qwen/Qwen3-235B-A22B-Instruct-2507"
```

## Output Contract

Each `data-agent run` produces a run directory with:

- `result.json`: structured result and execution control fields.
- `trace.json`: authoritative step/tool audit log.
- `summary.md`: human-readable summary.
- `retrieval/retrieval_chunks.jsonl`: RAG/search chunks.
- `retrieval/retrieval_manifest.json`: retrieval export metadata.

Important `result.json` fields:

- `schema_version`
- `execution_control`
- `extracted`
- `quality`
- `recovery_decision`
- `retrieval_export`
- `trace_path`
- `summary_path`

The full CLI contract is in `docs/CLI_CONTRACT.md`.

## Saved Evidence

The submission package intentionally separates deterministic evidence, offline
regression fixtures, and live-provider evidence.

| Evidence | Current saved result |
| --- | --- |
| Labeled evaluation | 17 cases, 45 expected fields, field/evidence/quality/provenance checks in `submission_artifacts/evaluation/` |
| MinerU CLI PDFs | 4 file-level local CLI runs with page provenance and MinerU intermediate artifacts in `submission_artifacts/mineru_cases/` |
| Public PDFs | IRS W-4, NIST AI RMF, Microsoft annual report exhibit, CDC VIS in `submission_artifacts/public_real_cases/` |
| Long document chunking | NIST AI RMF 48 pages split into 3 online Agent API chunks in `submission_artifacts/long_document_chunks/` |
| Failure/recovery | Controlled negative and recovery cases in `submission_artifacts/failure_recovery_cases/` |
| Retrieval validation | Schema, duplicate, density, and lexical retrieval smoke checks in `submission_artifacts/retrieval_validation/` |
| Live tool-calling Agent | 8 attempted ModelScope Qwen3 runs; 4 reached finalize/tool-call completion; 2 manually reviewed answer-quality pass examples in `submission_artifacts/agent_live_cases/` |

Live evidence semantics:

- `tool_call_completed=true` means a real provider call consumed tokens and
  reached the `finalize` tool.
- `answer_quality_pass=true` is a separate manual review field.
- Only the 2 saved `answer_quality_pass=true` cases should be cited as semantic
  live-agent successes.
- Offline `agent_decision_cases` are scripted regression fixtures; their token
  counts are synthetic and are not live LLM evidence.

## Current Boundaries

- This is a CLI-first submission. No long-running public API endpoint is claimed.
- The optional FastAPI wrapper is secondary and exists for local integration
  experiments only.
- Saved evaluation labels include project-authored fixtures and lightweight
  public-PDF labels; they are not a third-party OCR benchmark.
- The long-document saved evidence demonstrates chunk orchestration, not a GPU
  throughput benchmark.
- Cost reports use replaceable May 2026 scenario assumptions and should be
  updated with current provider prices before production planning.

## Optional HTTP Wrapper

The repository still contains an optional FastAPI wrapper for local integration
testing. It is not the primary review interface. Install it with:

```bash
pip install -e ".[api]"
uvicorn mineru_data_agent.api:app --host 127.0.0.1 --port 8080
```

Contract: `docs/API_CONTRACT.md`. Deployment notes:
`docs/DEPLOYMENT_AND_API.md`.

## Development

```bash
pip install -e ".[dev]"
pytest -q
python -m compileall -q src scripts tests
```

Build the submission zip:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\make_submission_zip.ps1 -Output dist\mineru-data-agent-submission.zip
```

The zip inventory test checks that CLI/live-agent files and evidence are present
and that local machine paths do not leak into text artifacts.

## Repository

Open-source materials include `LICENSE`, `CONTRIBUTING.md`,
`CODE_OF_CONDUCT.md`, `SECURITY.md`, `ROADMAP.md`, issue templates, tests,
scripts, docs, and saved artifacts. Public repository:
https://github.com/codezzzsleep/mineru-data-agent.
