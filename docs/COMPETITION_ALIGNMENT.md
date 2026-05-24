# 赛题对齐说明

## 0. 指标口径

本项目提交材料中的 `quality.score` 是规则风险分；字段级 precision/recall/F1、文本证据、数字证据和表格证据在 `submission_artifacts/evaluation/` 统计。HTML/网页案例用于复跑 Agent 管线；PDF 文件级 MinerU 证据、Office 证据、公开真实 PDF 证据和长文档分片结果分别放在对应 artifact 目录。

## 1. 官方赛题定位

官方 MDIC2026 页面将本项目对应到「赛道二：智能进化·Agent 能力评测赛道」，赛题名称为「数据智能体 Data Agent 构建」。

该赛题不是单纯比拼 PDF 解析准确率，而是要求构建一个能理解任务需求、调用工具或模块完成数据处理、生成结构化结果并输出可验证日志的智能体。处理对象覆盖 PDF、Word、PPT、HTML 等文档或网页，重点关注单一多模态模型难以稳定解决的复杂文档解析问题，例如财务报表数字解析、跨页指代消解、复杂图表与工程图解析、低质量文档处理等。

官方页面同时说明，参赛需使用 MinerU 工具链，范围包括 SaaS 端与开源项目。因此，本项目采用 CLI-first 策略：所有核心能力通过 `data-agent` 命令复现；PDF 后端可在命令行中选择在线 Agent API 或本地 MinerU CLI，便于在不同资源条件下运行。

官方入口：https://mineru.net/MDIC2026

## 2. 本项目与赛题要求的对应关系

| 赛题要求 | 本项目实现 |
| --- | --- |
| 理解任务需求 | `TaskPlanner` 根据自然语言任务、文件类型和场景 profile 生成基础计划；开启 LLM 时，DeepSeek/ModelScope 会在解析前输出任务理解、目标 schema、profile/runner/backend/method/lang 建议、复核重点和恢复策略 |
| 调用工具或模块 | `data-agent run` 在 CLI 中调度 `MinerUAgentAPIRunner` 在线 API、`MinerURunner` 本地 MinerU CLI 或 HTML/DOCX/PPTX 轻量结构化模块；质量异常时可执行 text cleanup、OCR retry 或 CLI fallback；LLM 预调度建议会通过安全白名单进入 `execution_control.applied` |
| 完成数据处理 | 抽取 Markdown、内容块、章节、表格、键值对、键值字典、数字事实、日期/建议/异常信号、页级或文档级线索和 `recovery_decision` |
| 生成结构化结果 | 每次运行生成 `result.json` 与 `retrieval_chunks.jsonl`，供程序、评审脚本或检索入库流程直接消费；HTML/DOCX/PPTX 输入保留标题、段落、列表、表格和 slide-level provenance；新运行额外输出 `field_evidence`，记录字段 confidence proxy、证据文本和行/页/块级 provenance |
| 输出可验证日志 | 每次运行生成 `trace.json`，记录执行步骤、工具调用、耗时、状态、重试事件、LLM 预调度、自动恢复尝试和错误摘要；失败运行也会落 trace；提交包内包含 5 个 HTML fixture artifact、4 个 PDF 文件级 CLI artifact、1 个 Agent API PDF artifact、1 个 API-to-CLI recovery artifact、2 个 Office 文件级 artifact、4 个挑战 fixture、4 个官方公开真实 PDF artifact、1 个 LLM-enabled artifact、1 份带标注评测报告和 1 份 artifact 级稳定性报告 |
| 面向复杂文档 | 内置财报、合同/规范、低质量 OCR、流程/工程资料、HTML 语料等 profile |
| 可部署可复现 | 提供 CLI、批处理、live tool-calling CLI、单元测试、提交压缩包、HeyWhale/本地 MinerU 运行建议、`docs/CLI_CONTRACT.md` CLI 合约、`docs/ENGINEERING_EVIDENCE.md` 扣分点证据矩阵、`scripts/run_adaptive_planning_cases.py` 自适应规划证据脚本、`scripts/build_evaluation_report.py` 评测脚本、`scripts/build_stability_report.py` 稳定性摘要脚本和 `scripts/build_baseline_comparison.py` 成本/速度/质量对比脚本；FastAPI/Docker 仅作为可选 HTTP wrapper 材料保留 |

## 3. 为什么先用在线 API

在线 API 适合作为第一阶段后端：

