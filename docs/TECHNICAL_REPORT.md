# Technical Report

## 0. 指标口径

本文中的 `quality.score` 是运行风险分：它记录空结果、乱码、页级 provenance 缺失、profile 预期缺失、合计行不一致等规则检查结果。字段级 precision/recall/F1、文本证据、数字证据和表格证据由 `submission_artifacts/evaluation/` 单独统计。HTML/网页 fixture 用于复跑管线和日志；PDF CLI、Office、公开真实 PDF、长文档分片和 LLM 案例分别放在对应 artifact 目录。

## 1. 背景与问题定义

真实语料生产中，PDF、扫描件、行业标准、财报和网页材料往往包含复杂版面、跨页上下文、密集数字、表格和低质量 OCR 场景。单一模型直接抽取容易出现幻觉、漏页、数字错误和不可追溯的问题。

本项目要解决的问题是：基于 MinerU 构建一个文档处理 Data Agent，把复杂文档解析为结构化结果，并输出质量报告和执行日志。该定位对应 MDIC2026「智能进化·Agent 能力评测赛道」中的「数据智能体 Data Agent 构建」赛题，官方要求参赛系统能够理解任务需求、调用工具或模块完成数据处理、生成结构化结果并输出可验证日志。

## 2. 系统设计

系统由六层组成：

1. Task Planner：根据任务描述和文件名推断场景 profile，例如财报、合同/规范、流程图、低质量 OCR，并在 `execution_control.planning_rationale` 中解释 profile、runner、backend、method、语言和恢复策略的选择原因。可选接入 DeepSeek v4-flash 或 ModelScope 上的 `deepseek-ai/DeepSeek-V4-Flash` 执行解析前调度，建议 profile、runner、backend、method、语言、目标 schema、复核重点和恢复策略。新运行还会写入 `execution_control.agent_action_plan`，记录子任务、候选工具、动态选择和 replan triggers。
2. MinerU Adapter：支持在线 Agent API 与本地 MinerU CLI 两种后端。在线 API 用于 CPU 环境快速验证，本地 CLI 用于保留 Markdown、content list、middle json、layout pdf 等 artifact。在线 API 的轻量 Markdown 路径若缺少页级 provenance，会被质量校验标注；当检测到本地 CLI 或显式配置 fallback runner 时，系统会自动执行本地 CLI fallback 并择优。
3. Structured Extractor：从 Markdown 与内容块中生成章节、表格、键值对、键值字典、数字事实、日期/建议/异常语义信号和页级溯源摘要。HTML 输入会保留标题层级、段落、列表和表格，避免网页语料被压平成不可复用纯文本。
4. Retrieval Exporter：把解析结果整理为 `retrieval_chunks.jsonl`、`retrieval_manifest.json` 和 `retrieval_quality.json`，便于检索、向量库入库与评审复查。跨页文本不会再合并到第一页；chunk 保留 `page_no` 起始页和 `pages` 覆盖页列表。
5. Quality Validator：检查空结果、编码噪声、页码覆盖、profile 预期、表格合计行等风险。
6. Recovery Orchestrator：`src/mineru_data_agent/recovery.py` 集中处理严格页级来源门槛、质量择优、恢复计划、LLM 复核影响、attempt 摘要和文本清理，主 `agent.py` 只负责按计划调用解析/恢复步骤。
7. CLI Layer：提供 `data-agent run`、`data-agent batch` 和 `data-agent agent-run` 三个评审入口；FastAPI 同步/异步接口保留为可选本地 wrapper，不是主要交付面。

## 3. Agent 执行机制

一次任务的流程如下：

