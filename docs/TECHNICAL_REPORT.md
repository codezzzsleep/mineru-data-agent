# Technical Report

## 0. 证据边界与评分口径

本文中的 `quality.score` 是规则校验分：表示本次运行是否触发空结果、乱码、页级 provenance 缺失、profile 预期缺失、合计行不一致等阻断或警告规则。它不是字段级准确率、表格逐格准确率或 OCR 字符准确率。HTML/网页案例是自构造 fixture，用于验证 Agent 管线、恢复、trace 和 retrieval 导出；PDF 文件级证据见 `submission_artifacts/mineru_cases/`，其中多数 PDF 为合成公开提交样本。新增 `submission_artifacts/public_real_cases/` 使用 IRS、NIST、SEC 和 CDC 官方公开 PDF，补充外部真实文档证据；这些公开样本采用轻量人工标注与文本证据门槛，仍不能被表述为完整 OCR 字符级 benchmark。

## 1. 背景与问题定义

真实语料生产中，PDF、扫描件、行业标准、财报和网页材料往往包含复杂版面、跨页上下文、密集数字、表格和低质量 OCR 场景。单一模型直接抽取容易出现幻觉、漏页、数字错误和不可追溯的问题。

本项目选择的核心问题是：基于 MinerU 构建一个可部署、可复现、可审计的 Data Agent，使其能够把复杂文档解析为结构化结果，并输出质量报告和完整执行日志。该定位对应 MDIC2026「智能进化·Agent 能力评测赛道」中的「数据智能体 Data Agent 构建」赛题，官方要求参赛系统能够理解任务需求、调用工具或模块完成数据处理、生成结构化结果并输出可验证日志。

## 2. 系统设计

系统由六层组成：

1. Task Planner：根据任务描述和文件名推断场景 profile，例如财报、合同/规范、流程图、低质量 OCR，并在 `execution_control.planning_rationale` 中解释 profile、runner、backend、method、语言和恢复策略的选择原因。可选接入 DeepSeek v4-flash 或 ModelScope 上的 `deepseek-ai/DeepSeek-V4-Flash` 执行解析前调度，建议 profile、runner、backend、method、语言、目标 schema、复核重点和恢复策略。
2. MinerU Adapter：支持在线 Agent API 与本地 MinerU CLI 两种后端。在线 API 用于低成本快速验证，本地 CLI 用于保留 Markdown、content list、middle json、layout pdf 等完整 artifact。在线 API 的轻量 Markdown 路径若缺少页级 provenance，会被质量校验明确标注；当检测到本地 CLI 或显式配置 fallback runner 时，系统会自动执行本地 CLI fallback 并择优。
3. Structured Extractor：从 Markdown 与内容块中生成章节、表格、键值对、键值字典、数字事实、日期/建议/异常语义信号和页级溯源摘要。HTML 输入会保留标题层级、段落、列表和表格，避免网页语料被压平成不可复用纯文本。
4. Retrieval Exporter：把解析结果整理为 `retrieval_chunks.jsonl`、`retrieval_manifest.json` 和 `retrieval_quality.json`，便于检索、向量库入库与评审复查。跨页文本不会再合并到第一页；chunk 保留 `page_no` 起始页和 `pages` 覆盖页列表。
5. Quality Validator：检查空结果、编码噪声、页码覆盖、profile 预期、表格合计行等风险。
6. API/CLI Layer：提供命令行、批处理、FastAPI 同步接口和异步 job/polling 接口，便于评审脚本调用和复现实验。

## 3. Agent 执行机制

一次任务的流程如下：

1. 接收输入文件、自然语言任务、profile、MinerU backend。
2. 推断任务类型并生成基础执行计划。
3. 若开启 LLM，先执行 `llm_pre_execution_planning`：模型基于任务、文件后缀、文件大小、当前 runner 和初始 profile 给出调度建议；系统只应用白名单内且未被用户显式锁定的 profile/backend/method/lang 建议，并把应用或忽略原因写入 `execution_control` 和 trace。
4. 对 PDF、图片调用 MinerU 在线 API 或本地 CLI；对 HTML、DOCX 和 PPTX 使用轻量结构化提取器。
5. 读取 MinerU 输出，构造结构化视图，包括 `sections`、`tables`、`key_values`、`key_value_map`、`numeric_facts` 和 `semantic_signals`。
6. 生成检索友好的知识库 chunks，过滤页眉页脚、页码、目录等低价值内容。
7. 运行质量校验；若命中可恢复风险，执行文本清理二次 pass、PDF/图片 OCR 重试，或在在线 API 缺页级 provenance 时执行本地 CLI fallback，并按质量评分择优。若恢复尝试失败，失败尝试会进入 `recovery_decision.attempts` 与 trace，系统保留初始可用结果继续输出。
8. 生成 `result.json`、`summary.md`、`trace.json`。