- 不依赖本地 GPU，CPU 资源也能跑通主流程。
- 免去模型下载和镜像权限问题，更适合在资源不稳定时保证可复现。
- 能输出 Markdown，足够支撑 Agent 的结构化抽取、质量校验和日志生成。
- 已在本地完成验证，生成了 `result.json`、`trace.json`、`summary.md`。

在线 API 与本地 CLI 的分工：

- 轻量 API 主要返回 Markdown，缺少本地 MinerU CLI 可保留的 layout、middle、model、可视化 PDF 等中间 artifact。
- 文件大小、页数和频率通常会受到在线服务限制。
- 面对复杂工程图、密集表格和大文档，最终版本仍应优先在 MinerU 镜像或 GPU 资源上运行本地 CLI 后端。

因此，本项目的比赛路线是：

1. `--runner agent-api`：先跑通 Data Agent 主流程，保证 CPU 环境可演示。轻量结果若缺少页级 provenance，会在质量报告中标注；若检测到本地 CLI 或显式配置了 fallback CLI，系统会自动尝试本地 MinerU CLI。
2. `--runner cli`：在 MinerU 镜像或 GPU 资源可用时补齐中间 artifact 和页级来源。
3. 技术报告中分别说明两种后端的输出范围。

当前提交材料按以下目录组织：

| 目录 | 内容 |
| --- | --- |
| `submission_artifacts/mineru_cases/` | 4 个 PDF 文件级本地 `mineru-cli` 案例，覆盖低质量扫描件、财报密集数字表、合同/标准条款和流程图文档 |
| `submission_artifacts/agent_api_cases/` | 1 个 CPU 友好的在线 Agent API PDF 案例，记录轻量路径和 provenance warning |
| `submission_artifacts/recovery_cases/` | 真实 PDF 解析前调度后先走在线 API，命中 `no_page_provenance` 后 fallback 到 CLI artifact，`recovery_decision.executed=true` |
| `submission_artifacts/office_cases/` | 2 个 DOCX/PPTX 文件级 native extractor 案例 |
| `submission_artifacts/challenge_cases/` | 4 个挑战 fixture 与人工标注表，覆盖跨页财报、OCR 噪声合同、行业标准矩阵和故障工作流 |
| `submission_artifacts/adaptive_cases/` | 同一财报输入在增长排名和异常证据任务下生成不同 `adaptive_decision`、`target_schema`、`post_processors` 和 `task_result` |
| `submission_artifacts/public_real_cases/` | IRS、NIST、SEC、CDC 4 份官方公开 PDF，保存 source metadata、human labels、trace、result 和 retrieval 导出 |
| `submission_artifacts/long_document_chunks/public_nist_ai_rmf_full_chunked/` | NIST 48 页官方公开 PDF 按 20 页 API 限制拆为 3 个 page range，3/3 成功，58 个 retrieval chunks |
| `submission_artifacts/evaluation/` | 17 个案例、45 个字段、22 条文本证据、11 条数字证据、6 条表格证据、字段 precision/recall/F1 和多类门槛指标 |
| `submission_artifacts/stability/`、`submission_artifacts/http_load_test_100/`、`submission_artifacts/baseline_comparison/` | trace 完整性、工具耗时、100 请求本地 HTTP loopback、runner 分组对比和 recovery 统计 |

## 4. 评审展示重点

本项目提交时应突出以下内容：

- 不是「调用一次 MinerU」：项目增加任务规划、结构化抽取、质量控制和日志。
- 不是「只做文档转 Markdown」：输出包含机器可读 JSON、人工摘要和 trace。
- 不是「只能展示 Demo」：额外输出可入库的 `retrieval_chunks.jsonl`、`retrieval_manifest.json` 和 `retrieval_quality.json`。
- 不是「没有指标的 Demo」：提供 `evaluation_metrics.json` 和 `evaluation_metrics.md`，可复查 45 个标注字段、字段 precision/recall/F1、22 条文本证据、11 条数字证据、6 条表格证据和结构/质量/provenance/recovery 门槛。
- 不是「单场景 Demo」：围绕赛题痛点覆盖财报数字、低质量 OCR、合同/规范结构、HTML 语料等多类任务。
- 风险不只写在文档里：质量校验会把空结果、乱码、页码缺失、数字/表格风险写入输出。
- 资源策略清楚：CPU 可跑在线 API 主流程，GPU/MinerU 镜像可跑 CLI artifact。
