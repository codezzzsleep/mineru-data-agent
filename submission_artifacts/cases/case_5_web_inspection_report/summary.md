# MinerU Data Agent Run e0f566f95db8

- Task: 清洗网页巡检日报，抽取日期、异常数量、异常表格和处理建议。
- Profile: general_document
- Input: `<PROJECT_ROOT>\examples\cases\case_5_web_inspection_report.html`
- Quality: pass (100/100)
- Content blocks: 8
- Pages with provenance: 0
- Provenance level: document
- Sections: 2
- Tables: 1
- Key-values: 3
- Numeric facts: 4
- Dates detected: 1
- Recommendation signals: 2
- Anomaly signals: 7
- Retrieval chunks: 3
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

## Extracted Fields
- 报告日期: 2026-05-22
- 巡检范围: 产线 A、产线 B、仓储温控区和空压站。
- 处理建议: 优先复查高温轴承，并将异常记录写入维护台账。

## Recommendation Evidence
- 处理建议: 优先复查高温轴承，并将异常记录写入维护台账。
- 处理建议：优先复查高温轴承，并将异常记录写入维护台账。

## Recovery Decision
- Decision: accept
- Native extractor result has document/slide-level provenance; use PDF/MinerU path for page-layout audit.

Attempts:
- initial: pass (100/100), selected

## Issues
- [info] document_level_provenance: Native document input has document-level provenance rather than page-level provenance.

## Markdown Preview

# 设备巡检日报

报告日期：2026-05-22

巡检范围：产线 A、产线 B、仓储温控区和空压站。

产线 A 今日完成 42 次巡检，发现 2 个需要复核的温度异常点。

产线 B 今日完成 37 次巡检，未发现停机风险。

## 异常记录

| 设备 | 异常类型 | 数值 | 处理状态 |
| --- | --- | --- | --- |
| A-17 轴承 | 温度异常 | 86.5 | 待复核 |
| A-22 电机 | 振动异常 | 4.8 | 已派单 |

处理建议：优先复查高温轴承，并将异常记录写入维护台账。
