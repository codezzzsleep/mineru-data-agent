# MinerU Data Agent

基于 MinerU 的文档处理 Data Agent，面向「智能进化·Agent 能力评测赛道」设计。

评审导航见 `docs/EVALUATION_GUIDE.md`；一页摘要见 `docs/EXECUTIVE_SUMMARY.md`；上手选择见 `docs/QUICK_DECISION_GUIDE.md`；新增 profile 参考 `docs/PROFILE_EXTENSION_GUIDE.md`。

指标口径：`quality.score` 记录空结果、乱码、页级来源缺失、合计行不一致等规则风险；字段级 precision/recall/F1 在 `submission_artifacts/evaluation/` 单独统计。`submission_artifacts/cases/` 用于复跑 HTML/网页流程，PDF、Office、公开真实文档和长文档证据分别放在对应的 artifact 目录中。

项目在 MinerU/HTML/Office 解析结果之上增加：

- 任务意图识别、自适应执行计划、动态 schema、任务级后处理和恢复优先级
- 可配置 profile 推断：内置 profile 由关键词和轻量确定性 token/字符向量相似度共同打分，可用 `MINERU_DATA_AGENT_PROFILE_CONFIG` 调整；它不是学习型 embedding 模型
- Agent action plan：每次运行记录子任务拆解、候选工具、动态选择原因、replan triggers、质量后的再规划结果和本地记忆策略
- PDF/图片的 MinerU 解析适配，以及 DOCX/PPTX/HTML 的轻量结构化适配；当前提交包已包含 4 个 PDF 文件级本地 MinerU CLI 证据和 2 个 Office 文件级证据
- HTML 文档的轻量结构化适配，保留标题层级、段落、列表和表格
- DOCX/PPTX 文档的轻量结构化适配，保留 Word 章节/表格与 PPT slide-level provenance
- Markdown、内容块、表格、键值对、数字事实、日期/建议/异常信号抽取
- 文本质量、页码溯源、财报数字、合同/规范结构等校验
- 可选 DeepSeek/ModelScope 预执行调度：在解析前建议 profile、runner、backend、method、语言、目标 schema 和恢复策略，并把安全白名单内的建议实际应用到本次运行
- 质量异常后的自动恢复执行：编码噪声清理二次 pass，以及 PDF/图片类低质量结果的 OCR 重试择优
- 在线 Agent API 缺少页级 provenance 时，如果检测到本地 MinerU CLI 或显式配置了 CLI 路径，可自动触发 CLI fallback，并把初始问题码、两次尝试和最终择优结果写入 `recovery_decision`
- 跨运行本地记忆：同一输出根目录下的 `.mineru_data_agent/memory.sqlite` 记录 profile、问题码和恢复结果，后续运行可把历史成功恢复路径纳入 `runtime_recovery_plan`；这是本地统计，不是模型训练
- 面向检索/评测入库的 `retrieval_chunks.jsonl` 导出
- `result.json`、`trace.json`、`summary.md` 三类可复查输出；新结果含 `schema_version`，便于下游兼容性检查
- FastAPI 同步接口与异步 job/polling 接口，方便组委会或评审脚本调用
- Dockerfile 与 docker-compose 一键启动 API，降低复现成本
- 5 个可复跑 HTML/网页 fixture artifact，覆盖财报、低质量 OCR、合同条款、流程说明和网页巡检
- 4 个 PDF 文件级本地 MinerU CLI artifact，覆盖扫描版、财报表格、合同条款和流程图文档，包含 MinerU 中间文件和页级 provenance
- 1 个 CPU 友好的 MinerU 在线 Agent API PDF artifact，用于验证无本地 GPU 时的 PDF fixture 主流程
- 1 个真实 PDF recovery 证据：在线 API 先跑、缺少页级 provenance 后自动 fallback 到 CLI artifact，`recovery_decision.executed=true`
- 2 个 Office 文件级 artifact，覆盖 Word 合规矩阵和 PowerPoint 工作流汇报
- 4 个更贴近评审挑战的复杂文档 fixture，并附人工标注表，覆盖跨页财报、OCR 噪声合同、行业标准矩阵和故障工作流
- 4 个官方公开真实 PDF 案例，覆盖 IRS 表单、NIST AI RMF、Microsoft SEC 年报和 CDC 公共卫生说明，并附人工轻量标注和来源元数据
- 1 个自适应规划案例：同一财报输入在“增长最快项目”和“异常/证据复核”两个任务下生成不同 task intents、target schema、post-processors 和 task-specific answers
- 5 个 Agent decision 离线回归案例：覆盖财报增长、OCR 噪声合同、条款实体、流程图文档和跨页表格，展示任务拆解、动态工具选择和质量后 replan；不作为 live LLM 证据
- 5 个 controlled failure/recovery 案例：覆盖 text cleanup、OCR retry 成功/失败、strict provenance failure 和 numeric mismatch；不作为 live OCR/GPU/公网 benchmark
- 1 个 controlled cross-run memory 案例：同一噪声文档第二次运行读取第一次 text cleanup 成功记录，并把本地统计推荐写入 `runtime_recovery_plan`
- 1 个实际启用 DeepSeek-V4-Flash 的 LLM 证据案例，用于任务理解、schema 建议、复核重点和恢复建议；当前 live rerun 已记录 2 次 LLM 调用、4309 tokens
- 1 份 LLM impact 报告，对比保存的规则运行与 LLM-enabled 运行，列出 LLM 决策点、token、应用/忽略项和 recovery suggestion
- 1 份成本模型报告，把 native、CLI、在线 API、LLM 四类路径拆开，并用环境变量填入价格后自动估算 100 份文档成本
- 1 份恢复有效性报告，按保存结果汇总 recovery 触发率、被选中的恢复路径、初始问题码和额外工具耗时
- 1 份长文档风险报告，单独列出 NIST 48 页分片运行的页级来源、跨分片上下文和 GPU/CLI 长文档缺口
- 1 份 retrieval validation 报告，检查 chunk schema、空文本、重复率和轻量 lexical top-k 命中率；不作为 embedding benchmark
- 1 份 agent value 报告，区分 deterministic/offline/live/controlled 决策模式，并统计 Agent 层在 parser artifact 之外增加的 schema、质量、恢复、field evidence 和 retrieval 字段
- 1 份 coverage.py 行覆盖率报告，当前覆盖 `src/mineru_data_agent`
- 1 份代码质量报告，统计 Python 文件、代码行、测试函数和 CI workflow，方便评审快速检查工程规模
- 1 份带标注评测报告，新增字段级 precision/recall/F1 与 failed-check 分布，用于区分规则质量分和人工标签指标
- 2 份本地 HTTP loopback 压测报告，覆盖同步解析和异步 job 轮询；其中加强版为 100 请求、并发 20、100/100 成功；另有 1 份成本/速度/质量对比报告，按 runner/场景组展示 tradeoff

