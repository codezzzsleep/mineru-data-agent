# 详细功能清单

本文从 README 中拆出较细的功能点，方便评委按能力项核对。

## 核心能力

- 任务意图识别、自适应执行计划和目标 schema 选择。
- 可配置 profile 推断：关键词匹配 + 确定性相似度打分。
- Agent action plan：包含子任务拆解、候选工具和 replan triggers。
- PDF、Office、HTML 结构化解析适配层。
- Markdown、表格、键值对、数字事实、语义信号抽取。
- 文本质量、页级来源、财报数字、合同/结构类 validator。
- 可选 DeepSeek/ModelScope LLM 解析前调度。
- 自动恢复：编码噪声清理、OCR retry、CLI fallback。
- 跨运行本地记忆：用 SQLite 复用历史 recovery 路径统计。
- Retrieval chunks JSONL 导出，便于下游 RAG。
- CLI-first 单文件与批处理执行。
- 可选 FastAPI 同步/异步 job wrapper，仅用于本地集成测试。

## Live LLM Agent 证据

`agent_live.py` 提供真实 OpenAI-compatible tool-calling harness，并通过 `data-agent agent-run` 暴露为 CLI 命令。新版 live Agent 是 skill-guided：LLM 必须先选择高层 skill，包括 `financial_total_audit`、`not_found_guard`、`text_recovery_then_extract`、`contract_clause_review`、`workflow_risk_review` 或 `structured_extraction`。当证据与初始计划冲突时，模型可以切换 skill；最终 `finalize` 前必须调用 `validate_answer`。

工具层会强制执行这个闭环：未完成 `select_skill` 前拒绝其他工具；未解析文档前拒绝答案校验；`finalize` 必须使用已验证的同一答案和同一证据列表。HTTP API 不暴露 live-agent endpoint，避免把不稳定 provider 调用混入稳定评审接口。

当前保存的 `submission_artifacts/agent_live_cases/agent_live_report.json` 是 2026-05-25 更严格 skill/validation gate 之前生成的旧版 provider 包：8 次 ModelScope Qwen3-235B live 尝试，4 次 finalize/tool-call completion，2 次人工复核语义通过，0 个新版 tool-validated skill-gated rerun case。

| Trace | Turns | Tokens | Tool-call completed | Answer-quality pass | 关键观察 |
| --- | ---: | ---: | --- | --- | --- |
| Q3 mismatch decline | 7 | 13,230 | true | true | 正确拒答 `not_found`，并引用了文档中实际存在的季度 |
| Low-quality OCR recovery | 10 | 17,708 | true | true | 自主触发 `clean_text` 后再抽取 |
| Financial total check | 8 | 15,724 | true | false | 工具链完成，但最终数字一致性表述自相矛盾 |
| Contract obligation analysis | 8 | 12,704 | true | false | 工具链完成，但最终答案漏掉了合同责任内容 |

Live-agent 总尝试 tokens：61,890。Tool-call-completed tokens：59,366。Answer-quality-pass tokens：30,938。

## 提交证据概览

- 17 个带标注案例，输出字段级 precision/recall/F1。
- 4 份官方公开 PDF：IRS W-4、NIST AI RMF、Microsoft 10-K、CDC VIS。
- 公开真实文档证据位于 `submission_artifacts/public_real_cases/`，长文档分片证据位于 `submission_artifacts/long_document_chunks/`。
- 5 个 controlled failure/recovery 负样本。
- 8 次旧版 live LLM agent trace，其中 4 次 finalize/tool-call completion、2 次人工复核 answer-quality pass、0 个保存的新版 skill-gated tool-validated rerun case。
- 成本/速度/质量 tradeoff model 使用可替换的 2026 年 5 月场景假设，不作为合约价格。
- HTTP load 证据保留为二级工程材料；CI 当前以 CLI smoke commands 作为主回归门禁。