每一步都会写入 trace，包含步骤状态、时间、工具命令、耗时、stdout/stderr 摘要，满足可追溯性要求。若解析或工具调用失败，系统也会写出失败态 `trace.json`，避免异常链路只停留在控制台错误里。

对于生产化稳定性，系统提供批处理 manifest 入口。批处理中单个任务失败不会中断整批，最终生成 `batch_report.json`，记录每个任务的状态、run id、输出路径、质量评分和错误信息。在线 API 调用对 429、5xx 和网络异常等瞬时错误提供重试，并把重试事件写入工具调用日志。

大模型层采用可选增强设计。没有 `DEEPSEEK_API_KEY` 或 `MODELSCOPE_API_KEY` 时，系统仍能依赖 MinerU 与规则模块完成端到端流程；配置 DeepSeek 官方或 ModelScope 推理入口后，系统会先让 LLM 参与解析前调度，再进行解析后复核。解析前调度的结果保存在 `execution_control` 与 `llm_analysis.pre_execution_plan`，解析后复核保存在 `llm_analysis.post_parse_analysis`。该设计避免评审复现时因密钥或网络问题导致主流程不可用。本提交包已保存 1 个实际启用 ModelScope `deepseek-ai/DeepSeek-V4-Flash` 的案例，见 `submission_artifacts/llm_cases/`；另保存 1 个真实 PDF 的解析前调度 + API-to-CLI fallback recovery 演练，见 `submission_artifacts/recovery_cases/`。后者当前使用离线确定性预调度器和缓存 CLI artifact 回放，不冒充现场 LLM/CLI 全链路。

## 4. MinerU 使用方式

第一阶段推荐使用 MinerU 在线 Agent API 后端，免登录、无需 Token，适合 HeyWhale CPU 环境先跑通 Agent 主流程：

```bash
data-agent run --runner agent-api --input demo.pdf --out runs --task "..." --method auto
```

第二阶段在 GPU 镜像或本地模型资源可用时，使用 `pipeline` backend 运行本地 MinerU CLI，保留更完整的中间结果：

```bash
data-agent run --input demo.pdf --out runs --task "..." --backend pipeline --method auto
```

在和鲸 MinerU GPU 镜像中，可根据资源情况切换为更强后端。项目通过 `MINERU_EXECUTABLE` 和 `MINERU_MODEL_SOURCE` 环境变量适配不同部署环境。

