# LLM Case Artifacts

本目录保存一次实际启用大模型的 Data Agent 运行证据。该证据用于证明项目不只是规则后处理，还能调用 OpenAI-compatible 大模型完成任务理解、目标 schema 建议、复核重点和恢复建议生成。

| Case | Provider | Model | Status | Evidence |
| --- | --- | --- | --- | --- |
| `case_llm_financial_review` | ModelScope | `deepseek-ai/DeepSeek-V4-Flash` | completed | `result.json`, `trace.json`, `summary.md`, `retrieval/` |

安全说明：API key 仅通过运行时环境变量传入，未写入 `result.json`、`trace.json`、文档或提交包。
