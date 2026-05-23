# 部署与 API 说明

## 1. 环境要求

轻量演示环境：

- Python 3.10 到 3.13
- CPU 资源即可
- 可访问 `https://mineru.net`

完整 MinerU artifact 环境：

- HeyWhale MinerU 镜像或本地安装 MinerU CLI
- 推荐 GPU 资源
- 可选设置 `MINERU_EXECUTABLE` 和 `MINERU_MODEL_SOURCE`

## 2. 安装

```bash
pip install -e ".[dev]"
```

如果需要本地 MinerU pipeline：

```bash
pip install -e ".[mineru]"
```

## 3. 单文件命令行

在线 API 后端：

```bash
data-agent run \
  --runner agent-api \
  --input demo.pdf \
  --out runs \
  --task "解析文档并输出结构化结果、质量日志和知识库 chunks" \
  --profile auto
```

本地 MinerU CLI 后端：

```bash
data-agent run \
  --runner cli \
  --input demo.pdf \
  --out runs \
  --task "解析财报 PDF，抽取表格、关键数字并检查合计行" \
  --backend pipeline \
  --method auto
```

在线 API 缺少页级 provenance 时，系统会在检测到本地 `mineru` 命令、`MINERU_EXECUTABLE` 或显式 CLI 路径后尝试本地 CLI fallback。可通过 `--fallback-mineru-executable` 指定 fallback 使用的 MinerU 可执行文件；如果当前环境没有可用 CLI，系统会保留在线 API 结果和 `no_page_provenance` 警告，不会盲目产生失败恢复记录。如只想保留在线 API 结果，也可关闭该恢复路径：

```bash
data-agent run \
  --runner agent-api \
  --fallback-mineru-executable /path/to/mineru \
  --input demo.pdf \
  --out runs \
  --task "先用在线 API 解析，缺页级 provenance 时自动 fallback 到 CLI"
```

```bash
data-agent run \
  --runner agent-api \
  --no-cli-fallback-on-no-page-provenance \
  --input demo.pdf \
  --out runs \
  --task "只验证在线 API 轻量路径"
```

## 4. 批处理命令行

批处理用于模拟生产环境中的多任务调度。单个任务失败不会中断整批，最终会生成 `batch_report.json`。

```bash
data-agent batch \
  --manifest examples/batch_manifest.json \
  --out runs/batch_html \
  --runner agent-api
```

如果批处理里只包含 HTML，可使用默认 runner，因为 HTML 会走本地轻量解析：

```bash
data-agent batch \
  --manifest examples/batch_manifest.json \
  --out runs/batch_html
```

生成提交材料中的 5 个案例 artifact：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_submission_cases.ps1 -Python .\.venv\Scripts\python.exe
```

生成结果位于 `submission_artifacts/cases/`，包含 `artifact_index.json`、`batch_report.json` 和每个案例的 `result.json`、`trace.json`、`summary.md`、`retrieval/`。

收集真实 MinerU CLI 案例 artifact：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\collect_mineru_case.ps1 -RunDir runs\mineru_cli_refresh\4568109b3cc5
```

当前结果位于 `submission_artifacts/mineru_cases/`。该目录用于证明本地 `mineru-cli` 后端、页级 provenance、MinerU 中间文件和 retrieval 导出已经跑通。

生成官方公开真实文档证据包：

```powershell
.\.venv\Scripts\python.exe .\scripts\run_public_real_cases.py
```

当前结果位于 `submission_artifacts/public_real_cases/`，覆盖 IRS W-4、NIST AI RMF 1.0、Microsoft 2024 Annual Report SEC PDF exhibit 和 CDC VIS 使用说明。每个案例包含官方输入副本、source metadata、human labels、trace、result、summary 和 retrieval 导出；NIST 与 Microsoft 长文档按在线 Agent API 限制只跑前 20 页，并在 metadata 中写明。

## 5. API 服务

启动：

```bash
uvicorn mineru_data_agent.api:app --host 0.0.0.0 --port 8080
```

稳定接口、参数、返回 schema 和错误码见 `docs/API_CONTRACT.md`。该文档是评审脚本优先参考的 API 合约。

健康检查：

```bash
curl http://127.0.0.1:8080/health
```

本提交包保存了本地 API 冒烟测试证据，见 `submission_artifacts/api_smoke/`。该证据覆盖 `/health`、一次 HTML 文件上传解析和一次 PDF 文件上传解析，返回的 `trace_path`、`summary_path` 和 retrieval 输出均已落盘。另保存 1 个 CPU 环境下 `--runner agent-api` PDF 复跑证据，见 `submission_artifacts/agent_api_cases/`。

