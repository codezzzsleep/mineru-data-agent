> Boundary: offline scripted decision regression. Token counts here are synthetic and should not be read as live provider usage.

# MinerU Data Agent Run 38961250fefc

- Task: 识别合同条款中的甲方、乙方、义务、例外条件和来源证据。
- Profile: standard_or_contract
- Execution method: auto
- Execution backend: pipeline
- LLM preplan applied changes: 0
- Input: `<PROJECT_ROOT>\examples\cases\case_3_standard_contract.html`
- Quality: pass (100/100)
- Content blocks: 12
- Pages with provenance: 0
- Provenance level: document
- Sections: 5
- Tables: 0
- Key-values: 7
- Field evidence records: 7
- Numeric facts: 1
- Dates detected: 1
- Recommendation signals: 2
- Anomaly signals: 3
- Retrieval chunks: 5
- Recovery decision: accept
- Recovery selected attempt: initial
- Recovery attempts: 1
- Task intents: entity_resolution, evidence_trace
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
9. Prioritize section hierarchy, clause-like paragraphs, parties, obligations, and dates
10. Preserve source page or document heading evidence for each clause
11. Apply task intent `entity_resolution` with schema-aware extraction and verification
12. Apply task intent `evidence_trace` with schema-aware extraction and verification
13. LLM preplan: Decompose task into extraction, validation, and recovery decisions
14. LLM preplan: Select tools based on profile, provenance need, and quality risks

## Planning Rationale
- standard/contract keywords or explicit profile require section and clause preservation
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
- Intents: entity_resolution, evidence_trace
- Target schema keys: document_title, parties, clause_id, obligation, effective_date, evidence, 甲方, 乙方, 义务, 例外条件
- Quality thresholds: {"min_quality_score": 88, "require_tables": false, "require_numeric_facts": false, "prefer_page_provenance": false}
- Recovery strategy:
  - text_cleanup on mojibake_or_encoding_noise (normal)
  - llm_suggested_review on manual review if party field is missing (advisory)

## Agent Action Plan
- Subtasks: 7
- Selected tools: native_extractor, llm_preplanner, structured_extractor, contract_validator, text_cleanup, llm_post_review, retrieval_exporter
- understand_task: Classify the document task and identify intent-specific outputs.
- choose_parse_path: Pick the cheapest parser path that still preserves required provenance.
- extract_structure: Normalize sections, tables, key-values, numeric facts, and field evidence.
- validate_quality: Run profile and task-specific gates before accepting the result.
- llm_review: Review parse output against task-specific risks and propose follow-up actions.
- replan_if_needed: Map quality issues to recovery actions and select the best attempt.

## Runtime Recovery Plan
- Initial issue codes: document_level_provenance
- llm_suggested_review: skipped for llm_suggested (llm_post_review.recovery_suggestions)

## Agent Replan After Quality
- Issue codes: document_level_provenance
- Attempted actions: initial
- Selected reason: initial result remained the best accepted quality attempt

## Task-Specific Answers

## LLM Agent Analysis

Pre-execution control: profile=standard_or_contract, runner=native, method=auto, backend=pipeline

识别合同条款中的甲方、乙方、义务、例外条件和来源证据。

LLM usage: 1460 tokens across 2 call(s); estimated cost=None

Suggested execution plan:
1. Review quality issues
2. Map issue codes to replan actions

## Extracted Fields
- 合同编号: DPA-2026-0519
- 签署日期: 2026-05-19
- 异常提示: 跨页表格、签章覆盖和乱码文本需要进入人工复核队列。
- 处理建议: 保留章节标题、条款编号和源文件证据，便于合规审计。
- 第一条 服务范围: 乙方负责对甲方提供的 PDF、HTML、Word 与扫描图片进行解析、清洗、结构化抽取和质量复核。
- 第二条 数据安全: 乙方不得将甲方原始文件、API 密钥或中间处理结果用于合同外目的，日志中不得记录敏感密钥。
- 第三条 验收标准: 验收以结构化 JSON、执行 trace、质量报告和可复跑命令为准；若发现关键字段缺失，应在 2 个工作日内补正。

## Field Evidence
- 合同编号: confidence=0.86, location=3, evidence=合同编号：DPA-2026-0519
- 签署日期: confidence=0.86, location=5, evidence=签署日期：2026-05-19
- 异常提示: confidence=0.86, location=21, evidence=异常提示：跨页表格、签章覆盖和乱码文本需要进入人工复核队列。
- 处理建议: confidence=0.86, location=23, evidence=处理建议：保留章节标题、条款编号和源文件证据，便于合规审计。
- 第一条 服务范围: confidence=0.86, location=document, evidence=## 第一条 服务范围

## Recommendation Evidence
- 处理建议: 保留章节标题、条款编号和源文件证据，便于合规审计。
- 处理建议：保留章节标题、条款编号和源文件证据，便于合规审计。

## Recovery Decision
- Decision: accept
- Native extractor result has document/slide-level provenance; use PDF/MinerU path for page-layout audit.
- LLM suggested: manual review if party field is missing

Attempts:
- initial: pass (100/100), selected

## Issues
- [info] document_level_provenance: Native document input has document-level provenance rather than page-level provenance.

## Markdown Preview

# 数据处理服务合同关键条款

合同编号：DPA-2026-0519

签署日期：2026-05-19

## 第一条 服务范围

乙方负责对甲方提供的 PDF、HTML、Word 与扫描图片进行解析、清洗、结构化抽取和质量复核。

## 第二条 数据安全

乙方不得将甲方原始文件、API 密钥或中间处理结果用于合同外目的，日志中不得记录敏感密钥。

## 第三条 验收标准

验收以结构化 JSON、执行 trace、质量报告和可复跑命令为准；若发现关键字段缺失，应在 2 个工作日内补正。

## 第四条 异常处理

异常提示：跨页表格、签章覆盖和乱码文本需要进入人工复核队列。

处理建议：保留章节标题、条款编号和源文件证据，便于合规审计。
