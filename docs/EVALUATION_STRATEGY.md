# 评分对齐与优化策略

赛题页显示，赛道二满分 100 分，评审分为五个维度。本项目按评分权重组织功能和提交材料。

## 1. 评分维度映射

| 官方评分维度 | 分值 | 本项目对应能力 | 当前状态 | 下一步优化 |
| --- | ---: | --- | --- | --- |
| 复杂文档理解与结构化处理能力 | 20 | MinerU 解析、Markdown/内容块读取、章节/表格/键值/数字事实抽取、HTML 表格解析、DOCX/PPTX 结构化、质量校验、知识库 chunks、带标注字段和文本证据评测 | 已实现并有 5 个 HTML fixture artifact + 4 个 PDF 文件级 CLI artifact + 1 个 Agent API PDF artifact + 1 个 recovery artifact + 2 个 Office 文件级 artifact + 4 个挑战 fixture + 4 个官方公开真实 PDF artifact + 17 案例评测指标 | 补更多扫描版真实文件、复杂图表和更细粒度人工标注 |
| 难点场景攻克与技术创新性 | 15 | 面向财报数字、低质量 OCR、行业标准、工程流程、网页清洗等 profile 的任务化处理 | 已有案例证据，并新增 39 个标注字段、22 条文本证据和 2 个 recovery gate 的提交级指标；外部真实样本已覆盖 IRS/NIST/SEC/CDC，但标注仍是轻量级 | 主攻财报数字或低质量 OCR，加入表格逐格/字段级标注集 |
| Agent 任务规划与自动执行能力 | 30 | 任务 profile 推断、LLM 解析前调度、执行计划、工具调用、在线 API/本地 CLI 双后端、native Office/HTML 分支、API-to-CLI fallback、自动恢复尝试、恢复失败降级保留初始结果、批处理 manifest、失败不中断 | 已有可复跑证据；LLM 可在解析前建议 profile/backend/method/lang/schema/recovery policy，并有真实 PDF recovery artifact 证明 `executed=true` | 让 LLM 进一步参与二次校验规则生成和真实 CLI 全链路 fallback |
| 系统稳定性与工程可复现性 | 20 | CLI、FastAPI、失败 trace 返回、trace、batch_report、部署文档、测试、提交压缩包、案例 artifact | 已补强并在 HeyWhale CPU 环境验证；API 失败响应会返回 trace 路径 | 补长文档/高并发稳定性记录 |
| 代码开源共享与产业生态价值 | 15 | 可开源项目结构、检索导出 JSONL、API 文档、案例报告、原创性边界说明、MIT License、开源发布清单 | 已创建公开 GitHub repo：https://github.com/codezzzsleep/mineru-data-agent | 记录 commit hash，补演示视频/PPT |

## 2. 当前项目主线

项目主线应表述为：

> 基于 MinerU 的可信文档 Data Agent。系统能理解任务目标，选择在线 API 或本地 CLI 后端完成解析，自动生成结构化结果、质量报告、可追溯日志和检索入库 chunks。

该表述能同时覆盖赛题页中的三类任务：

- 数据理解与结构化处理：`result.json` 与 `retrieval_chunks.jsonl`
- 复杂任务规划与自动执行：`plan`、`execution_control`、`trace.json`、`batch_report.json`
- 系统稳定性与综合能力：CLI、API、测试、部署说明、失败记录

## 3. 优先级判断

后续优化优先级：

1. 继续补真实文件证据：当前已补财报 PDF、合同 PDF、流程图 PDF、低质量扫描件、DOCX、PPTX、recovery 演练、挑战 fixture 和 4 个官方公开真实 PDF；下一步优先补扫描版真实文件、复杂图表样本和更细粒度人工标注。
2. 补工程稳定性数据：批处理耗时、失败恢复、在线 API 重试、本地 CLI artifact 对比。
3. 扩展大模型增强：当前 LLM 已参与解析前 profile/method/backend/lang 调度，并能把 fallback policy 写入执行计划；下一步让真实在线 LLM 参与二次校验规则生成、真实 CLI 全链路 fallback 和更细粒度 schema 对齐。
4. 强化一个主攻难点场景：建议优先选择财报密集数字或低质量 OCR。

不建议把精力分散到大量 UI 或大型模型微调上。赛题页更看重 Agent 的任务拆解、工具调用、可复现和真实场景落地。

## 4. 保守自评清单（按五维度）

基于当前仓库证据（重点参考 `submission_artifacts/evaluation/evaluation_metrics.md`）给出一版保守自评：

| 评分维度 | 权重 | 现状自评分 | 关键证据 | 主要短板 |
| --- | ---: | ---: | --- | --- |
| 复杂文档理解与结构化处理能力 | 20 | 18 | `submission_artifacts/cases/`、`submission_artifacts/mineru_cases/`、`submission_artifacts/public_real_cases/`、`submission_artifacts/office_cases/` | 真实复杂样本与细粒度标注仍偏少 |
| 难点场景攻克与技术创新性 | 15 | 12 | `submission_artifacts/challenge_cases/`、`submission_artifacts/recovery_cases/`、LLM 预调度链路 | 创新点有，但不可替代性与难点深度还可强化 |
| Agent 任务规划与自动执行能力 | 30 | 26 | `trace.json`、`execution_control`、batch 流程、API→CLI fallback | 多轮任务闭环与更强自治策略证据可再补 |
| 系统稳定性与工程可复现性 | 20 | 17 | `.github/workflows/tests.yml`、API smoke、提交产物完整 | 长时、高并发、极限输入稳定性证据不足 |
| 代码开源共享与产业生态价值 | 15 | 13 | README、部署/API 文档、MIT、案例产物 | 产业落地叙事与外部可复用性展示可加强 |

总分（保守自评）：86 / 100。

## 5. 补强优先级清单

### P0（立即补强，直接影响评审观感与得分）

- [ ] 增加真实复杂文档样本数量与覆盖面（扫描件、跨页表、复杂图表）并补标签。
- [ ] 对 1 个主攻难点做深打穿证据包（建议财报密集数字或低质量 OCR）。
- [ ] 增加稳定性压测记录（批处理连续运行、失败恢复率、耗时分布）。
- [ ] 补 Agent 自主决策价值对照证据（无预调度 vs 有预调度、无恢复 vs 有恢复）。

### P1（中优先级，提升说服力）

- [ ] 细化评测口径：补字段级/表格格级抽样核验（小规模人工集即可）。
- [ ] 增加跨后端一致性报告（agent-api 与 cli 结果差异解释）。
- [ ] 增加 Office/HTML/PDF 三类统一指标对齐表（便于评委横向比较）。

### P2（锦上添花）

- [ ] 增加产业场景落地说明（输入成本、运行成本、交付流程）。
- [ ] 增加演示脚本与一键复现实验入口（降低评委复跑门槛）。
- [ ] 增加 roadmap（后续可扩展能力与风险边界）。