## Quick Start

### 1. 安装

只使用在线 Agent API 和项目后处理逻辑时，安装轻量依赖即可：

```bash
pip install -e ".[dev]"
```

在和鲸 MinerU GPU 镜像中，如果要使用本地 MinerU CLI 完整产出 layout/middle/model 等 artifact，建议优先使用镜像内已有 MinerU；如果没有，安装 pipeline 版本：

```bash
pip install -e ".[mineru]"
```

### 2. 命令行运行

推荐先用 MinerU 在线 Agent API 跑通项目主流程。该接口免登录、无需 Token，适合 CPU 环境或 GPU 资源不可用时快速验证：

```bash
data-agent run \
  --runner agent-api \
  --input /path/to/input.pdf \
  --out runs \
  --task "解析扫描版中文 PDF，输出结构化文本和质量日志" \
  --method auto
```

如果有 HeyWhale MinerU 镜像或本地 MinerU CLI，再切换为本地完整解析：

```bash
data-agent run \
  --input /path/to/input.pdf \
  --out runs \
  --task "解析财报 PDF，抽取表格、关键数字并检查合计行" \
  --backend pipeline \
  --method auto
```

本地 Windows 调试时，如果 MinerU 在独立环境里：

```powershell
$env:MINERU_ROOT="D:\path\to\MinerU"
python -m mineru_data_agent.cli run `
  --input $env:MINERU_ROOT\demo\pdfs\small_ocr.pdf `
  --out runs `
  --task "解析扫描版中文 PDF，输出结构化文本和质量日志" `
  --mineru-executable $env:MINERU_ROOT\.venv\Scripts\mineru.exe
```

