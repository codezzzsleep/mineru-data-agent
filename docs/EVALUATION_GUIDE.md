# 评审指南

这是评审 MinerU Data Agent 提交包的最短路径。项目以命令行工具形式提交，稳定评审入口是 `data-agent`，可选 HTTP API 仅作为本地集成 wrapper。

## 1. 项目做什么

MinerU Data Agent 接收 PDF、HTML、DOCX、PPTX 或图片类文档输入，调用 MinerU 或轻量原生解析器，生成结构化 JSON、运行 trace、质量风险报告、恢复记录和 retrieval chunks。

Agent 层在基础解析之上增加任务规划、schema 选择、字段证据、质量检查、恢复决策、本地恢复记忆、CLI 批处理和可选 LLM 预调度/解析后复核。单独的 `data-agent agent-run` 命令用于真实 provider 的 tool-calling LLM Agent 复跑。

## 2. 三步 CLI 复现

```bash
pip install -e ".[dev]"
data-agent run --input examples/cases/case_1_financial_report.html --out runs/review_cli --task "抽取财报关键字段并检查合计行" --profile auto
data-agent batch --manifest examples/batch_manifest.json --out runs/review_batch
```

第一条命令应生成 `result.json`、`trace.json`、`summary.md` 和 `retrieval/` 目录。第二条命令应生成 `batch_report.json` 和每个任务的运行目录。

CPU 环境复跑 PDF：

```bash
data-agent run --runner agent-api --input demo.pdf --out runs/review_pdf_api --task "解析 PDF 并输出结构化结果和质量日志"
```

需要页级 provenance 和完整 MinerU artifact 时，使用本地 MinerU CLI：

```bash
data-agent run --runner cli --input demo.pdf --out runs/review_pdf_cli --task "解析财报 PDF，抽取表格、关键数字并检查合计行" --backend pipeline --method auto
```

## 3. Live LLM 复现

Live tool-calling 证据需要真实 provider key：

```bash
data-agent agent-run \
  --provider modelscope \
  --input examples/cases/case_2_low_quality_ocr.html \
  --out runs/agent_live \
  --task "发现乱码后先清理，再抽取设备 B-17 的异常温度"
```

批量复跑脚本：

```bash
python scripts/run_agent_live_cases.py --provider modelscope --min-completed-rate 0
```

没有 provider key 时，脚本不会生成伪 live 证据。

## 4. 评分维度映射

| 官方维度 | 建议先检查 | 文件位置 |
| --- | --- | --- |
| 复杂文档理解与结构化处理 | 17 个带标注案例、字段 precision/recall/F1、公开 PDF、PDF CLI 案例 | `submission_artifacts/evaluation/evaluation_metrics.md`、`submission_artifacts/public_real_cases/`、`submission_artifacts/mineru_cases/` |
| 难点场景攻克与技术价值 | 跨页财报 fixture、OCR 噪声合同、PDF recovery、controlled failure/recovery、长文档分片与风险说明 | `submission_artifacts/challenge_cases/`、`submission_artifacts/recovery_cases/`、`submission_artifacts/failure_recovery_cases/README.md`、`submission_artifacts/long_document_chunks/`、`submission_artifacts/long_document_risk/long_document_risk_report.md` |
| Agent 规划与自动执行 | CLI action plan、runtime recovery plan、本地恢复记忆、live tool-calling trace、离线 scripted regression 边界 | `docs/CLI_CONTRACT.md`、`submission_artifacts/memory_cases/`、`submission_artifacts/agent_live_cases/agent_live_report.md`、`submission_artifacts/agent_decision_cases/README.md`、`submission_artifacts/recovery_effectiveness/recovery_effectiveness_report.md` |
| 系统稳定性与可复现性 | CI 中的 CLI smoke、trace 聚合、覆盖率、代码/测试摘要、提交 zip inventory | `.github/workflows/tests.yml`、`submission_artifacts/stability/stability_report.md`、`submission_artifacts/coverage/coverage_report.md`、`submission_artifacts/code_quality/code_quality_report.md`、`tests/test_submission_zip_inventory.py` |
| 开源共享与生态价值 | 仓库结构、CLI 契约、License、贡献指南、原创性说明、artifact 索引 | `README.md`、`docs/CLI_CONTRACT.md`、`LICENSE`、`CONTRIBUTING.md`、`docs/ORIGINALITY_AND_COMPLIANCE.md`、`submission_artifacts/ARTIFACTS_INDEX.md` |

