# MinerU Data Agent Run 6eebecbf0e8a

- Task: 结构化合同条款，抽取合同编号、签署日期、章节条款、异常处理和处理建议。
- Profile: standard_or_contract
- Input: `<PROJECT_ROOT>\examples\cases\case_3_standard_contract.html`
- Quality: pass (100/100)
- Content blocks: 12
- Pages with provenance: 0
- Provenance level: document
- Sections: 5
- Tables: 0
- Key-values: 4
- Numeric facts: 1
- Dates detected: 1
- Recommendation signals: 2
- Anomaly signals: 3
- Retrieval chunks: 5
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
6. Prioritize section hierarchy and clause-like paragraph extraction
7. Preserve source page or document heading evidence for each clause

## Extracted Fields
- 合同编号: DPA-2026-0519
- 签署日期: 2026-05-19
- 异常提示: 跨页表格、签章覆盖和乱码文本需要进入人工复核队列。
- 处理建议: 保留章节标题、条款编号和源文件证据，便于合规审计。

## Recommendation Evidence
- 处理建议: 保留章节标题、条款编号和源文件证据，便于合规审计。
- 处理建议：保留章节标题、条款编号和源文件证据，便于合规审计。

## Recovery Decision
- Decision: accept
- Native extractor result has document/slide-level provenance; use PDF/MinerU path for page-layout audit.

Attempts:
- initial: pass (100/100), selected

## Issues
- [info] document_level_provenance: Native document input has document-level provenance rather than page-level provenance.

## Markdown Preview

# 数据处理服务合同关键条款

合同编号：DPA-2026-0519

签署日期：2026-05-19

## 第一条 服务范围

乙方负责对甲方提供的 PDF、HTML、Word 与扫描图片进行解析、清洗、结构化抽取和质量复核。

## 第二条 数据安全

乙方不得将甲方原始文件、API 密钥或中间处理结果用于合同外目的，日志中不得记录敏感密钥。

## 第三条 验收标准

验收以结构化 JSON、执行 trace、质量报告和可复跑命令为准；若发现关键字段缺失，应在 2 个工作日内补正。

## 第四条 异常处理

异常提示：跨页表格、签章覆盖和乱码文本需要进入人工复核队列。

处理建议：保留章节标题、条款编号和源文件证据，便于合规审计。