1. 接收输入文件、自然语言任务、profile、MinerU backend。
2. 推断任务类型并生成基础执行计划。
3. 若开启 LLM，先执行 `llm_pre_execution_planning`：模型基于任务、文件后缀、文件大小、当前 runner 和初始 profile 给出调度建议；系统只应用白名单内且未被用户显式锁定的 profile/backend/method/lang 建议，并把应用或忽略原因写入 `execution_control` 和 trace。
4. 执行 `agent_task_decomposition`，生成子任务图、selected tools、dynamic choices、replan triggers 和单次运行上下文策略。
5. 对 PDF、图片调用 MinerU 在线 API 或本地 CLI；对 HTML、DOCX 和 PPTX 使用轻量结构化提取器。
6. 读取 MinerU 输出，构造结构化视图，包括 `sections`、`tables`、`key_values`、`key_value_map`、`numeric_facts`、`semantic_signals` 和 `cross_page_references`。轻量提取层会额外吸收两列表格键值、多行键值、标题后紧邻段落和简单跨页引用。
7. 运行质量校验；若启用 LLM，先执行解析后复核，把 `risk_findings` 与 `recovery_suggestions` 写入 `llm_analysis.post_parse_analysis`，并允许白名单内的 recovery suggestion 进入 runtime recovery plan。
8. 若命中可恢复风险，执行文本清理二次 pass、PDF/图片 OCR 重试，或在在线 API 缺页级 provenance 时执行本地 CLI fallback，并按质量评分择优。若恢复尝试失败，失败尝试会进入 `recovery_decision.attempts` 与 trace，系统保留初始可用结果继续输出。
9. 执行 `agent_replan_after_quality`，把质量 issue code 映射到候选恢复动作，记录已尝试动作、最终选择原因和剩余风险的下一步动作。
10. 生成检索友好的知识库 chunks，过滤页眉页脚、页码、目录等低价值内容。
11. 若启用 LLM，把解析后复核的 risk/suggestion 汇总为 `recovery_decision.llm_quality_decision`。warning/error 级风险会改变或补充最终 recovery 决策。
12. 生成 `result.json`、`summary.md`、`trace.json`。

每一步都会写入 trace，包含步骤状态、时间、工具命令、耗时、stdout/stderr 摘要，满足可追溯性要求。若解析或工具调用失败，系统也会写出失败态 `trace.json`，避免异常链路只停留在控制台错误里。

对于生产化稳定性，系统提供批处理 manifest 入口。批处理中单个任务失败不会中断整批，最终生成 `batch_report.json`，记录每个任务的状态、run id、输出路径、质量评分和错误信息。在线 API 调用对 429、5xx 和网络异常等瞬时错误提供重试，并把重试事件写入工具调用日志。

大模型层默认关闭。配置 DeepSeek 官方或 ModelScope 推理入口后，稳定主路径可以先让 LLM 参与解析前调度，再进行解析后复核。解析前调度的结果保存在 `execution_control` 与 `llm_analysis.pre_execution_plan`，解析后复核保存在 `llm_analysis.post_parse_analysis`。真实 tool-calling Agent 作为 CLI 工具 `data-agent agent-run` 暴露，不新增 HTTP live-agent endpoint；它只从环境变量读取 provider key/base URL，并输出 `result.json`、`live_agent_trace.json` 和 `live_agent_summary.md`。本提交包已保存 1 个实际启用 ModelScope `deepseek-ai/DeepSeek-V4-Flash` 的预调度/复核案例，见 `submission_artifacts/llm_cases/`；另有 `submission_artifacts/agent_live_cases/` 记录 8 次 ModelScope Qwen3 tool-calling 尝试，其中 4 次到达 finalize/tool-call completion，人工复核后 2 次计为 answer-quality pass、2 次保留为质量存疑的 live tool-call trace；另保存 1 个真实 PDF 的解析前调度 + API-to-CLI fallback recovery 演练，见 `submission_artifacts/recovery_cases/`。`submission_artifacts/agent_decision_cases/` 是离线决策回归材料，使用本地 scripted decision client 检查 pre/post decision hook schema；它不替代 live provider 证据，其中 token 数也不作为真实用量。

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

本提交包内已纳入以下材料：

