# LLM Financial Review Case

本案例基于 `examples/cases/case_1_financial_report.html`，启用 ModelScope OpenAI-compatible 接口调用 `deepseek-ai/DeepSeek-V4-Flash`。

## 运行结果

- Run ID: `42f057700d90`
- LLM enabled: `true`
- Tool call: `modelscope-llm`
- Tool status: `completed`
- LLM elapsed seconds: `12.709`
- Quality: `pass (100/100)`
- Retrieval chunks: `3`

## 大模型职责

LLM 没有替代底层解析和规则校验，而是在已有结构化结果上生成：

- 任务理解
- 执行计划细化
- 目标 schema
- 复核重点
- 风险发现
- 恢复建议

## 边界说明

该案例输入是 HTML fixture，由本地 HTML 结构化模块解析，不是 MinerU CLI/API 解析。LLM 输出已明确标注这一点，避免把 HTML fixture 的证据包装成 MinerU PDF 解析证据。
