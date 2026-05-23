# Case Studies

本提交包把案例证据分成九类，避免把轻量 fixture、合成文件或离线恢复演练结果包装成真实客户材料的广泛评测。

## 1. HTML/网页 Fixture 案例

这 5 个案例统一由 `examples/batch_manifest_5cases.json` 驱动，并通过 `scripts/run_submission_cases.ps1` 生成。每个案例目录都包含输入 fixture、`result.json`、`trace.json`、`summary.md` 和 `retrieval/` 导出文件。

边界说明：这些 HTML/网页案例是自构造 fixture，目标是验证 Agent 管线、质量校验、自动恢复、trace 和 retrieval 导出，不代表真实 PDF 的字段级或表格逐格准确率。表格中的 100 分是规则校验分，不是人工标注准确率。

案例输出位置：`submission_artifacts/cases/`

| Case | Profile | 质量 | 章节 | 表格 | 键值对 | 关键风险/亮点 |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `case_1_financial_report` | `financial_report` | 100 / `pass` | 2 | 1 | 5 | 标记 `numeric_total_verified`，同列金额合计可被规则核验；HTML 来源为 `document_level_provenance` |
| `case_2_low_quality_ocr` | `low_quality_ocr` | 100 / `pass` | 2 | 0 | 5 | 初始结果为 92 / `pass_with_warnings`，命中 `possible_mojibake` 后执行 `text_cleanup` 并择优；HTML 来源为 `document_level_provenance` |
| `case_3_standard_contract` | `standard_or_contract` | 100 / `pass` | 5 | 0 | 4 | 抽取合同编号、签署日期、章节条款和异常处理；HTML 来源为 `document_level_provenance` |
| `case_4_workflow_diagram` | `workflow_or_diagram` | 100 / `pass` | 2 | 0 | 5 | 抽取流程步骤、关键参数、异常节点和处理建议；HTML 来源为 `document_level_provenance` |
| `case_5_web_inspection_report` | `general_document` | 100 / `pass` | 2 | 1 | 3 | 抽取网页巡检日报、异常表格和处理建议；HTML 来源为 `document_level_provenance` |

复跑方式：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_submission_cases.ps1 -Python .\.venv\Scripts\python.exe
```

复跑后可查看：

- `submission_artifacts/cases/artifact_index.json`
- `submission_artifacts/cases/batch_report.json`
- `submission_artifacts/cases/<case_id>/result.json`
- `submission_artifacts/cases/<case_id>/trace.json`
- `submission_artifacts/cases/<case_id>/summary.md`
- `submission_artifacts/cases/<case_id>/retrieval/retrieval_chunks.jsonl`

## 2. PDF 文件级 MinerU CLI 案例

PDF 文件级案例位置：`submission_artifacts/mineru_cases/`

这些案例均来自本地 `mineru-cli` 完整运行，并保留输入 PDF、MinerU 中间文件、trace、summary、result 和 retrieval 导出。其中低质量扫描件来自 MinerU demo PDF；财报、合同和流程图样本是可公开提交的合成业务 PDF，用于增加文件级复杂场景覆盖，避免引入版权或隐私风险。

| Case | 场景 | 页数 | 内容块 | 表格 | 质量 | 工具耗时 |
| --- | --- | ---: | ---: | ---: | --- | ---: |
| `case_mineru_cli_low_quality_pdf` | 低质量扫描版 PDF | 8 | 66 | 0 | `pass` 100 | 217.947s |
| `case_mineru_cli_financial_pdf` | 财报密集数字表、负值、合计行 | 3 | 12 | 1 | `pass` 100 | 89.128s |
| `case_mineru_cli_contract_pdf` | 合同/标准条款、合规矩阵 | 2 | 15 | 1 | `pass` 100 | 82.932s |
| `case_mineru_cli_workflow_pdf` | 流程图、执行矩阵、图文混合 | 2 | 11 | 1 | `pass` 100 | 84.646s |

关键证据：

- `trace.json`：记录 `mineru-cli` 工具调用、状态和耗时。
- `result.json`：记录内容块、页级 provenance、结构化视图和质量报告。
- `mineru/`：保留 MinerU 原始 Markdown、content list、middle/model JSON、layout/span/origin PDF 和图片 artifact。
- `retrieval/`：保留 `retrieval_chunks.jsonl`、`retrieval_manifest.json` 和 `retrieval_quality.json`。
- `input.pdf`：保留本次案例输入副本，便于复查。
- `case_mineru_cli_financial_pdf/human_spot_check.md`：对财报 fixture 的关键行和合计行做 8/8 样本级人工核对。
- `case_mineru_cli_financial_pdf/mismatch_drill/`：故意把合计行改错，保存 `numeric_total_mismatch` 触发证据，证明规则不是永远报通过。

收集方式：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\collect_mineru_case.ps1 -RunDir runs\mineru_cli_refresh\4568109b3cc5
```