| 类别 | 位置 | 内容 |
| --- | --- | --- |
| HTML/网页 fixture | `submission_artifacts/cases/` | 5 个可复跑案例，覆盖财报、低质量 OCR、合同、流程说明和网页巡检 |
| PDF CLI | `submission_artifacts/mineru_cases/` | 4 个本地 MinerU CLI 文件级案例，保留工具调用、页级 provenance、MinerU 中间文件和 retrieval 导出 |
| 在线 API PDF | `submission_artifacts/agent_api_cases/` | 1 个 CPU 环境 PDF 案例，记录在线 API 的轻量 Markdown 路径和 provenance warning |
| Recovery | `submission_artifacts/recovery_cases/` | 真实 PDF 先走在线 API，命中 `no_page_provenance` 后切到 CLI artifact，最终 `recovery_decision.executed=true` |
| Failure/recovery fault injection | `submission_artifacts/failure_recovery_cases/` | 5 个 controlled 负样本/恢复样本，覆盖 text cleanup、OCR retry 成功/失败、strict provenance failure 和 numeric mismatch |
| Office | `submission_artifacts/office_cases/` | 2 个 DOCX/PPTX native extractor 案例 |
| 挑战样本 | `submission_artifacts/challenge_cases/` | 4 个跨页财报、OCR 噪声合同、行业标准矩阵和故障工作流样本，附人工标注表 |
| 自适应规划 | `submission_artifacts/adaptive_cases/` | 同一财报输入在增长排名与异常证据任务下生成不同 intents、schema、post-processors 和 `task_result` |
| Agent decision regression | `submission_artifacts/agent_decision_cases/` | 5 个本地离线案例展示子任务拆解、动态工具选择、质量后 replan 和 scripted decision hooks |
| 公开真实 PDF | `submission_artifacts/public_real_cases/` | IRS、NIST、SEC、CDC 4 份官方公开 PDF，保存 source metadata、human labels、trace、result 和 retrieval 导出 |
| 长文档分片 | `submission_artifacts/long_document_chunks/public_nist_ai_rmf_full_chunked/` | NIST AI RMF 48 页拆成 3 个 page range，3/3 成功，58 个 retrieval chunks |
| LLM case | `submission_artifacts/llm_cases/case_llm_financial_review/` | ModelScope DeepSeek-V4-Flash 预调度和复核，`usage_summary.total_tokens=4309` |
| LLM impact | `submission_artifacts/llm_impact/` | 保存的规则运行与 LLM-enabled 运行对比，列出决策点、应用/忽略项、recovery suggestion 和 token |
| Evaluation | `submission_artifacts/evaluation/` | 17 个案例、45 个字段、22 条文本证据、11 条数字证据、6 条表格证据和字段级 precision/recall/F1 |
| Coverage | `submission_artifacts/coverage/` | coverage.py 对 `src/mineru_data_agent` 的本地 pytest 行覆盖率 |
| Retrieval validation | `submission_artifacts/retrieval_validation/` | chunk schema、重复率、空文本和 lightweight lexical query smoke；不等同 embedding benchmark |
| Agent value | `submission_artifacts/agent_value/` | 统计 Agent 层相对 parser Markdown/content_list 增加的 schema、质量、恢复、field evidence、retrieval 和决策模式字段；不等同 parser 准确率 benchmark |
| Stability/API/Tradeoff | `submission_artifacts/stability/`、`submission_artifacts/http_load_test_100/`、`submission_artifacts/baseline_comparison/`、`submission_artifacts/llm_cost/` | trace 完整性、工具耗时、100 请求本地 HTTP loopback、runner 分组对比和 LLM token 审计 |
| Artifact index | `submission_artifacts/ARTIFACTS_INDEX.md` | 提交 artifact 总导航，列出各目录 result/trace 数量和主报告 |

## 5. 质量控制

当前实现包含以下质量检查：

