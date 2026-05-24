# CLI 契约

本项目以 CLI-first 的 MinerU Data Agent 形式提交。评委应把 `data-agent` 命令作为稳定接口；HTTP API 是可选 wrapper，不是主竞赛接口。

## 命令

### `data-agent run`

解析单个文档，并写出一个运行目录：

- `result.json`
- `trace.json`
- `summary.md`
- `retrieval/retrieval_chunks.jsonl`
- `retrieval/retrieval_manifest.json`

示例：

```bash
data-agent run \
  --input examples/cases/case_1_financial_report.html \
  --out runs/cli_demo \
  --task "抽取财报关键字段并检查合计行" \
  --profile auto
```

CPU 环境解析 PDF，可通过 CLI 调用 MinerU 在线 Agent API：

```bash
data-agent run \
  --runner agent-api \
  --input demo.pdf \
  --out runs/pdf_api \
  --task "解析 PDF 并输出结构化结果和质量日志"
```

需要审计级 PDF artifact 和页级 provenance 时，使用本地 MinerU CLI：

```bash
data-agent run \
  --runner cli \
  --input demo.pdf \
  --out runs/pdf_cli \
  --task "解析财报 PDF，抽取表格、关键数字并检查合计行" \
  --backend pipeline \
  --method auto
```

### `data-agent batch`

执行 JSON manifest。单个任务失败不会中断整批。

```bash
data-agent batch \
  --manifest examples/batch_manifest.json \
  --out runs/batch_demo
```

批处理目录会写出 `batch_report.json` 和每个任务的 run directory。

### `data-agent agent-run`

运行 live OpenAI-compatible tool-calling Agent 路径。Provider key 只从环境变量读取，不写入 artifact。

```bash
data-agent agent-run \
  --provider modelscope \
  --input examples/cases/case_2_low_quality_ocr.html \
  --out runs/agent_live \
  --task "发现乱码后先清理，再抽取设备 B-17 的异常温度"
```

该命令写出：

- `result.json`
- `live_agent_trace.json`
- `live_agent_summary.md`

证据口径：

- Live Agent 是 **skill-guided**：LLM 必须先调用 `select_skill` 选择高层策略；如果证据与初始计划冲突，可以切换 skill。
- 当前 skill 包括 `financial_total_audit`、`not_found_guard`、`text_recovery_then_extract`、`contract_clause_review`、`workflow_risk_review` 和 `structured_extraction`。
- LLM 必须在 `finalize` 前调用 `validate_answer`。该工具检查未被证据支持的数字、简单算术矛盾、缺失证据和 selected-skill not_found 冲突。
- 工具层强制最小闭环：未选择 skill 前拒绝除 `select_skill` 外的工具；未解析文档前拒绝 `validate_answer`；`finalize` 只有在同一答案和同一证据列表已通过校验后才允许执行。
- `tool_call_completed=true`：真实 provider 调用到达 `finalize`，消耗 provider token，并生成完成态 trace。
- `answer_validation.ok=true`：内置校验通过。它增强证据链，但仍不替代人工或 benchmark 复核。
- `answer_quality_pass=true`：单独的人工或 benchmark 语义复核认为最终答案正确。
- 不能把 tool-call completion 直接当作语义成功；语义成功必须看 `answer_quality_pass=true`。

## 稳定输出字段

评审脚本可优先检查以下 `result.json` 顶层字段：

| 字段 | 含义 |
| --- | --- |
| `schema_version` | 输出 schema 版本，用于兼容性检查。 |
| `run_id` | 稳定运行标识。 |
| `task` | 用户任务。 |
| `profile` | 确定性 profile 推断和可选 LLM 复核后的最终 profile。 |
| `execution_control` | 规划依据、action plan、记忆、恢复计划和应用/忽略控制项。 |
| `extracted` | 结构化章节、表格、键值、数字事实、语义信号和任务结果。 |
| `quality` | 质量状态、分数、issue code 和 warning。 |
| `recovery_decision` | 恢复尝试、选中尝试和原因链。 |
| `retrieval_export` | Retrieval chunk 路径和统计。 |
| `trace_path` | 完整执行 trace。 |
| `summary_path` | 人类可读摘要。 |

## 非目标

- CLI 提交不要求提供长期公网 API。
- 已保存 API smoke/load artifact 只是二级工程证据。
- 离线 scripted decision cases 是回归 fixture，不是 live LLM 证据。
- 当前保存的 live-agent 包包含 8 次 provider 尝试、4 次 tool-call completion 和 2 次人工复核 answer-quality pass。该包生成于更严格的 2026-05-25 skill/validation gate 之前，因此是旧版 live-provider 证据，不代表新版 gate 已完成 provider rerun。
