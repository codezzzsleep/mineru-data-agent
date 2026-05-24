# MinerU Data Agent

面向 MDIC 2026 赛道二的数据智能体提交项目。项目定位是 **CLI-first**：
稳定评审入口是 `data-agent` 命令行工具，不把长期公网 HTTP 服务作为主交付面。

系统使用 MinerU 处理 PDF/图片文档，使用轻量原生模块处理 HTML、DOCX、PPTX，并在解析结果之上增加任务画像推断、结构化抽取、质量校验、自动恢复、运行日志和检索导出。若评审环境提供真实大模型 Key，可通过 `data-agent agent-run` 运行 OpenAI-compatible 的 tool-calling LLM Agent。

## 评审先看

1. **完整中文技术报告**：`docs/技术报告.md`
2. **一页摘要**：`docs/EXECUTIVE_SUMMARY.md`
3. **评审指南与评分映射**：`docs/EVALUATION_GUIDE.md`
4. **典型案例说明**：`docs/CASE_STUDIES.md`
5. **提交证据总索引**：`submission_artifacts/ARTIFACTS_INDEX.md`
6. **CLI 契约**：`docs/CLI_CONTRACT.md`
7. **Live LLM Agent 证据说明**：`submission_artifacts/agent_live_cases/agent_live_report.md`

`docs/TECHNICAL_REPORT.md` 保留为同内容英文路径镜像，方便脚本和旧链接兼容；面向评委阅读时优先使用中文文件名。

## 核心能力

- `data-agent run`：单文档输入，输出结构化 JSON、trace、summary 和 retrieval chunks。
- `data-agent batch`：按 manifest 批处理；单个任务失败不会中断整批。
- `data-agent agent-run`：带 skill 选择、工具调用、答案校验和证据 trace 的 live LLM Agent 路径。
- PDF/图片支持 MinerU 在线 Agent API 和本地 MinerU CLI 两种后端。
- HTML/DOCX/PPTX 使用轻量原生解析，便于 CPU 环境复跑和回归测试。
- 质量检查覆盖空结果、文本噪声、页级来源、财报合计、弱结构和 profile 相关风险。
- 自动恢复覆盖文本清理、OCR retry，以及缺少页级来源时的可选 CLI fallback。
- 本地 SQLite 恢复记忆用于同一输出根目录下的重复运行策略复用。
- Retrieval JSONL 导出便于下游 RAG、搜索和评审抽查。

详细功能清单见 `docs/FEATURES.md`。

## 安装

基础 CLI：

```bash
pip install -e .
```

开发与测试：

```bash
pip install -e ".[dev]"
```

如果评审环境没有 MinerU CLI，又需要本地 pipeline 后端，可安装：

```bash
pip install -e ".[mineru]"
```

可选 HTTP wrapper 依赖，仅用于本地集成测试：

```bash
pip install -e ".[api]"
```

## 快速复跑

HTML/Office 冒烟路径，不依赖 MinerU：

```bash
data-agent run \
  --input examples/cases/case_1_financial_report.html \
  --out runs/cli_demo \
  --task "抽取财报关键字段并检查合计行" \
  --profile auto
```

CPU 环境解析 PDF，可走 MinerU 在线 Agent API：

```bash
data-agent run \
  --runner agent-api \
  --input demo.pdf \
  --out runs/pdf_api \
  --task "解析 PDF，输出结构化结果、质量日志和 retrieval chunks" \
  --method auto
```

需要页级 provenance 和 MinerU middle/layout/model artifact 时，使用本地 MinerU CLI：

```bash
data-agent run \
  --runner cli \
  --input demo.pdf \
  --out runs/pdf_cli \
  --task "解析财报 PDF，抽取表格、关键数字并检查合计行" \
  --backend pipeline \
  --method auto
```

批处理：

```bash
data-agent batch \
  --manifest examples/batch_manifest.json \
  --out runs/batch_demo
```

Live tool-calling Agent，需要真实 provider key：

```bash
data-agent agent-run \
  --provider modelscope \
  --input examples/cases/case_2_low_quality_ocr.html \
  --out runs/agent_live \
  --task "发现乱码后先清理，再抽取设备 B-17 的异常温度"
```

Provider key 只从环境变量读取：

```bash
export MODELSCOPE_API_KEY="<your-modelscope-token>"
export MODELSCOPE_BASE_URL="https://api-inference.modelscope.cn/v1"
export MODELSCOPE_MODEL="Qwen/Qwen3-235B-A22B-Instruct-2507"
```

PowerShell：

```powershell
$env:MODELSCOPE_API_KEY="<your-modelscope-token>"
$env:MODELSCOPE_BASE_URL="https://api-inference.modelscope.cn/v1"
$env:MODELSCOPE_MODEL="Qwen/Qwen3-235B-A22B-Instruct-2507"
```