额外 PDF fixture 生成方式：

```powershell
$env:MINERU_ROOT="D:\path\to\MinerU"
$env:MINERU_ROOT\.venv\Scripts\python.exe .\scripts\generate_complex_pdf_fixtures.py
```

## 3. MinerU 在线 Agent API PDF 案例

在线 Agent API 案例位置：`submission_artifacts/agent_api_cases/case_agent_api_contract_pdf/`

该案例在 CPU 环境调用 MinerU 在线 Agent API 解析 `standard_contract_cross_page.pdf`，输出 Markdown、结构化章节、HTML 表格解析、质量报告、trace 和 retrieval chunks。由于在线 API 轻量路径不提供页级 provenance，质量状态为 `pass_with_warnings`，并在 `recovery_decision` 中明确建议需要页级审计时切换本地 MinerU CLI。

## 4. PDF LLM 预调度 + API-to-CLI Fallback 证据

Recovery 案例位置：`submission_artifacts/recovery_cases/case_pdf_llm_api_to_cli_fallback/`

该案例使用真实 PDF fixture `examples/real_pdfs/standard_contract_cross_page.pdf`，执行顺序为：解析前调度、在线 Agent API 首次解析、质量校验发现 `no_page_provenance`、自动触发 CLI fallback、选择页级 provenance 更完整的 `cli_fallback` 尝试。关键证据如下：

| 证据项 | 当前结果 |
| --- | --- |
| `llm_preplan_enabled` | `true` |
| 初始问题码 | `no_page_provenance` |
| `recovery_decision.executed` | `true` |
| `selected_attempt` | `cli_fallback` |
| 最终质量 | `pass` 100 |
| 最终 provenance | `page` |

边界必须如实说明：当前运行环境没有可用的 DeepSeek/ModelScope key，也没有可直接调用的本地 MinerU CLI 可执行文件，所以这个案例使用离线确定性预调度器和已保存的本地 CLI artifact 回放。它证明的是代码级自动 fallback、attempt 记录、择优和证据链闭合；若要做现场全链路演示，需要配置真实 LLM key 和 MinerU CLI。

## 5. DOCX/PPTX 文件级案例

Office 案例位置：`submission_artifacts/office_cases/`

| Case | 场景 | Provenance | 内容块 | 表格 | Retrieval chunks | 质量 |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `case_docx_standard_review` | Word 标准审查包、合规矩阵、风险建议 | document-level | 10 | 1 | 3 | `pass` 100 |
| `case_pptx_workflow_review` | PowerPoint 工作流汇报、执行矩阵、风险建议 | 3 slides | 7 | 1 | 4 | `pass` 100 |

关键证据：

- `result.json`：包含 DOCX/PPTX 的章节、表格、键值对、日期/风险/建议和 `recovery_decision`。旧证据会记录 initial attempt；新运行会在需要时写入自动恢复 attempts。
- `trace.json`：记录 `extract_docx` 或 `extract_pptx` 步骤。
- `office/`：保留原始文件副本、Markdown 和 content list。
- `retrieval/`：保留检索导出。

