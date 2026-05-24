# 原创性与合规说明

## 1. 第三方参考边界

本项目允许阅读公开资料来理解行业常见做法，但提交代码必须保持清晰边界：

- 不复制第三方项目源码。
- 不复刻第三方项目的品牌、项目名、README 叙事和专有实现细节。
- 不把第三方项目已有功能包装成本项目原创成果。
- 如果未来直接引入第三方代码，必须保留许可证、版权声明，并在技术报告中明确说明来源和改动范围。

`frondesce/mineru-kb-packager` 只作为“MinerU 后处理可以服务检索入库”的方向参考。本项目没有把该仓库作为依赖，也不把它包含在提交包中。为避免命名和叙事混淆，本项目将相关模块命名为 `Retrieval Exporter`，输出 `retrieval_chunks.jsonl`、`retrieval_manifest.json` 和 `retrieval_quality.json`，服务于本项目的结构化结果与评审复查。

## 2. 本项目原创实现范围

当前提交的核心实现包括：

- 任务 profile 推断与执行计划。
- CLI-first MinerU 在线 Agent API 与本地 CLI 双后端适配。
- HTML 轻量解析。
- Markdown、内容块、章节、表格、键值对、数字事实抽取。
- 质量校验与风险标注。
- Retrieval Exporter 检索导出。
- 批处理 manifest、失败不中断与 batch report。
- DeepSeek/ModelScope 可选 LLM 任务理解和复核层。
- 可选 FastAPI wrapper 接口。

这些模块围绕赛题要求组织，重点不是复刻某个知识库打包工具，而是构建一个可执行、可追溯、可复现的 Data Agent。

## 3. 密钥与敏感信息

项目不得提交任何真实 API key、token、账号或私密文件。

要求：

- DeepSeek 使用 `DEEPSEEK_API_KEY` 环境变量。
- ModelScope 使用 `MODELSCOPE_API_KEY` 环境变量。
- 文档只保留占位示例，不写真实密钥。
- `trace.json` 和 `result.json` 不输出 Authorization header 或 key。
- 提交包生成脚本应排除缓存、运行中间件、虚拟环境和本地配置。

## 4. 开源发布边界

项目采用 MIT License，便于评审和社区复现核心代码。当前已创建公开 GitHub 仓库：https://github.com/codezzzsleep/mineru-data-agent。提交材料应记录 repo URL 与本次推送后的 commit hash。

## 5. 赛题对齐原则

本项目后续优化必须优先服务赛题五项评分：

- 复杂文档理解与结构化处理。
- 难点场景攻克与技术创新。
- Agent 任务规划与自动执行。
- 系统稳定性与工程可复现性。
- 代码开源共享与产业生态价值。

所有新增模块都应回答两个问题：

- 它是否改善 Agent 的自动决策、工具调用、异常恢复或稳定复现？
- 它是否能通过真实案例、日志和测试结果被评审验证？