## 输出契约

每次 `data-agent run` 会生成一个运行目录，主要文件包括：

- `result.json`：结构化结果和执行控制字段。
- `trace.json`：权威步骤/工具审计日志。
- `summary.md`：面向人工阅读的摘要。
- `retrieval/retrieval_chunks.jsonl`：RAG/搜索 chunks。
- `retrieval/retrieval_manifest.json`：检索导出元数据。

关键字段：

- `schema_version`
- `execution_control`
- `extracted`
- `quality`
- `recovery_decision`
- `retrieval_export`
- `trace_path`
- `summary_path`

完整 CLI 契约见 `docs/CLI_CONTRACT.md`。

## 已保存证据

提交包刻意区分确定性证据、离线回归 fixture 和真实 provider 证据，避免把 scripted case 包装成 live LLM 成功。

| 证据类别 | 当前保存结果 |
| --- | --- |
| 带标注评测 | 17 个案例、45 个预期字段，字段/证据/质量/provenance 检查见 `submission_artifacts/evaluation/` |
| MinerU CLI PDF | 4 个文件级本地 CLI 运行，含页级 provenance 和 MinerU 中间 artifact，见 `submission_artifacts/mineru_cases/` |
| 官方公开 PDF | IRS W-4、NIST AI RMF、Microsoft annual report exhibit、CDC VIS，见 `submission_artifacts/public_real_cases/` |
| 长文档分片 | NIST AI RMF 48 页拆成 3 个在线 Agent API 分片，见 `submission_artifacts/long_document_chunks/` |
| 失败/恢复 | controlled negative 与 recovery case，见 `submission_artifacts/failure_recovery_cases/` |
| Retrieval 校验 | chunk schema、重复率、密度和 lexical retrieval smoke，见 `submission_artifacts/retrieval_validation/` |
| Live tool-calling Agent | 旧版 provider 包：8 次 ModelScope Qwen3 尝试，4 次到达 finalize/tool-call completion，2 次人工复核 answer-quality pass，见 `submission_artifacts/agent_live_cases/` |

Live evidence 口径：

- `selected_skill` 表示 LLM 选择的高层 skill，如财报合计核验、not_found 防幻觉、文本恢复、合同条款、流程风险或通用结构化抽取。
- `answer_validation.ok=true` 表示最终答案通过内置证据、数字、简单算术和 selected-skill not_found 冲突检查。
- 新版 `agent-run` 在工具层强制要求先 `select_skill`，解析后才能 `validate_answer`，且 `finalize` 必须复用已经验证过的同一答案和同一证据列表。
- 已保存的 `agent_live_cases` 包生成于更严格的 skill/validation gate 之前，因此只作为旧版真实 provider trace，不声称新版 gate 已完成 provider rerun。
- `tool_call_completed=true` 只表示真实 provider 调用消耗 token 并到达 `finalize` 工具。
- `answer_quality_pass=true` 是单独的人工语义复核字段。
- 只有 2 个已保存 `answer_quality_pass=true` 案例可引用为 live-agent 语义成功。
- 离线 `agent_decision_cases` 是 scripted regression fixture；其中 token 数为脚本化计数，不是 live LLM 证据。

## 当前边界

- 本项目是 CLI-first 提交，不声称提供长期公网 API。
- FastAPI wrapper 仅作为本地集成实验的二级材料。
- 已保存评测标签包含项目自建 fixture 和轻量公开 PDF 标签，不等同第三方 OCR benchmark。
- 长文档保存证据展示分片编排能力，不等同 GPU 吞吐 benchmark。
- 成本报告使用 2026 年 5 月场景假设，生产规划前应替换为当前 provider 报价。

## 可选 HTTP Wrapper

仓库仍保留 FastAPI wrapper，用于本地集成测试，不是主要评审入口：

```bash
pip install -e ".[api]"
uvicorn mineru_data_agent.api:app --host 127.0.0.1 --port 8080
```

接口契约见 `docs/API_CONTRACT.md`，部署说明见 `docs/DEPLOYMENT_AND_API.md`。

## 开发与打包

```bash
pip install -e ".[dev]"
pytest -q
python -m compileall -q src scripts tests
```

构建提交 zip：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\make_submission_zip.ps1 -Output dist\mineru-data-agent-submission.zip
```

zip inventory 测试会检查 CLI/live-agent 文件和证据是否存在，并确认文本 artifact 中没有泄露本机路径。

## 开源材料

仓库包含 `LICENSE`、`CONTRIBUTING.md`、`CODE_OF_CONDUCT.md`、`SECURITY.md`、`ROADMAP.md`、Issue 模板、测试、脚本、文档和保存证据。公开仓库：

https://github.com/codezzzsleep/mineru-data-agent
