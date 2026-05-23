# 赛题对齐说明

## 1. 官方赛题定位

官方 MDIC2026 页面将本项目对应到「赛道二：智能进化·Agent 能力评测赛道」，赛题名称为「数据智能体 Data Agent 构建」。

该赛题不是单纯比拼 PDF 解析准确率，而是要求构建一个能理解任务需求、调用工具或模块完成数据处理、生成结构化结果并输出可验证日志的智能体。处理对象覆盖 PDF、Word、PPT、HTML 等文档或网页，重点关注单一多模态模型难以稳定解决的复杂文档解析问题，例如财务报表数字解析、跨页指代消解、复杂图表与工程图解析、低质量文档处理等。

官方页面同时说明，参赛需使用 MinerU 工具链，范围包括 SaaS 端与开源项目。因此，本项目采用「在线 Agent API 快速闭环 + 本地 MinerU CLI 完整 artifact」的双后端策略，符合参赛要求，也便于在不同资源条件下复现。

官方入口：https://mineru.net/MDIC2026

## 2. 本项目与赛题要求的对应关系

| 赛题要求 | 本项目实现 |
| --- | --- |
| 理解任务需求 | `TaskPlanner` 根据自然语言任务、文件类型和场景 profile 生成执行计划；已补 1 个 ModelScope DeepSeek-V4-Flash 证据，用于输出任务理解、建议 schema、复核重点和恢复建议 |
| 调用工具或模块 | `MinerUAgentAPIRunner` 调用在线 API；`MinerURunner` 调用本地 MinerU CLI；HTML/DOCX/PPTX 使用轻量结构化模块；在线 API 支持瞬时错误重试；质量异常时可执行 text cleanup 或 OCR retry |
| 完成数据处理 | 抽取 Markdown、内容块、章节、表格、键值对、键值字典、数字事实、日期/建议/异常信号、页级或文档级线索和 `recovery_decision` |
| 生成结构化结果 | 每次运行生成 `result.json` 与 `retrieval_chunks.jsonl`，供程序、评审脚本或检索入库流程直接消费；HTML/DOCX/PPTX 输入保留标题、段落、列表、表格和 slide-level provenance |
| 输出可验证日志 | 每次运行生成 `trace.json`，记录执行步骤、工具调用、耗时、状态、重试事件、自动恢复尝试和错误摘要；失败运行也会落 trace；提交包内包含 5 个 HTML fixture artifact、4 个 PDF 文件级 CLI artifact、1 个 Agent API PDF artifact、2 个 Office 文件级 artifact 和 1 个 LLM-enabled artifact |
| 面向复杂文档 | 内置财报、合同/规范、低质量 OCR、流程/工程资料、HTML 语料等 profile |
| 可部署可复现 | 提供 CLI、批处理、FastAPI、单元测试、提交压缩包和 HeyWhale 部署建议 |

## 3. 为什么先用在线 API

在线 API 适合作为第一阶段演示后端：

- 不依赖本地 GPU，CPU 资源也能跑通主流程。
- 免去模型下载和镜像权限问题，更适合在资源不稳定时保证可复现。
- 能输出 Markdown，足够支撑 Agent 的结构化抽取、质量校验和日志生成。
- 已在本地完成端到端验证，生成了 `result.json`、`trace.json`、`summary.md`。

但在线 API 不是最终能力上限：

- 轻量 API 主要返回 Markdown，缺少本地 MinerU CLI 可保留的 layout、middle、model、可视化 PDF 等完整中间 artifact。
- 文件大小、页数和频率通常会受到在线服务限制。
- 面对复杂工程图、密集表格和大文档，最终版本仍应优先在 MinerU 镜像或 GPU 资源上运行本地 CLI 后端。

因此，本项目的比赛路线是：

1. `--runner agent-api`：先跑通 Data Agent 主流程，保证 CPU 环境可演示。轻量结果若缺少页级 provenance，会在质量报告中标注。
2. `--runner cli`：在 MinerU 镜像或 GPU 资源可用时补齐完整 artifact，增强评审说服力。
3. 在技术报告中明确两种后端的边界，避免把在线 API 的轻量结果包装成完整本地解析能力。

当前已补充 4 个 PDF 文件级本地 `mineru-cli` 证据，路径为 `submission_artifacts/mineru_cases/`。它们覆盖低质量扫描件、财报密集数字表、合同/标准条款和流程图文档，能够证明 CLI 后端、页级 provenance、HTML 表格解析、图像 artifact 和 retrieval 导出可用。另补 1 个 CPU 友好的在线 Agent API PDF 证据，路径为 `submission_artifacts/agent_api_cases/`，用于证明无 GPU 条件下也能跑通真实 PDF 主流程；该路径不冒充本地 CLI 的完整页级 artifact，缺少页级 provenance 时会在质量报告中显式标注。再补 2 个 DOCX/PPTX 文件级 native extractor 证据，路径为 `submission_artifacts/office_cases/`，用于覆盖 Word/PPT 结构化处理。上述样本仍不能代表真实客户材料的长期泛化评测。

## 4. 评审展示重点

本项目提交时应突出以下内容：

- 不是「调用一次 MinerU」：核心价值在于任务规划、结构化抽取、质量控制和可审计日志。
- 不是「只做文档转 Markdown」：输出包含机器可读 JSON、人工摘要和 trace。
- 不是「只能展示 Demo」：额外输出可入库的 `retrieval_chunks.jsonl`、`retrieval_manifest.json` 和 `retrieval_quality.json`。
- 不是「单场景 Demo」：围绕赛题痛点覆盖财报数字、低质量 OCR、合同/规范结构、HTML 语料等多类任务。
- 不隐藏失败和风险：质量校验会把空结果、乱码、页码缺失、数字/表格风险显式写入输出。
- 资源策略清楚：CPU 可跑在线 API 闭环，GPU/MinerU 镜像可跑完整 CLI artifact。
