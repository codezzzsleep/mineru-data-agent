> Boundary: offline scripted decision regression. Token counts here are synthetic and should not be read as live provider usage.

# MinerU Data Agent Run c7cb56bc440c

- Task: 把流程图文档拆成步骤、责任角色、输入输出、异常触发条件，并标记需要视觉复核的节点。
- Profile: workflow_or_diagram
- Execution method: auto
- Execution backend: pipeline
- LLM preplan applied changes: 0
- Input: `<PROJECT_ROOT>\examples\cases\case_4_workflow_diagram.html`
- Quality: pass (100/100)
- Content blocks: 11
- Pages with provenance: 0
- Provenance level: document
- Sections: 2
- Tables: 0
- Key-values: 5
- Field evidence records: 5
- Numeric facts: 4
- Dates detected: 1
- Recommendation signals: 2
- Anomaly signals: 2
- Retrieval chunks: 2
- Recovery decision: accept
- Recovery selected attempt: initial
- Recovery attempts: 1
- Task intents: anomaly_detection
- LLM analysis: enabled/completed

## Plan
1. Inspect input type, document metadata, and natural-language task objective
2. Infer task intents and generate a target extraction schema
3. Choose MinerU/native parsing path and record execution rationale
4. Normalize content blocks with page-level or document-level provenance
5. Build markdown, section, key-value, table, numeric, and field-evidence views
6. Run task-specific post-processing and quality checks
7. Select recovery action from issue codes, retry history, and task priorities
8. Produce traceable result, summary, retrieval chunks, and audit logs
9. Prioritize figure/image references, ordered procedural statements, actors, inputs, and outputs
10. Flag pages that need visual model follow-up
11. Apply task intent `anomaly_detection` with schema-aware extraction and verification
12. LLM preplan: Decompose task into extraction, validation, and recovery decisions
13. LLM preplan: Select tools based on profile, provenance need, and quality risks

## Planning Rationale
- workflow/diagram keywords or explicit profile require procedural and figure evidence
- HTML/DOCX/PPTX inputs are handled by native extractors to preserve document structure without MinerU
- backend=pipeline is used for MinerU parsing when the selected runner calls MinerU
- method=auto balances automatic parsing with OCR fallback when quality gates require it
- lang=ch is passed to MinerU or recorded for native extraction audit
- Recovery policy:
  - text_cleanup if mojibake or encoding noise is detected
  - ocr_retry for PDF/image results with blocking extraction or OCR-related quality issues
  - cli_fallback when online API lacks page-level provenance and a local MinerU CLI is available
  - manual_numeric_review when subtotal/total consistency checks fail

## Adaptive Task Decision
- Intents: anomaly_detection
- Target schema keys: process_name, step, actor, input_output, risk, evidence, risk_reason, 步骤, 责任角色, 异常触发条件
- Quality thresholds: {"min_quality_score": 80, "require_tables": false, "require_numeric_facts": false, "prefer_page_provenance": false}
- Recovery strategy:
  - text_cleanup on mojibake_or_encoding_noise (normal)
  - llm_suggested_review on visual review if diagram evidence is missing (advisory)

## Agent Action Plan
- Subtasks: 7
- Selected tools: native_extractor, llm_preplanner, structured_extractor, workflow_validator, text_cleanup, llm_post_review, retrieval_exporter
- understand_task: Classify the document task and identify intent-specific outputs.
- choose_parse_path: Pick the cheapest parser path that still preserves required provenance.
- extract_structure: Normalize sections, tables, key-values, numeric facts, and field evidence.
- validate_quality: Run profile and task-specific gates before accepting the result.
- llm_review: Review parse output against task-specific risks and propose follow-up actions.
- replan_if_needed: Map quality issues to recovery actions and select the best attempt.

## Runtime Recovery Plan
- Initial issue codes: document_level_provenance

## Agent Replan After Quality
- Issue codes: document_level_provenance
- Attempted actions: initial
- Selected reason: initial result remained the best accepted quality attempt

## Task-Specific Answers
- Anomaly candidates: 2

## LLM Agent Analysis

Pre-execution control: profile=workflow_or_diagram, runner=native, method=auto, backend=pipeline

把流程图文档拆成步骤、责任角色、输入输出、异常触发条件，并标记需要视觉复核的节点。

LLM usage: 1460 tokens across 2 call(s); estimated cost=None

Suggested execution plan:
1. Review quality issues
2. Map issue codes to replan actions

## Extracted Fields
- 报告日期: 2026-05-20
- 流程名称: 正极浆料涂布与烘干流程
- 流程图说明: 投料 -> 搅拌 -> 过滤 -> 涂布 -> 烘干 -> 收卷 -> 质检。
- 异常提示: 若温区 3 连续 5 分钟超过 92 摄氏度，需暂停收卷并复核传感器。
- 处理建议: Agent 应抽取步骤顺序、关键参数、异常节点和待视觉模型复核的图像说明。

## Field Evidence
- 报告日期: confidence=0.86, location=3, evidence=报告日期：2026-05-20
- 流程名称: confidence=0.86, location=5, evidence=流程名称：正极浆料涂布与烘干流程
- 流程图说明: confidence=0.86, location=7, evidence=流程图说明：投料 -> 搅拌 -> 过滤 -> 涂布 -> 烘干 -> 收卷 -> 质检。
- 异常提示: confidence=0.86, location=19, evidence=异常提示：若温区 3 连续 5 分钟超过 92 摄氏度，需暂停收卷并复核传感器。
- 处理建议: confidence=0.86, location=21, evidence=处理建议：Agent 应抽取步骤顺序、关键参数、异常节点和待视觉模型复核的图像说明。

## Recommendation Evidence
- 处理建议: Agent 应抽取步骤顺序、关键参数、异常节点和待视觉模型复核的图像说明。
- 处理建议：Agent 应抽取步骤顺序、关键参数、异常节点和待视觉模型复核的图像说明。

## Recovery Decision
- Decision: accept
- Native extractor result has document/slide-level provenance; use PDF/MinerU path for page-layout audit.
- LLM suggested: visual review if diagram evidence is missing

Attempts:
- initial: pass (100/100), selected

## Issues
- [info] document_level_provenance: Native document input has document-level provenance rather than page-level provenance.

## Markdown Preview

# 锂电池涂布产线流程说明

报告日期：2026-05-20

流程名称：正极浆料涂布与烘干流程

流程图说明：投料 -> 搅拌 -> 过滤 -> 涂布 -> 烘干 -> 收卷 -> 质检。

## 关键步骤

- 投料阶段核对批次号和固含量。

- 搅拌阶段记录转速 1,200 rpm 和温度 25 摄氏度。

- 涂布阶段监控厚度 118 微米，允许偏差 3 微米。

- 烘干阶段检查温区 1 到温区 4 的温度曲线。

异常提示：若温区 3 连续 5 分钟超过 92 摄氏度，需暂停收卷并复核传感器。

处理建议：Agent 应抽取步骤顺序、关键参数、异常节点和待视觉模型复核的图像说明。
