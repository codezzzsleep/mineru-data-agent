# MinerU Data Agent

CLI-first Data Agent Harness for complex document processing, with stable review gates, traceable recovery, and Agent-ready document skill packages.

本项目为 MDIC 2026 赛道二数据智能体提交作品，主交付形态是命令行工具 `data-agent`。

本仓库已同步决赛答辩版本，包含交互式 `chat`、自动路由和逐本语料包。版本来源与发布检查见 [决赛版本说明](docs/FINAL_DEFENSE_RELEASE.md)。

**正式技术报告只有一份：根目录 [技术报告.md](技术报告.md)。**

该报告已完整覆盖赛题要求的整体设计方案、任务执行机制、数据处理与工具调用能力、系统性能与稳定性、不少于 5 个典型任务执行示例，以及系统适用场景与应用价值说明。

## 快速运行

```bash
pip install -e ".[dev]"
data-agent run --input examples/cases/case_1_financial_report.html --out runs/cli_demo --task "抽取财报关键字段并检查合计行" --profile auto
```

输出目录包含：

- `result.json`
- `trace.json`
- `summary.md`
- `retrieval/retrieval_chunks.jsonl`

批处理：

```bash
data-agent batch --manifest examples/batch_manifest.json --out runs/batch_demo
```

把批处理或切块处理结果重组为“每份原始资料一个 AI 友好交付包”：

```bash
data-agent corpus package-sources --run-root runs/202606170251 --source-root 史料part --out runs/source_packages
```

每份资料目录会包含 `result.json`、`summary.md`、`trace.json`、`retrieval/retrieval_chunks.jsonl` 和 `document_skill/`。如果一本资料被拆成多个页段处理，系统会合并回同一个原始资料目录，并在 `trace.json` 与 `result.json.source_runs` 中保留页段和原 run 证据。

Live LLM Agent 复跑需要真实 provider key：

```bash
data-agent agent-run --provider modelscope --input examples/cases/case_2_low_quality_ocr.html --out runs/agent_live --task "发现乱码后先清理，再抽取设备 B-17 的异常温度"
```

## 提交包

最终提交包：

```text
dist/mineru-data-agent-submission.zip
```

公开仓库：

```text
https://github.com/codezzzsleep/mineru-data-agent
```