- 空 Markdown 检查
- 编码噪声/乱码模式检查
- 内容块数量与页码溯源检查
- 在线 Markdown 轻量结果缺失页级 provenance 时输出 `no_page_provenance` 警告；HTML fixture 会标记为 `document_level_provenance` 信息项，不伪装成页级来源
- 审计型任务可启用 `--strict-page-provenance` / API `strict_page_provenance=true`；PDF/image 最终仍缺页级 provenance 时，结果保留但标为 `needs_review` 和 `strict_page_provenance_failed`
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
- CLI-first 调用方式：`data-agent run`、`data-agent batch`、`data-agent agent-run`
- 批处理 manifest 与 `batch_report.json`
- 可选 DeepSeek v4-flash / ModelScope 接入，不把 API key 写入日志或输出文件
- LLM 预调度的 `execution_control`，记录 recommended/applied/ignored/resolved 参数
- Agent action plan 的 `execution_control.agent_action_plan`，记录子任务、工具选择和 replan triggers
- Agent action plan 的 `state_machine`，记录条件 DAG、质量触发边、runner/method 变化和恢复 loop policy
- Runtime recovery plan 的 `execution_control.runtime_recovery_plan`，记录由 action plan、质量问题和 LLM recovery suggestions 共同筛出的恢复动作；自动恢复按这个计划执行或跳过
- 质量后再规划的 `execution_control.replan_after_quality`，记录 issue code 到恢复动作的映射和选择原因
- 严格来源门槛的 `execution_control.strict_page_provenance`，记录是否要求页级来源、是否适用于当前文件类型、最终是否满足
- 带标注评测脚本 `scripts/build_evaluation_report.py` 与标注文件 `examples/evaluation/labels.json`
- 每次运行的 trace 文件
- 失败运行也会保留 trace 文件
- 可选 HTTP wrapper 输出默认持久化到 `runs/api`，请求结束后仍可查看 `trace_path`、`summary_path` 和 artifact
- 可选 HTTP wrapper 提供 `/v1/jobs` 与 `/v1/jobs/{job_id}`，支持长任务异步提交和状态轮询
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
- `submission_artifacts/agent_decision_cases/` 中包含 5 个本地 Agent decision regression 案例，用 scripted decision client 离线复现 pre/post decision hook schema
- `submission_artifacts/coverage/` 中包含本地 pytest 对 `src/mineru_data_agent` 的 coverage.py 行覆盖率报告
- `submission_artifacts/llm_impact/` 中包含保存的规则运行与 LLM-enabled 运行对比
- `submission_artifacts/evaluation/` 中包含 17 个案例、45 个标注字段、22 条文本证据、11 条数字证据、6 条表格证据、字段 precision/recall/F1 和 failed-check 分布的带标注评测指标
- `submission_artifacts/stability/` 中包含 17 个保存案例的 trace、工具耗时、质量状态和恢复统计
- `submission_artifacts/api_load_smoke/`、`submission_artifacts/http_load_test/` 和 `submission_artifacts/http_load_test_100/` 保留为可选 HTTP wrapper 的二级工程证据；CI 现在以 CLI smoke 作为主门禁
- `submission_artifacts/baseline_comparison/` 中包含保存 artifact 的成本/速度/质量分组对比
- `submission_artifacts/agent_value/` 中包含 Agent 层增量字段和决策模式分布，明确区分 deterministic、offline scripted、controlled fault injection 和 saved live LLM trace
- `submission_artifacts/llm_cost/` 中包含 LLM token/cost 审计报告
- `docs/BENCHMARK_AND_ROADMAP.md` 中包含外部 baseline 矩阵、真实文档 benchmark 设计和后续 roadmap

## 8. 日志脱敏策略

LLM API key 只从环境变量读取，不写入 `result.json`、`trace.json` 或 summary。DeepSeek/ModelScope 调用失败时，错误摘要会过滤 API key、Bearer token 和 `api_key=` 参数。MinerU 在线 Agent API 的重试事件和下载 URL 会过滤 `token=`、`access_token=`、`signature=`、`X-Amz-*` 等签名字段。提交材料收集脚本会把本机路径替换成 `<PROJECT_ROOT>`、`<USER_HOME>` 或 `<MINERU_ROOT>` 风格占位，避免泄露本地用户目录。