当前提交提供本地可启动 API 与本地烟测证据，尚未提供长期公网服务地址。评审若需要联网调用，可按本节命令在 HeyWhale 或自有服务器启动服务；公开部署属于加分项，不是当前提交包已完成的事实。

解析接口：

```bash
curl -X POST http://127.0.0.1:8080/v1/parse \
  -F "file=@demo.pdf" \
  -F "task=解析财报 PDF，抽取表格、关键数字并检查合计行" \
  -F "profile=financial_report" \
  -F "runner=agent-api" \
  -F "api_max_retries=2"
```

API 输出默认持久化到 `runs/api`。生产或评审环境可用环境变量指定：

```bash
export MINERU_DATA_AGENT_OUTPUT_DIR="/home/mw/project/mineru-data-agent/runs/api"
```

也可以在请求中传入：

```bash
  -F "output_root=/home/mw/project/mineru-data-agent/runs/api"
```

公开部署时建议增加两个保护配置：

```bash
export MINERU_DATA_AGENT_ALLOWED_OUTPUT_BASE="/home/mw/project/mineru-data-agent"
export MINERU_DATA_AGENT_MAX_UPLOAD_MB="200"
```

如果请求传入的 `output_root` 不在 `MINERU_DATA_AGENT_ALLOWED_OUTPUT_BASE` 内，接口会返回 400；如果上传文件超过限制，会返回 413。`runner` 只允许 `cli` 或 `agent-api`，`llm` 只允许 `none`、`deepseek` 或 `modelscope`，非法值会返回结构化错误。

开启 DeepSeek 大模型增强：

```bash
export DEEPSEEK_API_KEY="<your-deepseek-key>"
export DEEPSEEK_BASE_URL="https://api.deepseek.com"
export DEEPSEEK_MODEL="deepseek-v4-flash"
```

或使用 ModelScope 推理入口：

```bash
export MODELSCOPE_API_KEY="<your-modelscope-token>"
export MODELSCOPE_BASE_URL="https://api-inference.modelscope.cn/v1"
export MODELSCOPE_MODEL="deepseek-ai/DeepSeek-V4-Flash"
```

```bash
curl -X POST http://127.0.0.1:8080/v1/parse \
  -F "file=@demo.pdf" \
  -F "task=解析财报 PDF，抽取表格、关键数字并检查合计行" \
  -F "profile=financial_report" \
  -F "runner=agent-api" \
  -F "llm=modelscope" \
  -F "llm_model=deepseek-ai/DeepSeek-V4-Flash"
```

```bash
curl -X POST http://127.0.0.1:8080/v1/parse \
  -F "file=@demo.pdf" \
  -F "task=解析财报 PDF，抽取表格、关键数字并检查合计行" \
  -F "profile=financial_report" \
  -F "runner=agent-api" \
  -F "llm=deepseek" \
  -F "llm_model=deepseek-v4-flash"
```

本提交包保存了一次实际启用 ModelScope DeepSeek-V4-Flash 的运行证据，见 `submission_artifacts/llm_cases/`。该证据的 `trace.json` 记录了 `modelscope-llm completed`，`result.json` 中 `llm_analysis.enabled=true`。当前代码还会在解析前新增 `llm_pre_execution_planning` 步骤：LLM 建议 profile、runner、backend、method、语言、目标 schema 和恢复策略，系统把白名单内且未被显式锁定的建议写入 `execution_control.applied` 并用于本次解析。API key 只通过环境变量传入，不进入输出文件。

API 同样支持 provenance fallback 参数：`cli_fallback_on_no_page_provenance=true` 默认开启，`fallback_mineru_executable` 可指定本地 MinerU CLI 路径。实际 fallback runner 只有在显式路径、`MINERU_EXECUTABLE` 或系统 `mineru` 命令可用时才会创建。当前提交包的 `submission_artifacts/recovery_cases/case_pdf_llm_api_to_cli_fallback/` 已保存一个真实 PDF 的恢复演练：在线 API 首次解析后触发 `no_page_provenance`，随后选择 `cli_fallback`，最终 `recovery_decision.executed=true`。该案例在无真实 key/CLI 的当前环境下使用离线确定性预调度器和缓存 CLI artifact 回放，文档和 trace 已标注边界。

## 6. 返回结果

核心字段：

