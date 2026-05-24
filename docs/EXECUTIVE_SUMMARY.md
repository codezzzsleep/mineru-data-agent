# 一页摘要

MinerU Data Agent 面向赛道二提交：在 MinerU、Office 和 HTML 解析结果之上，增加任务规划、结构化抽取、质量校验、自动恢复、检索导出和运行日志。

## 评审先看

| 关注点 | 当前结果 | 位置 |
| --- | --- | --- |
| 不同任务触发不同计划 | 同一财报输入分别生成增长排名和异常复核两套 `adaptive_decision`、`target_schema`、`post_processors`、`task_result` | `submission_artifacts/adaptive_cases/` |
| 带标注指标 | 17 个案例、45 个字段、22 条文本证据、11 条数字证据、6 条表格证据；输出字段级 precision/recall/F1 | `submission_artifacts/evaluation/evaluation_metrics.md` |
| PDF 页级恢复 | 在线 API 缺少页级 provenance 后，记录 `no_page_provenance` 并切换到 CLI artifact，`recovery_decision.executed=true` | `submission_artifacts/recovery_cases/case_pdf_llm_api_to_cli_fallback/` |
| 长文档分片 | NIST AI RMF 48 页拆成 1-20、21-40、41-48 三段；3/3 成功，58 个 retrieval chunks | `submission_artifacts/long_document_chunks/public_nist_ai_rmf_full_chunked/` |
| LLM 用量 | ModelScope DeepSeek-V4-Flash 实跑 2 次调用，记录 4309 tokens | `submission_artifacts/llm_cost/llm_cost_report.md` |
| LLM 影响对比 | 保存的规则运行 vs LLM-enabled 运行，记录 LLM 决策点、token 和 recovery suggestion | `submission_artifacts/llm_impact/llm_impact_report.md` |
| API 并发 | 本地 HTTP loopback 100 请求、并发 20、100/100 成功，P95 约 4.21 秒 | `submission_artifacts/http_load_test_100/http_load_test_report.md` |
| Artifact 总索引 | 按目录列出 result/trace 数量和主报告 | `submission_artifacts/ARTIFACTS_INDEX.md` |

## 本轮重点

- `quality.score` 用于记录空结果、乱码、页级来源缺失、合计行不一致等规则风险；字段级指标单独在 evaluation 报告中统计。
- `execution_control` 记录任务意图、目标 schema、后处理器、LLM 建议的应用/忽略原因和恢复策略。
- LLM 解析后复核现在会写入 `recovery_decision.llm_quality_decision`，可把 warning/error 级风险同步到最终 recovery 决策。
- `trace.json`、`result.json`、`summary.md`、`retrieval_chunks.jsonl` 每次运行落盘，便于按文件复查。
- 当前未包含：公网生产压测、完整 OCR 字符级 benchmark、本机 GPU 长文档 benchmark。
