# MinerU Data Agent

本项目为 MDIC 2026 赛道二数据智能体提交作品，主交付形态是命令行工具 `data-agent`。

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
