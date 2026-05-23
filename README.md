# MinerU Data Agent

基于 MinerU 的复杂文档 Data Agent，面向「智能进化·Agent 能力评测赛道」设计。

证据边界：本项目里的 `quality.score` 是规则校验分，不是字段级、表格逐格或 OCR 字符级准确率。`submission_artifacts/cases/` 是自构造 HTML/网页 fixture，用于验证 Agent 管线和可追溯产物；PDF 文件级 MinerU 证据见 `submission_artifacts/mineru_cases/`，其中多个样本是为公开提交生成的合成业务样本。

它不是简单调用 MinerU，而是在 MinerU/HTML 解析结果之上增加：

- 任务意图识别与执行计划
- PDF/图片的 MinerU 解析适配，以及 DOCX/PPTX/HTML 的轻量结构化适配；当前提交包已包含 4 个 PDF 文件级本地 MinerU CLI 证据和 2 个 Office 文件级证据
- HTML 文档的轻量结构化适配，保留标题层级、段落、列表和表格
- DOCX/PPTX 文档的轻量结构化适配，保留 Word 章节/表格与 PPT slide-level provenance
- Markdown、内容块、表格、键值对、数字事实、日期/建议/异常信号抽取
- 文本质量、页码溯源、财报数字、合同/规范结构等校验
- 可选 DeepSeek/ModelScope 预执行调度：在解析前建议 profile、runner、backend、method、语言、目标 schema 和恢复策略，并把安全白名单内的建议实际应用到本次运行
- 质量异常后的自动恢复执行：编码噪声清理二次 pass，以及 PDF/图片类低质量结果的 OCR 重试择优
- 面向检索/评测入库的 `retrieval_chunks.jsonl` 导出
- `result.json`、`trace.json`、`summary.md` 三类可复查输出
- FastAPI 接口，方便组委会或评审脚本调用
- 5 个可复跑 HTML/网页 fixture artifact，覆盖财报、低质量 OCR、合同条款、流程说明和网页巡检
- 4 个 PDF 文件级本地 MinerU CLI artifact，覆盖扫描版、财报表格、合同条款和流程图文档，包含 MinerU 中间文件和页级 provenance
- 1 个 CPU 友好的 MinerU 在线 Agent API PDF artifact，证明无需本地 GPU 也可跑通 PDF fixture 主流程
- 2 个 Office 文件级 artifact，覆盖 Word 合规矩阵和 PowerPoint 工作流汇报
- 1 个实际启用 DeepSeek-V4-Flash 的 LLM 证据案例，用于任务理解、schema 建议、复核重点和恢复建议

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

本提交包内保存了本地 API 冒烟测试证据：`submission_artifacts/api_smoke/`。该测试覆盖 `/health`、一次 HTML 上传解析和一次 PDF 上传解析，证明 FastAPI 服务能返回结构化结果、trace、summary 和 retrieval 路径；当前尚未提供公网服务地址。

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

生成并复跑额外 PDF 文件级样本：

```powershell
$env:MINERU_ROOT="D:\path\to\MinerU"
$env:MINERU_ROOT\.venv\Scripts\python.exe .\scripts\generate_complex_pdf_fixtures.py
```

当前提交包还包含 3 个可公开分享的合成业务 PDF 文件级证据，位于 `submission_artifacts/mineru_cases/`：

- `case_mineru_cli_financial_pdf`：3 页财报样本，包含密集数字表、负值、合计行和审计备注。
- `case_mineru_cli_contract_pdf`：2 页合同/标准样本，包含条款、合规矩阵和签署信息。
- `case_mineru_cli_workflow_pdf`：2 页流程/工程样本，包含流程图图片 artifact、执行矩阵、异常和建议。

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

本提交包保存了一次实际启用 ModelScope DeepSeek-V4-Flash 的证据，见 `submission_artifacts/llm_cases/`。该案例的 `trace.json` 记录 `modelscope-llm completed`，`result.json` 中 `llm_analysis.enabled=true`。API key 只通过环境变量传入，没有写入输出文件。

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

当前报告位于 `submission_artifacts/evaluation/`，覆盖 8 个提交案例、24 个标注字段、profile 命中、结构门槛、质量门槛和 provenance 门槛。

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

本项目主打「可信复杂文档处理」：

- 用 MinerU 完成底层版面/OCR/结构解析
- 用 Agent 计划组织解析步骤和后处理
- 用质量校验降低幻觉和不可追溯问题
- 用日志和 artifact 路径证明每一步可复现

官方 MDIC2026 页面明确赛道二要求构建「数据智能体 Data Agent」，并说明参赛需使用 MinerU 工具链（含 SaaS 端与开源项目）。本项目的赛题对齐分析见 `docs/COMPETITION_ALIGNMENT.md`。

赛题页评分维度与本项目优化策略见 `docs/EVALUATION_STRATEGY.md`；部署与 API 复现说明见 `docs/DEPLOYMENT_AND_API.md`。

项目原创性、第三方参考边界和密钥处理说明见 `docs/ORIGINALITY_AND_COMPLIANCE.md`。

开源发布前后检查见 `docs/OPEN_SOURCE_RELEASE.md`。当前压缩包提交路径已经完整，公开仓库为 https://github.com/codezzzsleep/mineru-data-agent；提交时同时记录本次推送后的 commit hash。

## Backend Strategy

- `--runner agent-api`：调用 MinerU 在线 Agent API，免 Token、资源轻、启动快，适合先完成比赛演示闭环。
- 在线 Agent API 的轻量 Markdown 路径不保证页级 provenance；系统会在 `quality.issues` 中用 `no_page_provenance` 显式提示。
- `--runner cli`：调用本地 MinerU CLI，适合 GPU 镜像、大文件、完整中间结果和可视化 PDF artifact。
- `--llm deepseek`：可选 DeepSeek v4-flash 官方推理层，参与解析前调度和解析后复核；不开启时项目仍可完整运行。
- `--llm modelscope`：可选 ModelScope 推理入口，默认模型 `deepseek-ai/DeepSeek-V4-Flash`。

当前提交包内的强复现证据分为六类：5 个 HTML/网页 fixture 用于稳定验证 Agent 的计划、结构化抽取、质量校验、trace、自动恢复与检索导出；4 个 PDF 文件级案例用本地 `mineru-cli` 跑通，证明 MinerU CLI 后端、页级 provenance、HTML 表格解析、图像 artifact 和完整中间 artifact 可用；1 个 CPU 友好的 MinerU 在线 Agent API PDF 案例证明无 GPU 条件下也能跑通 PDF fixture；2 个 DOCX/PPTX 文件级案例证明 Office 文档结构化、表格抽取和 slide-level provenance 可用；1 个 LLM-enabled 财报复核案例证明 DeepSeek-V4-Flash 能参与任务理解、schema 建议和风险恢复建议；1 份带标注评测报告证明 8 个案例的 24 个标注字段、profile、结构门槛、质量门槛和 provenance 门槛均可复查。合成 PDF/Office 样本不能替代真实客户材料的长期泛化评测。