### 3. API 服务

```bash
uvicorn mineru_data_agent.api:app --host 0.0.0.0 --port 8080
```

也可以用 Docker 一键启动本地 API：

```bash
docker compose up --build
```

健康检查：

```bash
curl http://127.0.0.1:8080/health
```

解析接口：

```bash
curl -X POST http://127.0.0.1:8080/v1/parse \
  -F "file=@demo.pdf" \
  -F "task=解析财报 PDF，抽取表格、关键数字并检查合计行" \
  -F "profile=auto" \
  -F "runner=agent-api"
```

API 默认把输出持久化到 `runs/api`，也可以通过 `MINERU_DATA_AGENT_OUTPUT_DIR` 或表单字段 `output_root` 指定目录，确保返回的 `trace_path`、`summary_path` 和 artifact 路径在请求结束后仍可复查。公开部署时建议设置 `MINERU_DATA_AGENT_ALLOWED_OUTPUT_BASE` 约束 `output_root` 可写范围，并通过 `MINERU_DATA_AGENT_MAX_UPLOAD_MB` 或 `MINERU_DATA_AGENT_MAX_UPLOAD_BYTES` 限制上传大小。

本提交包内保存了本地 API 冒烟测试结果：`submission_artifacts/api_smoke/`。该测试覆盖 `/health`、一次 HTML 上传解析和一次 PDF 上传解析，返回结构化结果、trace、summary 和 retrieval 路径；当前尚未提供公网服务地址。

异步接口使用 `POST /v1/jobs` 提交同样的 multipart 表单，随后用 `GET /v1/jobs/{job_id}` 查询 `queued/running/completed/failed` 状态；完成后 `result` 字段与 `/v1/parse` 返回一致。并发 smoke 结果位于 `submission_artifacts/api_load_smoke/`，当前保存 8 请求、并发 4 的本地 FastAPI TestClient 结果，8/8 成功且每次都落盘 trace/result/summary。本地 HTTP loopback 压测结果位于 `submission_artifacts/http_load_test/` 和 `submission_artifacts/http_load_test_100/`：前者保存 12 请求、并发 6、12/12 成功并保留每次请求 artifact；后者保存 100 请求、并发 20，混合同步 `/v1/parse` 和异步 `/v1/jobs`，100/100 成功、P95 约 4.21 秒。这是本地 TCP 层验证；公网和 GPU 压测需在部署环境另跑。

本地 MinerU CLI API 调用：

```bash
curl -X POST http://127.0.0.1:8080/v1/parse \
  -F "file=@demo.pdf" \
  -F "task=解析财报 PDF，抽取表格、关键数字并检查合计行" \
  -F "profile=auto" \
  -F "runner=cli" \
  -F "backend=pipeline"
```

### 4. 批处理运行

赛题页强调复杂任务规划、批处理执行、异常处理与恢复。项目提供批处理入口，按 manifest 连续运行多个任务，并在单个任务失败时继续执行后续任务；单文件运行中也会把自动恢复尝试写入 `recovery_decision.attempts`：

