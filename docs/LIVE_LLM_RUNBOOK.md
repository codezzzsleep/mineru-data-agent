# Live LLM Matrix Runbook

This runbook is for rerunning multiple end-to-end LLM cases with a real DeepSeek or ModelScope key. It is intentionally separate from the offline scripted decision cases: a matrix result counts as live LLM evidence only when the provider key is present and the script actually calls the provider.

## Scope

- Manifest: `examples/llm_live_cases.json`
- Runner: `scripts/run_live_llm_matrix.py`
- Default output: `submission_artifacts/llm_live_matrix/`
- Default run scratch: `runs/live_llm_matrix/`
- Providers: `modelscope` or `deepseek`

The default manifest uses local HTML fixtures so the run isolates LLM preplanning and post-parse review without needing a MinerU CLI/GPU environment. It covers financial review, low-quality OCR review, contract clause review, workflow review, and cross-page financial review.

## ModelScope

```powershell
$env:MODELSCOPE_API_KEY="<your-modelscope-token>"
$env:MODELSCOPE_BASE_URL="https://api-inference.modelscope.cn/v1"
$env:MODELSCOPE_MODEL="deepseek-ai/DeepSeek-V4-Flash"

.\.venv\Scripts\python.exe scripts\run_live_llm_matrix.py `
  --provider modelscope `
  --model $env:MODELSCOPE_MODEL
```

## DeepSeek

```powershell
$env:DEEPSEEK_API_KEY="<your-deepseek-key>"
$env:DEEPSEEK_BASE_URL="https://api.deepseek.com"
$env:DEEPSEEK_MODEL="deepseek-v4-flash"

.\.venv\Scripts\python.exe scripts\run_live_llm_matrix.py `
  --provider deepseek `
  --model $env:DEEPSEEK_MODEL
```

## Expected Outputs

Successful live runs write:

- `submission_artifacts/llm_live_matrix/llm_live_matrix_report.json`
- `submission_artifacts/llm_live_matrix/llm_live_matrix_report.md`
- one case directory per manifest case, each containing `result.json`, `trace.json`, `summary.md`, retrieval artifacts, and a case README

The report records provider, model, case status, quality score, LLM call count, token usage, applied controls, risk findings, and recovery suggestions. API keys are read only from environment variables and are scrubbed from artifacts.

## Missing-Key Behavior

By default the script exits non-zero when the provider key is missing:

```powershell
.\.venv\Scripts\python.exe scripts\run_live_llm_matrix.py --provider modelscope
```

For CI or documentation checks, a non-evidence skip report can be written explicitly:

```powershell
.\.venv\Scripts\python.exe scripts\run_live_llm_matrix.py `
  --provider modelscope `
  --output-dir runs\llm_live_matrix_skip `
  --write-skip-report
```

That skip report says `live_provider_evidence=false`; it must not be cited as a live provider run.

## Useful Narrow Runs

Run one case:

```powershell
.\.venv\Scripts\python.exe scripts\run_live_llm_matrix.py `
  --provider modelscope `
  --case low_quality_ocr_review
```

Run the first two cases:

```powershell
.\.venv\Scripts\python.exe scripts\run_live_llm_matrix.py `
  --provider deepseek `
  --limit 2
```

Continue through later cases even if one provider call fails:

```powershell
.\.venv\Scripts\python.exe scripts\run_live_llm_matrix.py `
  --provider modelscope `
  --continue-on-error
```

## Boundary

This matrix is a live LLM rerun harness, not proof of raw OCR improvement. The default cases use local HTML inputs, so they test LLM planning, schema suggestions, post-parse risk review, and bounded recovery suggestions. Larger PDF, MinerU CLI/GPU, and public network load benchmarks remain separate evidence tracks.
