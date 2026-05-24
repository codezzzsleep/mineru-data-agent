# Live LLM 复跑手册

本文用于重新运行 DeepSeek/ModelScope 的真实 LLM 证据。它刻意与离线 scripted decision cases 分开：只有存在 provider key 且代码实际调用 provider 的结果，才算 live LLM 证据。

## 范围

- 官方单案例 live tool-calling CLI：`data-agent agent-run`
- 批量 tool-calling 证据脚本：`scripts/run_agent_live_cases.py`
- LLM 预调度/复核矩阵脚本：`scripts/run_live_llm_matrix.py`
- Provider：`modelscope` 或 `deepseek`

Live tool-calling Agent 只通过 CLI 暴露。HTTP API 保持为稳定 deterministic/LLM-preplan 路径，不暴露 `/v1/agent/parse`。

## 官方 CLI：`data-agent agent-run`

```powershell
$env:MODELSCOPE_API_KEY="<your-modelscope-token>"
$env:MODELSCOPE_BASE_URL="https://api-inference.modelscope.cn/v1"
$env:MODELSCOPE_MODEL="Qwen/Qwen3-235B-A22B-Instruct-2507"

.\.venv\Scripts\data-agent.exe agent-run `
  --provider modelscope `
  --model $env:MODELSCOPE_MODEL `
  --input examples/cases/case_1_financial_report.html `
  --out runs/agent_live `
  --task "识别 2026Q1 的营业收入和利润总额，验证合计行是否一致"
```

每次运行写出 `result.json`、`live_agent_trace.json` 和 `live_agent_summary.md`。`result.json` 使用以下证据字段：`selected_skill`、`skill_history`、`answer_validation`、`tool_call_completed`、`answer_quality_pass`、`quality_review` 和 `tool_sequence`。一个成功的 skill-gated run 应显示：LLM 先通过 `select_skill` 选择 skill，再解析文档，随后用 `validate_answer` 校验完全一致的最终答案，最后才调用 `finalize`。

## 批量 Tool-Calling 证据

```powershell
.\.venv\Scripts\python.exe scripts\run_agent_live_cases.py `
  --provider modelscope `
  --model $env:MODELSCOPE_MODEL `
  --reset-output `
  --min-completed-rate 0
```

该脚本更新 `submission_artifacts/agent_live_cases/agent_live_report.json` 和 `.md`。新报告使用 `evidence_generation=skill_guided_validation_gate`，并包含 `tool_validated_cases`、`selected_skill` 和 `answer_validation` 字段。失败、quota 受限和答案质量存疑的案例会保留，不会隐藏。若使用 `--skip-existing`，没有 `answer_validation_ok` 的旧版完成行不会被跳过，会重新运行以生成 skill-gated 证据。

## LLM 预调度/复核矩阵

矩阵脚本使用本地 HTML fixture，隔离测试 LLM preplanning 和 post-parse review，不依赖 MinerU CLI/GPU 环境。覆盖财报复核、低质量 OCR 复核、合同条款复核、流程复核和跨页财报复核。

- Manifest：`examples/llm_live_cases.json`
- Runner：`scripts/run_live_llm_matrix.py`
- 默认输出：`submission_artifacts/llm_live_matrix/`
- 默认临时运行目录：`runs/live_llm_matrix/`

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

## 预期输出

成功的 live run 会写出：

- `submission_artifacts/llm_live_matrix/llm_live_matrix_report.json`
- `submission_artifacts/llm_live_matrix/llm_live_matrix_report.md`
- 每个 case 一个目录，包含 `result.json`、`trace.json`、`summary.md`、retrieval artifact 和 case README

报告记录 provider、model、case status、quality score、LLM 调用次数、token 用量、applied controls、risk findings 和 recovery suggestions。API key 只从环境变量读取，并会从 artifact 中脱敏。

## 缺少 Key 时的行为

默认情况下，provider key 缺失会导致脚本非零退出：

```powershell
.\.venv\Scripts\python.exe scripts\run_live_llm_matrix.py --provider modelscope
```

CI 或文档检查可显式写出 non-evidence skip report：

```powershell
.\.venv\Scripts\python.exe scripts\run_live_llm_matrix.py `
  --provider modelscope `
  --output-dir runs\llm_live_matrix_skip `
  --write-skip-report
```

该 skip report 会写明 `live_provider_evidence=false`，不能引用为 live provider run。

## 常用窄范围复跑

只跑一个 case：

```powershell
.\.venv\Scripts\python.exe scripts\run_live_llm_matrix.py `
  --provider modelscope `
  --case low_quality_ocr_review
```

只跑前两个 case：

```powershell
.\.venv\Scripts\python.exe scripts\run_live_llm_matrix.py `
  --provider deepseek `
  --limit 2
```

某个 provider 调用失败后继续跑后续 case：

```powershell
.\.venv\Scripts\python.exe scripts\run_live_llm_matrix.py `
  --provider modelscope `
  --continue-on-error
```

## 边界

该矩阵是 live LLM 复跑工具，不证明原始 OCR 能力提升。默认 case 使用本地 HTML 输入，测试的是 LLM 规划、schema 建议、解析后风险复核和受限 recovery suggestion。更大的 PDF、MinerU CLI/GPU 和公网负载 benchmark 属于单独证据轨道。
