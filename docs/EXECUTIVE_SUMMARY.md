# Executive Summary

MinerU Data Agent 是一个面向赛道二的可信文档处理 Agent：它在 MinerU/Office/HTML 解析之上增加任务意图识别、动态 schema、质量校验、自动恢复、检索导出和可审计日志。

## 关键证据

| 评审关注点 | 证据位置 |
| --- | --- |
| Agent 自适应规划 | `submission_artifacts/adaptive_cases/` |
| 真实 LLM token 用量 | `submission_artifacts/llm_cost/llm_cost_report.md` |
| 长文档分片执行 | `submission_artifacts/long_document_chunks/public_nist_ai_rmf_full_chunked/` |
| 带标注指标与 F1 | `submission_artifacts/evaluation/evaluation_metrics.md` |
| HTTP 并发 smoke | `submission_artifacts/http_load_test_100/http_load_test_report.md` |
| Recovery 证据 | `submission_artifacts/recovery_cases/case_pdf_llm_api_to_cli_fallback/` |

## 核心改进

- 同一文档、不同自然语言任务会生成不同 `adaptive_decision`、`target_schema`、`post_processors` 和 `task_result`。
- 财报类任务可对表格行计算 delta/percent_change，并产出 `top_growth_candidate`。
- 评测报告除轻量标签准确率外，新增字段级 precision/recall/F1 和 failed-check 分布。
- 提交包保留诚实边界：当前不是公网生产压测，不是完整 OCR 字符级 benchmark，也不是本机 GPU 长文档 benchmark。
