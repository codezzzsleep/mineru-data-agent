# 评分对齐与优化策略

赛题页显示，赛道二满分 100 分，评审分为五个维度。本项目按评分权重组织功能和提交材料。

## 1. 评分维度映射

| 官方评分维度 | 分值 | 本项目对应能力 | 当前状态 | 下一步优化 |
| --- | ---: | --- | --- | --- |
| 复杂文档理解与结构化处理能力 | 20 | MinerU 解析、Markdown/内容块读取、章节/表格/键值/数字事实抽取、HTML 表格解析、DOCX/PPTX 结构化、质量校验、知识库 chunks | 已实现并有 5 个 HTML fixture artifact + 4 个 PDF 文件级 CLI artifact + 1 个 Agent API PDF artifact + 2 个 Office 文件级 artifact | 补更多真实客户形态样本和复杂图表样本 |
| 难点场景攻克与技术创新性 | 15 | 面向财报数字、低质量 OCR、行业标准、工程流程、网页清洗等 profile 的任务化处理 | 已有案例证据，仍偏工程框架 | 主攻财报数字或低质量 OCR，加入更强指标 |
| Agent 任务规划与自动执行能力 | 30 | 任务 profile 推断、执行计划、DeepSeek/ModelScope 可选计划增强、工具调用、在线 API/本地 CLI 双后端、native Office/HTML 分支、自动恢复尝试、恢复失败降级保留初始结果、批处理 manifest、失败不中断 | 已有可复跑证据，并补充 1 个 LLM-enabled 财报复核案例；已加入 text_cleanup 与 OCR retry 的执行闭环 | 让 LLM 进一步参与后端选择和 schema 驱动二次校验 |
| 系统稳定性与工程可复现性 | 20 | CLI、FastAPI、trace、batch_report、部署文档、测试、提交压缩包、案例 artifact | 已补强并在 HeyWhale CPU 环境验证 | 补长文档/高并发稳定性记录 |
| 代码开源共享与产业生态价值 | 15 | 可开源项目结构、检索导出 JSONL、API 文档、案例报告、原创性边界说明、MIT License、开源发布清单 | 已创建公开 GitHub repo：https://github.com/codezzzsleep/mineru-data-agent | 记录 commit hash，补演示视频/PPT |

## 2. 当前项目主线

项目主线应表述为：

> 基于 MinerU 的可信文档 Data Agent。系统能理解任务目标，选择在线 API 或本地 CLI 后端完成解析，自动生成结构化结果、质量报告、可追溯日志和检索入库 chunks。

该表述能同时覆盖赛题页中的三类任务：

- 数据理解与结构化处理：`result.json` 与 `retrieval_chunks.jsonl`
- 复杂任务规划与自动执行：`plan`、`trace.json`、`batch_report.json`
- 系统稳定性与综合能力：CLI、API、测试、部署说明、失败记录

## 3. 优先级判断

后续优化优先级：

1. 继续补真实文件证据：当前已补财报 PDF、合同 PDF、流程图 PDF、低质量扫描件、DOCX 和 PPTX；下一步优先补更多真实客户形态样本与复杂图表样本。
2. 补工程稳定性数据：批处理耗时、失败恢复、在线 API 重试、本地 CLI artifact 对比。
3. 扩展大模型增强：当前已有 1 个 ModelScope DeepSeek-V4-Flash 证据和规则驱动自动恢复；下一步让 LLM 参与后端选择、失败恢复和 schema 驱动的二次校验。
4. 强化一个主攻难点场景：建议优先选择财报密集数字或低质量 OCR。

不建议把精力分散到大量 UI 或大型模型微调上。赛题页更看重 Agent 的任务拆解、工具调用、可复现和真实场景落地。