```bash
data-agent batch \
  --manifest examples/batch_manifest.json \
  --out runs/batch_html
```

批处理会生成 `batch_report.json`，记录每个任务的状态、run id、输出目录、质量评分和错误信息。

生成提交用 5 个案例证据：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_submission_cases.ps1 -Python .\.venv\Scripts\python.exe
```

输出会写入 `submission_artifacts/cases/`，每个案例包含输入样例、`result.json`、`trace.json`、`summary.md` 和 `retrieval/` 文件。当前已生成的 5 个 HTML fixture 案例覆盖：

- 财报密集数字与合计行复核
- 低质量 OCR 与编码噪声识别
- 合同/行业标准条款结构化
- 工艺流程步骤与异常节点解析
- HTML 网页巡检日报清洗

收集真实 MinerU CLI PDF 运行证据：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\collect_mineru_case.ps1 -RunDir runs\mineru_cli_refresh\4568109b3cc5
```

当前证据位于 `submission_artifacts/mineru_cases/case_mineru_cli_low_quality_pdf/`，包含原始输入 PDF、副本、`mineru-cli` trace、MinerU `middle/model/layout/span/origin` 等 artifact 和 retrieval 导出。

在线 API 缺少页级 provenance 时，系统会在检测到本地 `mineru` 命令、`MINERU_EXECUTABLE` 或显式 `--fallback-mineru-executable` 后自动启用 CLI fallback；没有可用 CLI 时会保留在线 API 结果和 provenance 警告，避免在评审 CPU 环境里产生无意义的失败恢复记录：

```bash
data-agent run \
  --runner agent-api \
  --fallback-mineru-executable /path/to/mineru \
  --input /path/to/input.pdf \
  --out runs \
  --task "先用在线 API 解析 PDF，缺少页级 provenance 时自动切换本地 CLI"
```

如果评测任务必须要求页级来源，可加 `--strict-page-provenance`。在 fallback 后仍缺页级来源时，系统会保留 partial result，但把 `quality.status` 标成 `needs_review`，并在 `recovery_decision.decision=strict_page_provenance_failed` 中写明原因。

生成并复跑额外 PDF 文件级样本：

```powershell
$env:MINERU_ROOT="D:\path\to\MinerU"
$env:MINERU_ROOT\.venv\Scripts\python.exe .\scripts\generate_complex_pdf_fixtures.py
```

当前提交包还包含 3 个可公开分享的合成业务 PDF 文件级证据，位于 `submission_artifacts/mineru_cases/`：

- `case_mineru_cli_financial_pdf`：3 页财报样本，包含密集数字表、负值、合计行和审计备注。
- `case_mineru_cli_contract_pdf`：2 页合同/标准样本，包含条款、合规矩阵和签署信息。
- `case_mineru_cli_workflow_pdf`：2 页流程/工程样本，包含流程图图片 artifact、执行矩阵、异常和建议。

生成官方公开真实文档案例：

```powershell
.\.venv\Scripts\python.exe .\scripts\run_public_real_cases.py
```

当前结果位于 `submission_artifacts/public_real_cases/`，包含 4 份官方公开 PDF：IRS W-4 表单、NIST AI RMF 1.0、Microsoft 2024 Annual Report SEC PDF exhibit 和 CDC VIS 使用说明。每个案例都保存输入副本、source metadata、human labels、`result.json`、`trace.json`、`summary.md` 和 retrieval 导出。NIST 与 Microsoft 长文档在该公开样本目录中按在线 Agent API 页数限制提交前 20 页，并在 `source_metadata.json` 标明运行范围。

生成长文档分片执行证据：

```powershell
.\.venv\Scripts\python.exe .\scripts\run_long_document_chunks.py
```

