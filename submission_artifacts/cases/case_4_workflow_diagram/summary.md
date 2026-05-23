# MinerU Data Agent Run 82f2fcd2a454

- Task: 解析工艺流程说明，抽取流程步骤、关键参数、异常节点和处理建议。
- Profile: workflow_or_diagram
- Input: `<PROJECT_ROOT>\examples\cases\case_4_workflow_diagram.html`
- Quality: pass (100/100)
- Content blocks: 11
- Pages with provenance: 0
- Provenance level: document
- Sections: 2
- Tables: 0
- Key-values: 5
- Numeric facts: 4
- Dates detected: 1
- Recommendation signals: 2
- Anomaly signals: 2
- Retrieval chunks: 2
- Recovery decision: accept
- Recovery selected attempt: initial
- Recovery attempts: 1
- LLM analysis: disabled

## Plan
1. Inspect input type and task objective
2. Parse document with MinerU or native HTML extractor
3. Normalize content blocks with page-level or document-level provenance
4. Build markdown, section, key-value, table, and numeric views
5. Run quality checks and produce traceable logs
6. Prioritize figure/image references and ordered procedural statements
7. Flag pages that need visual model follow-up

## Extracted Fields
- 报告日期: 2026-05-20
- 流程名称: 正极浆料涂布与烘干流程
- 流程图说明: 投料 -> 搅拌 -> 过滤 -> 涂布 -> 烘干 -> 收卷 -> 质检。
- 异常提示: 若温区 3 连续 5 分钟超过 92 摄氏度，需暂停收卷并复核传感器。
- 处理建议: Agent 应抽取步骤顺序、关键参数、异常节点和待视觉模型复核的图像说明。

## Recommendation Evidence
- 处理建议: Agent 应抽取步骤顺序、关键参数、异常节点和待视觉模型复核的图像说明。
- 处理建议：Agent 应抽取步骤顺序、关键参数、异常节点和待视觉模型复核的图像说明。

## Recovery Decision
- Decision: accept
- Native extractor result has document/slide-level provenance; use PDF/MinerU path for page-layout audit.

Attempts:
- initial: pass (100/100), selected

## Issues
- [info] document_level_provenance: Native document input has document-level provenance rather than page-level provenance.

## Markdown Preview

# 锂电池涂布产线流程说明

报告日期：2026-05-20

流程名称：正极浆料涂布与烘干流程

流程图说明：投料 -> 搅拌 -> 过滤 -> 涂布 -> 烘干 -> 收卷 -> 质检。

## 关键步骤

- 投料阶段核对批次号和固含量。

- 搅拌阶段记录转速 1,200 rpm 和温度 25 摄氏度。

- 涂布阶段监控厚度 118 微米，允许偏差 3 微米。

- 烘干阶段检查温区 1 到温区 4 的温度曲线。

异常提示：若温区 3 连续 5 分钟超过 92 摄氏度，需暂停收卷并复核传感器。

处理建议：Agent 应抽取步骤顺序、关键参数、异常节点和待视觉模型复核的图像说明。