本提交包内已纳入十五类证据：5 个可复跑 HTML/网页 fixture 案例，用于稳定验证 Data Agent 的任务规划、结构化抽取、质量校验、自动恢复、trace 和检索导出；4 个 PDF 文件级本地 MinerU CLI 案例，位于 `submission_artifacts/mineru_cases/`，覆盖低质量扫描件、财报密集数字表、合同/标准条款和流程图文档，均包含 `mineru-cli` 工具调用、页级 provenance、MinerU 中间文件和 retrieval 导出；1 个 CPU 友好的 MinerU 在线 Agent API PDF 案例，位于 `submission_artifacts/agent_api_cases/`，证明无 GPU 条件下也能处理 PDF fixture；1 个真实 PDF 的 recovery 演练，位于 `submission_artifacts/recovery_cases/`，证明 `no_page_provenance` 后可自动 fallback 到 CLI artifact 且 `recovery_decision.executed=true`；2 个 DOCX/PPTX 文件级 native extractor 案例，位于 `submission_artifacts/office_cases/`，覆盖 Word 合规矩阵和 PowerPoint 工作流汇报；4 个挑战 fixture 与人工标注表，位于 `submission_artifacts/challenge_cases/`，覆盖跨页财报、OCR 噪声合同、行业标准矩阵和故障工作流；4 个官方公开真实 PDF 案例，位于 `submission_artifacts/public_real_cases/`，覆盖 IRS W-4、NIST AI RMF 1.0、Microsoft 2024 Annual Report SEC PDF exhibit 和 CDC VIS 使用说明，均保存 source metadata、human labels、trace、result 和 retrieval 导出；1 个 NIST 48 页长文档分片案例，位于 `submission_artifacts/long_document_chunks/public_nist_ai_rmf_full_chunked/`，证明在线 API 20 页上限下可通过 Agent 拆分 page ranges，3/3 分片成功并输出 58 个 retrieval chunks；1 个 LLM-enabled 财报复核案例，位于 `submission_artifacts/llm_cases/case_llm_financial_review/`，包含 `modelscope-llm-preplan completed`、`modelscope-llm completed`、`llm_analysis.enabled=true` 和 `usage_summary.total_tokens=4309` 的结果；1 份带标注评测报告，位于 `submission_artifacts/evaluation/`，覆盖 17 个案例、45 个标注字段、22 条文本证据、11 条数字证据、6 条表格证据、profile 命中、结构门槛、质量门槛、provenance 门槛和 recovery 门槛；1 份稳定性报告，位于 `submission_artifacts/stability/`，汇总 17 个保存案例的 trace 完整性、工具调用、耗时、质量状态、provenance 分布和恢复执行；1 份 API 并发 smoke 报告，位于 `submission_artifacts/api_load_smoke/`，保存 8 请求、并发 4 的本地 FastAPI 接口验证；2 份真实 HTTP loopback 压测报告，位于 `submission_artifacts/http_load_test/` 和 `submission_artifacts/http_load_test_100/`，分别保存 12 请求并发 6 与 100 请求并发 20 的同步/异步混合接口成功记录；1 份成本/速度/质量对比报告，位于 `submission_artifacts/baseline_comparison/`，按 runner 与场景组展示标注通过率、质量、耗时、页级 provenance 和恢复执行；1 份 LLM token/cost 审计报告，位于 `submission_artifacts/llm_cost/`，记录 live LLM token usage，成本估算只在配置价格时计算。当前仍不能宣称已经覆盖真实客户材料的长期泛化评测，也不把本地 loopback 压测包装为外部公网或 GPU 高并发压测。

## 5. 质量控制

当前实现包含以下质量检查：

- 空 Markdown 检查
- 编码噪声/乱码模式检查
- 内容块数量与页码溯源检查
- 在线 Markdown 轻量结果缺失页级 provenance 时输出 `no_page_provenance` 警告；HTML fixture 会标记为 `document_level_provenance` 信息项，不伪装成页级来源
- 财报任务的表格/数字事实检查
- 合同/规范任务的章节结构检查
- 任务显式要求日期、建议、异常/风险时，检查对应语义信号是否存在
- 长文本缺少标题、键值对和表格时提示结构化信号不足
- 表格总计/小计行核验，区分 `numeric_total_verified`、`numeric_total_mismatch` 和 `numeric_total_needs_review`
- 财报案例附带 `human_spot_check.md` 与 `mismatch_drill/`，分别保存样本级人工核对和故意改错触发 `numeric_total_mismatch` 的证据
- MinerU Markdown 中的 HTML `<table>` 表格解析，避免真实 PDF 表格被误判为普通文本
- 质量恢复决策 `recovery_decision`，根据 warning/error、文件类型和 profile 给出重试、人工复核或接受策略
- 自动恢复执行记录 `recovery_decision.attempts`，包括 initial、text_cleanup、ocr_retry 或 cli_fallback 尝试、失败恢复尝试、最终选中的 `selected_attempt` 和初始风险保留字段
- 新运行输出 `extracted.field_evidence`，为键值字段保留 confidence proxy、证据文本和行/页/块级 provenance；若上游提供 bbox，则一并透传

这些检查不会替代人工评审，但能把不可见风险转化为可审计字段。质量状态区分 `pass`、`pass_with_warnings` 和 `needs_review`，避免把存在 warning 的结果包装成完全通过。

## 6. 典型应用价值