当前长文档结果位于 `submission_artifacts/long_document_chunks/public_nist_ai_rmf_full_chunked/`。它使用同一份 NIST AI RMF 1.0 官方公开 PDF，自动按在线 MinerU Agent API 的 20 页上限拆为 1-20、21-40、41-48 三段执行；保存每段 `result.json`、`trace.json`、`summary.md`、retrieval 导出，以及总报告 `long_document_chunk_report.md`。本次保存结果为 48 页、3/3 分片成功、42.418 秒、58 个 retrieval chunks。该结果用于展示长文档分片编排；本地 MinerU CLI/GPU 压测需在对应资源环境另跑。

生成并复跑 Office 文件级样本：

```powershell
$env:MINERU_ROOT="D:\path\to\MinerU"
$env:MINERU_ROOT\.venv\Scripts\python.exe .\scripts\generate_office_fixtures.py
```

当前 Office 证据位于 `submission_artifacts/office_cases/`：

- `case_docx_standard_review`：Word 标准审查包，包含章节、合规矩阵、风险和建议。
- `case_pptx_workflow_review`：PowerPoint 工作流汇报，包含 3 个 slide、执行矩阵、风险和建议。

### 5. 可选大模型增强

项目支持接入 DeepSeek 官方 OpenAI-compatible API，也支持 ModelScope 的 OpenAI-compatible 推理入口。默认关闭，不影响基础复现；开启后会先执行 `llm_pre_execution_planning`，在解析前建议 profile、runner、backend、method、语言、目标 schema 和恢复策略。系统只会应用白名单内且未被用户显式锁定的建议，例如把低质量扫描 PDF 的 `method=auto` 调整为 `method=ocr`；runner 建议会被记录，但实际 runner 仍由 `--runner` 或 API 参数控制。解析后还会继续生成任务理解、动态 schema、复核重点和异常恢复建议。

先设置环境变量，不要把 key 写进代码或提交包：

```bash
export DEEPSEEK_API_KEY="<your-deepseek-key>"
export DEEPSEEK_BASE_URL="https://api.deepseek.com"
export DEEPSEEK_MODEL="deepseek-v4-flash"
```

Windows PowerShell：

```powershell
$env:DEEPSEEK_API_KEY="<your-deepseek-key>"
$env:DEEPSEEK_BASE_URL="https://api.deepseek.com"
$env:DEEPSEEK_MODEL="deepseek-v4-flash"
```

如果走 ModelScope：

```powershell
$env:MODELSCOPE_API_KEY="<your-modelscope-token>"
$env:MODELSCOPE_BASE_URL="https://api-inference.modelscope.cn/v1"
$env:MODELSCOPE_MODEL="deepseek-ai/DeepSeek-V4-Flash"
```

运行时开启：

```bash
data-agent run \
  --runner agent-api \
  --llm deepseek \
  --input demo.pdf \
  --out runs \
  --task "解析财报 PDF，抽取关键数字并检查合计行"
```

ModelScope 入口：

```bash
data-agent run \
  --runner agent-api \
  --llm modelscope \
  --input demo.pdf \
  --out runs \
  --task "解析财报 PDF，抽取关键数字并检查合计行"
```

API 调用时传 `llm=deepseek` 或 `llm=modelscope` 即可。输出中的 `execution_control` 会记录 LLM 预调度建议、实际应用/忽略的参数变更和最终解析参数；`llm_analysis.pre_execution_plan` 会保留解析前计划，`llm_analysis.post_parse_analysis` 会保留解析后复核。如果服务返回 `reasoning_content`，也会进入 `llm_analysis`。

本提交包保存了一次实际启用 ModelScope DeepSeek-V4-Flash 的证据，见 `submission_artifacts/llm_cases/`。该案例的 `trace.json` 记录 `modelscope-llm-preplan completed` 与 `modelscope-llm completed`，`result.json` 中 `llm_analysis.enabled=true`，`usage_summary.total_tokens=4309`。API key 只通过环境变量传入，没有写入输出文件。