DOCX/PPTX 使用轻量 native extractor，而不是 MinerU CLI。其价值是覆盖赛题提到的 Word/PPT 文件类型；若评审需要版面级视觉 artifact，应优先参考 PDF/MinerU CLI 案例。

## 6. 挑战样本与人工标注表

挑战样本位置：`submission_artifacts/challenge_cases/`

这些样本由 `examples/challenge_manifest.json` 与 `scripts/run_challenge_cases.py` 生成，并额外保存 `human_annotation_table.md`。它们比基础 HTML fixture 更偏向评审会质疑的复杂形态，但仍是可公开提交的合成样本。

| Case | 场景 | 标注重点 | 当前结果 |
| --- | --- | --- | --- |
| `case_6_cross_page_financial_table` | 跨页风格财报明细，小计与总计分离 | Document ID、期间、Owner、合计/不一致风险 | `pass_with_warnings` 92，命中 `numeric_total_verified` 与 `numeric_total_mismatch` |
| `case_7_noisy_contract_scan` | OCR 噪声合同与编码污染 | Contract No、日期、cleanup recovery | `pass` 100，`recovery_decision.executed=true`，选中 `text_cleanup` |
| `case_8_industry_standard_matrix` | 行业标准合规矩阵 | Standard ID、Review Date、Owner、关键要求 | `pass` 100 |
| `case_9_incident_workflow_report` | 故障处置工作流与 fallback 时间线 | Incident ID、Report Date、System、fallback 动作 | `pass` 100 |

这些样本已纳入 `examples/evaluation/labels.json` 和 `submission_artifacts/evaluation/`，用于评测 17 个提交案例中的新增挑战维度。

## 7. 官方公开真实文档证据包

公开真实文档位置：`submission_artifacts/public_real_cases/`

这些案例由 `examples/public_real_documents/manifest.json` 和 `scripts/run_public_real_cases.py` 生成。它们使用官方公开来源，不是本项目合成 fixture；每个案例保存输入副本、`source_metadata.json`、`human_labels.json`、`result.json`、`trace.json`、`summary.md` 和 retrieval 导出。标签范围是样本级人工轻量标注和文本证据检查，不宣称完整 OCR 字符级或表格逐格准确率。

| Case | 官方来源 | 文档类型 | 标注重点 | 当前结果 |
| --- | --- | --- | --- | --- |
| `public_irs_w4_form` | Internal Revenue Service | W-4 表单 PDF | 标题、机构、年份、表单族、说明文本 | `pass_with_warnings` 76，22 个 retrieval chunks |
| `public_nist_ai_rmf` | National Institute of Standards and Technology | AI RMF 1.0 框架 PDF | 标题、NIST AI 100-1、发布日期、GOVERN/MAP/MEASURE/MANAGE 文本证据 | `pass_with_warnings` 92，23 个 retrieval chunks |
| `public_microsoft_annual_report` | U.S. SEC EDGAR | Microsoft 2024 Annual Report PDF exhibit | 公司、年报标题、财年、Revenue/Cash/Cloud 文本证据 | `pass_with_warnings` 76，48 个 retrieval chunks |
| `public_cdc_vis_instructions` | Centers for Disease Control and Prevention | VIS 使用说明 PDF | 主题、机构、法律语境、Required Use 文本证据 | `pass_with_warnings` 84，5 个 retrieval chunks |

边界说明：NIST 与 Microsoft 是长文档，当前通过在线 MinerU Agent API 跑前 20 页，`source_metadata.json` 中保留 `page_range`。4 个公开案例都因在线 API 轻量路径缺少页级 provenance 而保留 `no_page_provenance` warning，评审应把它看作外部真实材料兼容性证据，而不是页级审计能力的最终证明。

复跑方式：

```powershell
.\.venv\Scripts\python.exe .\scripts\run_public_real_cases.py
```

## 8. LLM-Enabled 财报复核案例

LLM 案例位置：`submission_artifacts/llm_cases/case_llm_financial_review/`

该案例使用 ModelScope OpenAI-compatible 接口调用 `deepseek-ai/DeepSeek-V4-Flash`。`trace.json` 中记录 `modelscope-llm completed`，`result.json` 中 `llm_analysis.enabled=true`。