- 财报和审计材料：抽取表格、关键数字、合计行和异常提示。
- 合同/行业标准：抽取章节、条款、约束条件和源页。
- 扫描件 OCR：识别低质量文本风险，提示重跑 OCR/VLM。
- 流程/工程资料：保留图像 artifact 和流程性文本。
- 网页语料清洗：把 HTML 转成统一结构化内容块，并保留标题、键值字段、表格和建议/异常线索。

## 7. 可复现性

项目提供：

- `pyproject.toml` 依赖声明
- CLI 与 API 两种调用方式
- 批处理 manifest 与 `batch_report.json`
- 可选 DeepSeek v4-flash / ModelScope 接入，不把 API key 写入日志或输出文件
- LLM 预调度的 `execution_control`，记录 recommended/applied/ignored/resolved 参数
- 带标注评测脚本 `scripts/build_evaluation_report.py` 与标注文件 `examples/evaluation/labels.json`
- 每次运行的 trace 文件
- 失败运行也会保留 trace 文件
- API 输出默认持久化到 `runs/api`，请求结束后仍可查看 `trace_path`、`summary_path` 和 artifact
- API 提供 `/v1/jobs` 与 `/v1/jobs/{job_id}`，支持长任务异步提交和状态轮询
- MinerU 原始输出 artifact 路径
- 单元测试覆盖核心抽取和校验逻辑
- `submission_artifacts/cases/` 中包含 5 个 HTML fixture 案例的输入、结果、trace、summary 和 retrieval 输出
- `submission_artifacts/mineru_cases/` 中包含 4 个 PDF 文件级本地 MinerU CLI 运行证据
- `submission_artifacts/agent_api_cases/` 中包含 1 个 CPU 在线 Agent API PDF 运行证据
- `submission_artifacts/recovery_cases/` 中包含 1 个真实 PDF 的解析前调度与 API-to-CLI fallback 证据，最终 `recovery_decision.executed=true`
- `submission_artifacts/office_cases/` 中包含 2 个 DOCX/PPTX 文件级运行证据
- `submission_artifacts/challenge_cases/` 中包含 4 个挑战 fixture、结果日志和人工标注表
- `submission_artifacts/public_real_cases/` 中包含 4 个官方公开真实 PDF 案例、来源元数据和人工轻量标注
- `submission_artifacts/llm_cases/` 中包含 1 个实际启用 DeepSeek-V4-Flash 的 LLM 运行证据
- `submission_artifacts/evaluation/` 中包含 17 个案例、45 个标注字段、22 条文本证据、11 条数字证据和 6 条表格证据的带标注评测指标
- `submission_artifacts/stability/` 中包含 17 个保存案例的 trace、工具耗时、质量状态和恢复统计
- `submission_artifacts/api_load_smoke/` 中包含 8 请求、并发 4 的本地 FastAPI smoke 报告和对应落盘 artifact
- `submission_artifacts/http_load_test/` 中包含 12 请求、并发 6 的真实 HTTP loopback 压测，混合同步 `/v1/parse` 和异步 `/v1/jobs`
- `submission_artifacts/http_load_test_100/` 中包含 100 请求、并发 20 的真实 HTTP loopback 压测，混合同步 `/v1/parse` 和异步 `/v1/jobs`
- `submission_artifacts/baseline_comparison/` 中包含保存 artifact 的成本/速度/质量分组对比
- `submission_artifacts/llm_cost/` 中包含 LLM token/cost 审计报告
- `docs/BENCHMARK_AND_ROADMAP.md` 中包含外部 baseline 矩阵、真实文档 benchmark 设计和后续 roadmap

## 8. 日志脱敏策略

LLM API key 只从环境变量读取，不写入 `result.json`、`trace.json` 或 summary。DeepSeek/ModelScope 调用失败时，错误摘要会过滤 API key、Bearer token 和 `api_key=` 参数。MinerU 在线 Agent API 的重试事件和下载 URL 会过滤 `token=`、`access_token=`、`signature=`、`X-Amz-*` 等签名字段。提交材料收集脚本会把本机路径替换成 `<PROJECT_ROOT>`、`<USER_HOME>` 或 `<MINERU_ROOT>` 风格占位，避免泄露本地用户目录。