另有 `submission_artifacts/recovery_cases/case_pdf_llm_api_to_cli_fallback/` 保存真实 PDF 的解析前调度和 API-to-CLI fallback 结果。当前环境没有 DeepSeek/ModelScope key，也没有可直接调用的 MinerU CLI 可执行文件，因此该案例使用离线确定性预调度器和已保存的本地 CLI artifact 回放来记录代码级恢复路径；`README.md`、`trace.json` 和 `result.json` 都标注了运行条件。配置真实 LLM key 与 MinerU CLI 后，同一机制可转为在线全链路运行。

## Output

每次运行会生成一个独立 run 目录：

```text
runs/<run_id>/
  result.json      # 结构化结果，含 sections/tables/key_values/semantic_signals
  trace.json       # 执行步骤、工具调用、耗时、错误信息
  summary.md       # 人类可读摘要
  retrieval/
    retrieval_chunks.jsonl     # 检索/向量库入库用的最小 JSONL
    retrieval_manifest.json    # 检索导出元数据和统计
    retrieval_quality.json     # 被过滤块、噪声块和解析风险
  mineru/          # 本地 MinerU 原始输出，包括 md/json/pdf 可视化文件
```

在线 Agent API 后端会生成 `mineru/<file>/agent_api/`，包含 Markdown、轻量内容块和 API 响应日志；本地 CLI 后端会保留 MinerU 的完整 artifact。

带标注评测指标可通过以下命令生成：

```bash
python scripts/build_evaluation_report.py
```

当前报告位于 `submission_artifacts/evaluation/`，覆盖 17 个提交案例、45 个标注字段、22 条文本证据、11 条数字证据、6 条表格证据、profile 命中、结构门槛、质量门槛、provenance 门槛和 recovery 门槛，并额外输出字段级 precision/recall/F1 与 failed-check 分布。

提交 artifact 总索引可通过以下命令生成：

```bash
python scripts/build_artifacts_index.py
```

当前索引位于 `submission_artifacts/ARTIFACTS_INDEX.md`，按目录列出 result/trace 数量和主要报告。

成本、速度和质量 tradeoff 对比可通过以下命令生成：

```bash
python scripts/build_baseline_comparison.py
```

当前报告位于 `submission_artifacts/baseline_comparison/`，按 native HTML、MinerU CLI PDF、Office、LLM recovery、挑战 fixture 和官方公开 PDF 分组展示标注通过率、工具耗时、平均质量分、trace 步骤数、页级 provenance 和 recovery 执行情况。它是保存 artifact 的对比视图，不是第三方 OCR benchmark。

LLM 开启/关闭影响对比可通过以下命令生成：

```bash
python scripts/build_llm_impact_report.py
```

当前报告位于 `submission_artifacts/llm_impact/`，对比保存的财报 HTML 规则运行与 LLM-enabled 运行。它用于说明 LLM 决策点和成本，不替代更大规模的 live LLM benchmark。

成本模型、恢复汇总、长文档风险、retrieval validation、agent value、coverage 和代码质量报告可通过以下命令生成：

```bash
python scripts/build_cost_model.py
python scripts/run_failure_recovery_cases.py
python scripts/build_recovery_effectiveness_report.py
python scripts/build_long_document_risk_report.py
python scripts/build_retrieval_validation_report.py
python scripts/build_agent_value_report.py
python scripts/build_coverage_report.py
python scripts/build_code_quality_report.py
python scripts/build_artifacts_index.py
```

当前报告分别位于 `submission_artifacts/cost_model/`、`submission_artifacts/failure_recovery_cases/`、`submission_artifacts/recovery_effectiveness/`、`submission_artifacts/long_document_risk/`、`submission_artifacts/retrieval_validation/`、`submission_artifacts/agent_value/`、`submission_artifacts/coverage/` 和 `submission_artifacts/code_quality/`。成本报告默认只给公式；设置 `MINERU_DATA_AGENT_GPU_CNY_PER_HOUR`、`MINERU_DATA_AGENT_AGENT_API_CNY_PER_PAGE`、`MINERU_DATA_AGENT_ASSUMED_PAGES_PER_PDF`、`MINERU_DATA_AGENT_LLM_CNY_PER_MILLION_TOKENS` 后会给出人民币估算。

