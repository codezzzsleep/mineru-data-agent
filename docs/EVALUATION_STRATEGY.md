# 评分对齐与优化策略

赛题页显示，赛道二满分 100 分，评审分为五个维度。本项目按评分权重组织功能和提交材料。

## 1. 评分维度映射

| 官方评分维度 | 分值 | 本项目对应能力 | 当前状态 | 下一步优化 |
| --- | ---: | --- | --- | --- |
| 复杂文档理解与结构化处理能力 | 20 | MinerU 解析、Markdown/内容块读取、章节/表格/键值/数字事实抽取、HTML 表格解析、DOCX/PPTX 结构化、质量校验、知识库 chunks、带标注字段和文本证据评测 | 已有 5 个 HTML fixture artifact + 4 个 PDF 文件级 CLI artifact + 1 个 Agent API PDF artifact + 1 个 recovery artifact + 2 个 Office 文件级 artifact + 4 个挑战 fixture + 4 个官方公开真实 PDF artifact + 17 案例评测指标 | 补更多扫描版真实文件、复杂图表和更细粒度人工标注 |
| 难点场景攻克与技术创新性 | 15 | 面向财报数字、低质量 OCR、行业标准、工程流程、网页清洗等 profile 的任务化处理 | 已有案例证据，并新增 45 个标注字段、22 条文本证据、11 条数字证据、6 条表格证据和 2 个 recovery gate 的提交级指标；外部真实样本已覆盖 IRS/NIST/SEC/CDC，但标注仍是轻量级 | 主攻财报数字或低质量 OCR，加入表格逐格/字段级标注集 |
| Agent 任务规划与自动执行能力 | 30 | 任务 profile 推断、自适应 task intents、动态 target schema、任务级 post-processors、LLM 解析前调度、LLM 解析后质量决策、执行计划、工具调用、在线 API/本地 CLI 双后端、native Office/HTML 分支、API-to-CLI fallback、严格页级来源门槛、自动恢复尝试、恢复失败降级保留初始结果、批处理 manifest、失败不中断 | 已有可复跑证据；`submission_artifacts/adaptive_cases/` 记录同一输入在增长排名与异常证据任务下生成不同 `adaptive_decision` 和 `task_result`；`submission_artifacts/agent_decision_cases/` 是离线决策回归材料，不算 live LLM 证据；LLM 可在解析前建议 profile/backend/method/lang/schema/recovery policy，新运行会把解析后风险写入 `recovery_decision.llm_quality_decision`；真实 PDF recovery artifact 中 `executed=true` | 用真实 key 扩展到 10 个 LLM on/off 对比案例和真实 CLI 全链路 fallback |
| 系统稳定性与工程可复现性 | 20 | CLI 命令、失败 trace、trace、batch_report、部署文档、CLI 合约、测试、覆盖率、提交压缩包、案例 artifact、稳定性报告、长文档分片执行；FastAPI/Docker 仅作为可选 wrapper 材料 | 已在 HeyWhale CPU 环境验证；CI 主门禁已改为 CLI smoke；`submission_artifacts/stability/` 汇总 17 个保存案例的 trace、工具耗时、质量状态和恢复统计；`submission_artifacts/long_document_chunks/` 保存 NIST 48 页在线 API 分片执行结果；`submission_artifacts/coverage/` 保存本地 pytest 行覆盖率；API/HTTP loopback 压测作为二级工程证据保留 | 补真实 GPU CLI pages-per-second 或更大规模 CLI 批处理压测 |
| 代码开源共享与产业生态价值 | 15 | 可开源项目结构、CLI 合约、检索导出 JSONL、案例报告、原创性边界说明、MIT License、开源发布清单 | 已创建公开 GitHub repo：https://github.com/codezzzsleep/mineru-data-agent | 记录 commit hash，补演示视频/PPT |

## 2. 当前项目主线

项目主线应表述为：

> 基于 MinerU 的 CLI-first 文档处理 Data Agent。系统通过 `data-agent` 命令根据任务目标选择在线 API 或本地 CLI 后端，生成结构化结果、质量报告、可追溯日志和检索入库 chunks。

该表述能同时覆盖赛题页中的三类任务：

- 数据理解与结构化处理：`result.json` 与 `retrieval_chunks.jsonl`
- 复杂任务规划与自动执行：`plan`、`execution_control.adaptive_decision`、`extracted.task_result`、`trace.json`、`batch_report.json`
- 系统稳定性与综合能力：CLI、测试、部署说明、失败记录；HTTP API 仅作为可选 wrapper

## 3. 优先级判断

后续优化优先级：

1. 继续补真实文件证据：当前已补财报 PDF、合同 PDF、流程图 PDF、低质量扫描件、DOCX、PPTX、recovery 演练、挑战 fixture 和 4 个官方公开真实 PDF；下一步优先补扫描版真实文件、复杂图表样本和更细粒度人工标注。
2. 补工程稳定性数据：当前已有保存 artifact 的稳定性与工具耗时报告、CI CLI smoke、NIST 48 页在线 API 分片长文档证据，以及作为二级材料保留的本地 HTTP wrapper 压测；下一步补真实 GPU CLI pages-per-second 或大规模 CLI 批处理压测。
3. 扩展大模型增强：当前 LLM 已参与解析前 profile/method/backend/lang 调度，并能把 fallback policy 写入执行计划；新运行还会把解析后风险写入 `recovery_decision.llm_quality_decision`。当前 5 个 agent decision pack 只作为离线回归，不作为 live LLM 证据。下一步用真实 key 复跑 10 个 LLM on/off 对比案例。
4. 强化一个主攻难点场景：建议优先选择财报密集数字或低质量 OCR。

不建议把精力分散到大量 UI 或大型模型微调上。赛题页更看重 Agent 的任务拆解、工具调用、可复现和真实场景验证。
