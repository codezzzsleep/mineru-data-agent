# MinerU Data Agent Run 2478fc60f3b2

- Task: 抽取报告日期、系统名称、异常情况和处理建议
- Profile: general_document
- Input: `<PROJECT_ROOT>\runs\api_smoke\_uploads\0436b28901264e3c8a5b26273ac3e49f.html`
- Quality: pass (100/100)
- Content blocks: 7
- Pages with provenance: 0
- Provenance level: document
- Sections: 1
- Tables: 1
- Key-values: 5
- Numeric facts: 0
- Dates detected: 1
- Recommendation signals: 3
- Anomaly signals: 2
- Retrieval chunks: 2
- Recovery decision: accept
- LLM analysis: disabled

## Plan
1. Inspect input type and task objective
2. Parse document with MinerU or native HTML extractor
3. Normalize content blocks with page-level or document-level provenance
4. Build markdown, section, key-value, table, and numeric views
5. Run quality checks and produce traceable logs

## Extracted Fields
- 报告日期: 2026-05-22
- 系统名称: 语料处理平台
- 巡检范围: 上传接口、解析任务队列、结果导出、日志归档和检索切片生成。
- 异常情况: 未发现阻断性错误，发现两条低优先级告警，均已进入复查队列。
- 处理建议: 继续观察任务队列延迟，保留 trace、summary 和 retrieval 输出用于复核。

## Recommendation Evidence
- 处理建议: 继续观察任务队列延迟，保留 trace、summary 和 retrieval 输出用于复核。
- 处理建议：继续观察任务队列延迟，保留 trace、summary 和 retrieval 输出用于复核。
- | 模块 | 状态 | 建议 |

## Recovery Decision
- Decision: accept
- Native extractor result has document/slide-level provenance; use PDF/MinerU path for page-layout audit.

## Issues
- [info] document_level_provenance: Native document input has document-level provenance rather than page-level provenance.

## Markdown Preview

# 网页巡检日报

报告日期：2026-05-22

系统名称：语料处理平台

巡检范围：上传接口、解析任务队列、结果导出、日志归档和检索切片生成。

异常情况：未发现阻断性错误，发现两条低优先级告警，均已进入复查队列。

处理建议：继续观察任务队列延迟，保留 trace、summary 和 retrieval 输出用于复核。

| 模块 | 状态 | 建议 |
| --- | --- | --- |
| 上传接口 | 正常 | 保留大小限制 |
| 结果导出 | 正常 | 定期抽查 |