LLM 在该案例中的职责是：

- 细化任务理解和执行计划。
- 生成目标 schema。
- 根据规则抽取与质量报告给出复核重点。
- 提供风险发现和恢复建议。

该案例输入仍是 HTML fixture，由本地 HTML 结构化模块解析。LLM 输出明确记录了这一点，避免把该案例包装成 MinerU PDF 解析证据。

当前代码已把 LLM 从单纯解析后复核前移到解析前调度。开启 `--llm deepseek` 或 `--llm modelscope` 时，trace 会新增 `llm_pre_execution_planning`，结果会新增 `execution_control` 和 `llm_analysis.pre_execution_plan`，记录模型建议的 profile、runner、backend、method、语言、目标 schema 和恢复策略；系统只应用安全白名单内且未被用户显式锁定的建议。

## 9. 带标注评测指标

评测报告位置：`submission_artifacts/evaluation/`

该报告由 `examples/evaluation/labels.json` 和 `scripts/build_evaluation_report.py` 生成，覆盖 17 个提交案例、45 个标注字段、22 条文本证据、11 条数字证据、6 条表格证据、profile 命中、结构门槛、质量门槛、provenance 门槛和 recovery 门槛。当前已保存结果：

- Expected-field accuracy: 100.0% (45/45)
- Text evidence accuracy: 100.0% (22/22)
- Numeric evidence accuracy: 100.0% (11/11)
- Table evidence accuracy: 100.0% (6/6)
- Profile accuracy: 100.0% (17/17)
- Structure gate pass rate: 100.0% (17/17)
- Quality gate pass rate: 100.0% (17/17)
- Provenance gate pass rate: 100.0% (17/17)
- Recovery gate pass rate: 100.0% (2/2)

该评测不是完整 OCR 字符级标注集，但能把关键字段、结构输出和可追溯性变成可复跑指标，补足“只有案例展示、没有指标”的短板。

## 10. 稳定性与耗时摘要

稳定性报告位置：`submission_artifacts/stability/`

该报告由 `scripts/build_stability_report.py` 生成，覆盖同一组 17 个提交案例，检查 result/trace 是否存在，统计 trace 步骤、工具调用、工具耗时、质量状态、provenance 分布和自动恢复执行。当前保存结果显示：

- Completed or inferred-completed traces: 17/17
- Total trace steps: 106
- Total tool calls: 11
- Total tool elapsed seconds: 240.107
- Max single-tool elapsed seconds: 89.128
- Recovery executed cases: 4
- Quality status counts: 12 个 `pass`，5 个 `pass_with_warnings`

边界说明：这是保存 artifact 的稳定性摘要，不是高并发压测。

## 11. 边界说明

当前证据已经能证明项目具备 HTML/网页结构化处理闭环、DOCX/PPTX 文件级结构化、批处理与 trace 机制，以及本地 MinerU CLI 后端对扫描件、财报表格、合同条款和流程图 PDF 的 artifact 产出能力。

但目前仍有明确缺口：

- PDF 文件级证据已扩展到 4 个，Office 文件级证据已扩展到 2 个，挑战 fixture 已扩展到 4 个，并新增 4 个官方公开真实 PDF 案例；但公开真实案例仍是轻量人工标注，还不足以证明真实客户材料的长期泛化能力。
- LLM 预调度已接入 profile/method/backend/lang 的安全控制，但 runner 的实际选择仍由部署参数控制，避免模型在运行中切换到当前环境不可用的后端。
- 已补“真实 PDF + 解析前调度 + recovery executed=true”的证据 artifact，但当前环境使用离线确定性预调度器和缓存 CLI artifact 回放；直播式全链路证据仍需要真实 DeepSeek/ModelScope key 和可调用 MinerU CLI。
- 当前 API smoke 已覆盖本地 HTML 上传和 PDF 上传；PDF 路径使用在线 Agent API，因此仍会保留 `no_page_provenance` 边界提示。