- `run_id`：本次运行编号
- `plan`：Agent 任务计划
- `execution_control`：解析前调度控制记录，包含 requested、initial、LLM recommendation、applied、ignored 和 resolved 参数
- `extracted`：章节、表格、键值对、键值字典、数字事实、日期/建议/异常信号等结构化视图
- `quality`：质量评分与风险列表
- `recovery_decision`：根据质量报告、文件类型和 profile 给出的接受、复核、重试、CLI fallback 或人工处理建议；包含 `attempts`、`selected_attempt`、`executed` 和 `initial_issue_codes`。恢复尝试失败时会记录 failed attempt，并保留初始可用结果继续输出。
- `retrieval_export`：检索 chunks、manifest 和质量报告路径
- `llm_analysis`：可选大模型解析前调度、解析后复核、目标 schema、复核重点、恢复建议和服务返回的 reasoning 内容
- `artifacts`：MinerU 原始输出或在线 API 输出
- `trace_path`：可追溯执行日志
- `summary_path`：人工可读摘要

若在线 API 或轻量 Markdown 路径无法提供页级信息，`quality.issues` 会出现 `no_page_provenance`，提示评审该结果只有块级或文档级溯源。HTML fixture 会记录 `document_level_provenance` 信息项，表示它只有文档级来源，不冒充 PDF 页级 provenance。需要完整页级 artifact 时，应使用本地 MinerU CLI 后端。

每次运行目录：

```text
runs/api/<run_id>/
  result.json
  trace.json
  summary.md
  retrieval/
    retrieval_chunks.jsonl
    retrieval_manifest.json
    retrieval_quality.json
  mineru/
```

## 7. 日志查看

`trace.json` 包含：

- 任务输入
- 执行步骤
- MinerU 工具调用
- DeepSeek/ModelScope 工具调用状态，不包含 API key
- 在线 API 重试事件
- 自动恢复尝试，例如 `auto_recovery_text_cleanup`、`auto_recovery_ocr_retry` 或 `auto_recovery_cli_fallback`
- 耗时、状态和错误摘要

日志脱敏策略：

- DeepSeek/ModelScope API key 只通过环境变量或请求参数进入运行时，不写入输出文件。
- LLM 调用失败摘要会过滤真实 key、Bearer token 和 `api_key=` 参数。
- MinerU 在线 Agent API 的重试事件、异常文本和保存的事件 JSON 会过滤 `token=`、`access_token=`、`signature=`、`X-Amz-*` 等签名字段。
- 提交材料收集脚本会对本机路径做 `<PROJECT_ROOT>`、`<USER_HOME>`、`<MINERU_ROOT>` 一类占位替换，减少本地环境泄露。

如果解析失败，系统仍会写出失败态 `trace.json`，其中 `status=failed`，并记录失败步骤和错误摘要。通过 API 调用时，失败响应的 `detail` 也会返回 `run_id`、`output_dir`、`trace_path`、`result_path` 和 `summary_path`，方便评审脚本直接定位失败证据。

`batch_report.json` 包含：

- 批处理总任务数
- 成功/失败数量
- 每个任务的 run id、输出路径、质量评分和错误信息

## 8. 带标注评测

标注文件位于 `examples/evaluation/labels.json`，覆盖 HTML、PDF/MinerU CLI、Office、recovery、挑战案例和官方公开真实 PDF 案例的关键字段、文本证据、profile、结构门槛、质量门槛、provenance 门槛和 recovery 门槛。

生成评测报告：

```bash
python scripts/build_evaluation_report.py
```

当前报告位于 `submission_artifacts/evaluation/evaluation_metrics.json` 和 `submission_artifacts/evaluation/evaluation_metrics.md`。已保存结果显示 17 个案例、45 个标注字段、22 条文本证据、11 条数字证据、6 条表格证据、profile、结构、质量、provenance 和 recovery 门槛均通过。该指标不是完整 OCR 字符级准确率，而是面向本赛题可复查结构化输出的提交级评测面。

## 9. 稳定性与耗时摘要

生成稳定性报告：

```bash
python scripts/build_stability_report.py
```

当前报告位于 `submission_artifacts/stability/stability_report.json` 和 `submission_artifacts/stability/stability_report.md`。它检查 `examples/evaluation/labels.json` 覆盖的 17 个保存案例，汇总 result/trace 存在性、trace 步骤数、工具调用次数、工具耗时、质量状态分布、provenance 分布和自动恢复执行数量。

边界：该报告是保存 artifact 的工程稳定性摘要，不是高并发压测。若要宣称生产级高负载能力，需要额外提供并发请求、长文档批量任务、资源占用和失败重试的现场压测记录。
