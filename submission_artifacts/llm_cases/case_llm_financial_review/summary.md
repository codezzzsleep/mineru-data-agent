# MinerU Data Agent Run 42f057700d90

- Task: 解析财报密集数字表格，抽取报告日期、公司名称、关键数字、检查合计行，并由大模型给出复核计划、目标schema和风险恢复建议。注意：HTML fixture 由本地 HTML 结构化模块解析，不要写成 MinerU CLI/API 已解析；没有质量错误时不要输出 error 级风险。
- Profile: financial_report
- Input: `<PROJECT_ROOT>\examples\cases\case_1_financial_report.html`
- Quality: pass (100/100)
- Content blocks: 8
- Pages with provenance: 0
- Provenance level: document
- Sections: 2
- Tables: 1
- Key-values: 5
- Numeric facts: 7
- Dates detected: 1
- Recommendation signals: 2
- Anomaly signals: 3
- Retrieval chunks: 3
- Recovery decision: accept
- LLM analysis: enabled/completed

## Plan
1. Inspect input type and task objective
2. Parse document with MinerU or native HTML extractor
3. Normalize content blocks with page-level or document-level provenance
4. Build markdown, section, key-value, table, and numeric views
5. Run quality checks and produce traceable logs
6. Prioritize dense table extraction and numeric consistency checks
7. Flag subtotal/total rows and suspicious numeric cells

## LLM Agent Analysis

解析一份由本地HTML结构化模块（native-html-extractor）提取的财务报告HTML fixture，报告为华东制造有限公司2026年一季度经营报表。任务包括：抽取报告日期、公司名称、表中关键数字（营业收入、营业成本、销售费用、管理费用、利润总额、合计项），验证合计行数值与明细项之和是否一致，并输出复核计划、目标提取schema、风险发现和恢复建议。输入为文档级溯源（无页面级），质量检查无错误，合计行已验证一致。

Suggested execution plan:
1. 确认输入来源为native-html-extractor，标注解析器类型并避免误写为MinerU CLI/API
2. 从markdown_preview和section_titles抽取报告日期、公司名称
3. 提取表格中所有数值行，包括明细项和合计行，记录每行每个数值单元格
4. 对合计行进行独立性验算：将前5个明细项的2026Q1列和2025Q4列分别求和，与合计行对应数值比较（已由quality.issues验证一致，delta=0）
5. 构建结构化schema，包含字段：报告日期、公司名称、项目、2026Q1值、2025Q4值、变动率、合计验证状态
6. 生成验证重点清单，涵盖数字一致性、合计行正确性、溯源完整性
7. 基于当前无质量错误的事实，输出info或warning级别的风险发现，不输出error级别
8. 提出恢复建议，针对未来可能出现的OCR跨列、行数不匹配等场景准备预案

## Extracted Fields
- 报告日期: 2026-04-30
- 公司名称: 华东制造有限公司
- 报表口径: 人民币万元，未经审计，用于 Data Agent 结构化处理与数字复核演示。
- 异常提示: 合计行需要与明细项重新核验，避免 OCR 或表格跨列导致金额幻觉。
- 处理建议: 将总计、小计、合计行加入复核队列，并保留源页和表格行号证据。

## Recommendation Evidence
- 处理建议: 将总计、小计、合计行加入复核队列，并保留源页和表格行号证据。
- 处理建议：将总计、小计、合计行加入复核队列，并保留源页和表格行号证据。

## Recovery Decision
- Decision: accept
- Native extractor result has document/slide-level provenance; use PDF/MinerU path for page-layout audit.

## Issues
- [info] document_level_provenance: HTML input has document-level provenance rather than page-level provenance.
- [info] numeric_total_verified: A total/subtotal row matched the sum of comparable numeric rows.

## Markdown Preview

# 华东制造有限公司 2026 年一季度经营报表

报告日期：2026-04-30

公司名称：华东制造有限公司

报表口径：人民币万元，未经审计，用于 Data Agent 结构化处理与数字复核演示。

## 资产负债与利润摘要

| 项目 | 2026Q1 | 2025Q4 | 变动率 |
| --- | --- | --- | --- |
| 营业收入 | 12,860.50 | 11,902.10 | 8.05% |
| 营业成本 | 8,430.25 | 7,921.30 | 6.43% |
| 销售费用 | 615.30 | 590.00 | 4.29% |
| 管理费用 | 781.20 | 760.15 | 2.77% |
| 利润总额 | 3,033.75 | 2,630.65 | 15.32% |
| 合计 | 25,721.00 | 23,804.20 | 8.05% |

异常提示：合计行需要与明细项重新核验，避免 OCR 或表格跨列导致金额幻觉。

处理建议：将总计、小计、合计行加入复核队列，并保留源页和表格行号证据。