离线 Agent decision 回归包可通过以下命令生成：

```bash
python scripts/run_agent_decision_cases.py
python scripts/build_artifacts_index.py
```

当前结果位于 `submission_artifacts/agent_decision_cases/`。该包是离线决策回归材料，使用本地 scripted decision client 复现子任务拆解、工具选择和 replan 字段；其中 token 数是脚本化计数，不作为 live LLM 用量或模型自主规划证据。真实 provider 调用仍以 `submission_artifacts/llm_cases/` 中的 ModelScope 案例为准。

## Recommended HeyWhale Setup

- 项目类型：IDE
- 镜像优先级：
  1. MinerU GPU镜像
  2. 沐曦资源vllm-metax-0.15.0-maca3.5.3.203-torch2.8
  3. scipy-py3.10-maca2.27-pytorch-mpi-ide
- 计算资源优先级：
  1. MinerU沐曦资源
  2. GPU 16G/24G 显存
  3. CPU 4核16G 运行在线 API 后端和轻量调试

## Competition Positioning

本项目的参赛定位：

- 用 MinerU 完成底层版面/OCR/结构解析
- 用 Agent 计划组织解析步骤和后处理
- 用质量校验降低幻觉和不可追溯问题
- 用日志和 artifact 路径记录每一步

官方 MDIC2026 页面明确赛道二要求构建「数据智能体 Data Agent」，并说明参赛需使用 MinerU 工具链（含 SaaS 端与开源项目）。本项目的赛题对齐分析见 `docs/COMPETITION_ALIGNMENT.md`。

赛题页评分维度与本项目优化策略见 `docs/EVALUATION_STRATEGY.md`；部署与 API 复现说明见 `docs/DEPLOYMENT_AND_API.md`；评审快速路径见 `docs/EVALUATION_GUIDE.md`。

项目原创性、第三方参考边界和密钥处理说明见 `docs/ORIGINALITY_AND_COMPLIANCE.md`。

开源发布前后检查见 `docs/OPEN_SOURCE_RELEASE.md`。提交压缩包路径为 `dist/mineru-data-agent-submission.zip`，公开仓库为 https://github.com/codezzzsleep/mineru-data-agent；提交时同时记录本次推送后的 commit hash。开源协作材料包括 `CONTRIBUTING.md`、GitHub Actions 和 `.github/ISSUE_TEMPLATE/`。

## Backend Strategy

- `--runner agent-api`：调用 MinerU 在线 Agent API，免 Token、资源轻、启动快，适合 CPU 环境先跑通主流程。
- 在线 Agent API 的轻量 Markdown 路径不保证页级 provenance；系统会在 `quality.issues` 中用 `no_page_provenance` 显式提示，并在检测到可用 CLI fallback 时自动尝试本地 MinerU CLI。
- `--strict-page-provenance`：当 PDF/image 类输入最终仍缺页级 provenance 时，把结果标为 `needs_review` 和 `strict_page_provenance_failed`，用于审计型任务。
- `--runner cli`：调用本地 MinerU CLI，适合 GPU 镜像、大文件、完整中间结果和可视化 PDF artifact。
- `--llm deepseek`：可选 DeepSeek v4-flash 官方推理层，参与解析前调度和解析后复核；不开启时项目仍可运行。
- `--llm modelscope`：可选 ModelScope 推理入口，默认模型 `deepseek-ai/DeepSeek-V4-Flash`。

当前提交包按以下材料组织：

