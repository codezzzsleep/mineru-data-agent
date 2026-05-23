# LLM Case Artifacts

本目录保存一次实际启用大模型的 Data Agent 运行结果。该结果记录 OpenAI-compatible 大模型参与任务理解、目标 schema 建议、复核重点和恢复建议生成。

当前代码已进一步把 LLM 前移为解析前调度器：开启 `--llm deepseek` 或 `--llm modelscope` 后，系统会先执行 `llm_pre_execution_planning`，由模型建议 profile、runner、backend、method、语言、目标 schema 和恢复策略；安全白名单内且未被显式锁定的建议会进入 `execution_control.applied` 并影响本次解析。旧目录中的 `case_llm_financial_review` 是一次真实 ModelScope 调用记录，主要覆盖解析后复核链路；新增预调度链路由测试覆盖，重新配置 key 复跑即可生成包含预调度步骤的新结果。

| Case | Provider | Model | Status | Evidence |
| --- | --- | --- | --- | --- |
| `case_llm_financial_review` | ModelScope | `deepseek-ai/DeepSeek-V4-Flash` | completed | `result.json`, `trace.json`, `summary.md`, `retrieval/` |

安全说明：API key 仅通过运行时环境变量传入，未写入 `result.json`、`trace.json`、文档或提交包。