## 5. 关键数字

| 指标 | 当前保存结果 | 来源 |
| --- | --- | --- |
| 带标注案例数 | 17 | `submission_artifacts/evaluation/evaluation_metrics.md` |
| 预期字段数 | 45 | `submission_artifacts/evaluation/evaluation_metrics.md` |
| 文本证据检查 | 22 | `submission_artifacts/evaluation/evaluation_metrics.md` |
| 数字证据检查 | 11 | `submission_artifacts/evaluation/evaluation_metrics.md` |
| 表格证据检查 | 6 | `submission_artifacts/evaluation/evaluation_metrics.md` |
| Live tool-calling Agent | 旧版 pre-skill-gate provider 包：8 次尝试、4 次 tool-call completed、2 次 answer-quality pass、0 个新版 skill-gated tool-validated rerun case | `submission_artifacts/agent_live_cases/agent_live_report.md` |
| 长文档分片 | NIST AI RMF 48 页，3 个分片，3/3 成功，58 个 retrieval chunks | `submission_artifacts/long_document_chunks/public_nist_ai_rmf_full_chunked/long_document_chunk_report.md` |
| LLM 预调度/复核用量 | 保存的 ModelScope 案例中 2 次调用、4309 tokens | `submission_artifacts/llm_cost/llm_cost_report.md` |
| Agent decision regression | 5 个离线本地案例，含子任务图、selected tools、质量后 replan 和 scripted decision hooks | `submission_artifacts/agent_decision_cases/README.md` |
| Recovery 聚合 | 保存结果中的 recovery 记录、执行次数、非初始结果选择次数和 issue-code 分布 | `submission_artifacts/recovery_effectiveness/recovery_effectiveness_report.md` |
| Controlled failure/recovery | text cleanup、OCR retry 成功/失败、strict provenance failure、numeric mismatch | `submission_artifacts/failure_recovery_cases/README.md` |
| Retrieval validation | chunk schema、重复率、空 chunk、轻量 lexical top-3 query smoke | `submission_artifacts/retrieval_validation/retrieval_validation_report.md` |
| 覆盖率 | 本地 pytest 对 `src/mineru_data_agent` 的行覆盖率 | `submission_artifacts/coverage/coverage_report.md` |
| 代码/测试规模 | Python 文件、测试函数、GitHub Actions workflow | `submission_artifacts/code_quality/code_quality_report.md` |

## 6. Artifact 导航

使用 `submission_artifacts/ARTIFACTS_INDEX.md` 作为证据目录地图。该索引列出每类 artifact 的 result/trace 数量和主报告路径。

## 7. 当前边界

当前保存提交不包含公网生产压测、GPU 长文档 benchmark 或 OCR 字符/表格逐格 benchmark。`agent_decision_cases` 是 scripted decision client 的离线回归证据，不等同 live LLM 证据。保存的 live-provider 证据分为两类：`submission_artifacts/llm_cases/` 中 1 个 ModelScope LLM 预调度/复核案例，以及 `submission_artifacts/agent_live_cases/` 中 8 次 tool-calling 尝试、4 次 finalize/tool-call completion、2 次人工复核 answer-quality pass。该 provider 包生成于 2026-05-25 skill/validation gate 之前，应视为旧版 live-provider 证据；若要证明新版 live Agent 的 `selected_skill` / `answer_validation` / tool-validated 能力，需要带 provider key 重新运行 `scripts/run_agent_live_cases.py`。可选 HTTP API 和 Docker 文件是二级集成材料，不是主评审面。