- 案例：HTML/网页 fixture、PDF CLI、Agent API PDF、PDF recovery、DOCX/PPTX、挑战样本、离线 Agent decision regression pack、公开真实 PDF、长文档分片、LLM-enabled 财报复核。
- 指标：`submission_artifacts/evaluation/` 统计 17 个案例、45 个字段、22 条文本证据、11 条数字证据、6 条表格证据和字段级 precision/recall/F1。
- 稳定性：`submission_artifacts/stability/` 汇总 trace、工具调用、耗时、质量状态和恢复执行。
- API：`submission_artifacts/api_load_smoke/`、`submission_artifacts/http_load_test/`、`submission_artifacts/http_load_test_100/` 保存本地接口验证和 100 请求并发结果。
- 成本/速度/质量：`submission_artifacts/baseline_comparison/` 按 runner 和场景组展示耗时、质量、页级 provenance 和 recovery；`submission_artifacts/llm_cost/` 记录 live LLM token usage；`submission_artifacts/llm_impact/` 对比规则运行与 LLM-enabled 运行。
- 运行边界：`submission_artifacts/cost_model/` 给出成本公式，`submission_artifacts/failure_recovery_cases/` 保存 controlled fault-injection 负样本与恢复路径，`submission_artifacts/recovery_effectiveness/` 汇总恢复触发和选择情况，`submission_artifacts/long_document_risk/` 列出长文档分片风险，`submission_artifacts/retrieval_validation/` 保存 chunk schema/去重/lexical 检索冒烟检查，`submission_artifacts/agent_value/` 汇总 Agent 层相对 parser artifact 的增量字段和决策模式，`submission_artifacts/coverage/` 保存覆盖率，`submission_artifacts/code_quality/` 汇总代码和测试规模。

新运行还会输出 `extracted.field_evidence` 和 `extracted.task_result`，为键值字段、任务级答案和 schema 决策提供可复查字段。公开真实文档样本使用轻量人工标注；如果需要 OCR 字符级或表格逐格 benchmark，应按 `docs/BENCHMARK_AND_ROADMAP.md` 扩展。

针对评审常见追问的证据矩阵见 `docs/ENGINEERING_EVIDENCE.md`；API 同步/异步接口、错误码和返回 schema 见 `docs/API_CONTRACT.md`；对标与后续真实 benchmark 路线见 `docs/BENCHMARK_AND_ROADMAP.md`；artifact 总索引见 `submission_artifacts/ARTIFACTS_INDEX.md`；稳定性摘要见 `submission_artifacts/stability/stability_report.md`，本地 API 并发 smoke 见 `submission_artifacts/api_load_smoke/api_load_smoke_report.md`，本地 HTTP loopback 压测见 `submission_artifacts/http_load_test/http_load_test_report.md` 和 `submission_artifacts/http_load_test_100/http_load_test_report.md`，Agent decision 回归案例见 `submission_artifacts/agent_decision_cases/README.md`，failure/recovery 负样本见 `submission_artifacts/failure_recovery_cases/README.md`，长文档分片证据见 `submission_artifacts/long_document_chunks/public_nist_ai_rmf_full_chunked/long_document_chunk_report.md`，长文档风险拆解见 `submission_artifacts/long_document_risk/long_document_risk_report.md`，retrieval validation 见 `submission_artifacts/retrieval_validation/retrieval_validation_report.md`，agent value 见 `submission_artifacts/agent_value/agent_value_report.md`，成本/速度/质量对比见 `submission_artifacts/baseline_comparison/baseline_comparison.md`，成本模型见 `submission_artifacts/cost_model/cost_model.md`，LLM token/cost 审计见 `submission_artifacts/llm_cost/llm_cost_report.md`，LLM impact 对比见 `submission_artifacts/llm_impact/llm_impact_report.md`，恢复有效性见 `submission_artifacts/recovery_effectiveness/recovery_effectiveness_report.md`，覆盖率见 `submission_artifacts/coverage/coverage_report.md`，代码质量摘要见 `submission_artifacts/code_quality/code_quality_report.md`。
