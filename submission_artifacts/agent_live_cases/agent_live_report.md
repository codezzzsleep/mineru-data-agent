# Live LLM Agent — Decision Trace Attempts

This report separates live provider tool-call completion from semantic answer quality.
A case counts as tool-call evidence when it reached completed, used provider tokens, and called finalize; it counts as semantic success only when answer_quality_pass=true after manual review.

Boundary: this saved provider pack is `legacy_pre_skill_gate`. It was generated
before the 2026-05-25 skill-guided validation gate, so it is live-provider
evidence for the older tool-calling loop, not proof that the newer
`select_skill -> parse -> validate_answer -> finalize` gate has completed a
provider rerun.

## Summary

- Provider: **modelscope**
- Model: **Qwen/Qwen3-235B-A22B-Instruct-2507**
- Evidence generation: **legacy_pre_skill_gate**
- Total attempted cases: **8**
- Tool-call completed cases: **4**
- Skill-gated tool-validated cases: **0**
- Answer-quality pass cases: **2**
- Answer-quality questionable cases: **2**
- Failed or incomplete cases: **4**
- Total attempted tokens: **61,890**
- Tool-call completed tokens: **59,366**
- Answer-quality pass tokens: **30,938**

## Cases

| # | Case | Tool-call completed | Answer-quality pass | Status | Turns | Tokens | Tool sequence |
| - | --- | --- | --- | --- | ---: | ---: | --- |
| 1 | 196d0a9ab359 | false | unreviewed | failed | 1 | 0 | - |
| 2 | 37a26944b806 | false | unreviewed | failed | 1 | 0 | - |
| 3 | 51095c378826 | true | true | completed | 7 | 13,230 | parse_html -> build_extracted -> validate_quality -> query_extracted -> query_extracted -> export_retrieval -> finalize |
| 4 | 6e4c38424514 | true | true | completed | 10 | 17,708 | parse_html -> build_extracted -> validate_quality -> clean_text -> build_extracted -> validate_quality -> query_extracted -> query_extracted -> export_retrieval -> finalize |
| 5 | aacfcda3d359 | false | unreviewed | failed | 1 | 0 | - |
| 6 | b09a230d6597 | true | false | completed | 8 | 15,724 | parse_html -> build_extracted -> validate_quality -> query_extracted -> query_extracted -> query_extracted -> export_retrieval -> finalize |
| 7 | f8931594641b | false | unreviewed | failed | 3 | 2,524 | parse_html -> build_extracted |
| 8 | f93eb9dcdc0d | true | false | completed | 8 | 12,704 | parse_html -> build_extracted -> validate_quality -> query_extracted -> query_extracted -> query_extracted -> export_retrieval -> finalize |

## Per-case detail

### 196d0a9ab359

- Input: case_6_cross_page_financial_table.html
- Task: 这份财报有跨页合并的表格。请抽取完整表格，并验证：跨页延续行是否被正确合并？合计是否跨页一致？
- Tool-call completed: false
- Answer-quality pass: unreviewed
- Answer-quality note: not applicable; case did not reach finalize with provider tokens
- Status: failed (turns=1, tokens=0)
- Trace: submission_artifacts/agent_live_cases/196d0a9ab359/live_agent_trace.json
- Error boundary: quota/HTTP failure retained in JSON report; not counted as semantic evidence.

### 37a26944b806

- Input: case_7_noisy_contract_scan.html
- Task: 这是噪声扫描合同。提取签署日期、双方主体、争议解决条款；如果某项被签章遮挡或乱码无法识别，标注为 unreadable
- Tool-call completed: false
- Answer-quality pass: unreviewed
- Answer-quality note: not applicable; case did not reach finalize with provider tokens
- Status: failed (turns=1, tokens=0)
- Trace: submission_artifacts/agent_live_cases/37a26944b806/live_agent_trace.json
- Error boundary: quota/HTTP failure retained in JSON report; not counted as semantic evidence.

### 51095c378826

- Input: case_1_financial_report.html
- Task: 请告诉我这份财报中 2025Q3 的营业收入。如果文档不包含该季度数据，请明确说明 not_found 并给出文档实际包含的季度
- Tool-call completed: true
- Answer-quality pass: true
- Answer-quality note: Manual review: correct not_found answer for 2025Q3; cites available 2026Q1 and 2025Q4 quarters.
- Status: completed (turns=7, tokens=13,230)
- Trace: submission_artifacts/agent_live_cases/51095c378826/live_agent_trace.json
- Tool calls: parse_html -> build_extracted -> validate_quality -> query_extracted -> query_extracted -> export_retrieval -> finalize

Final answer preview:

not_found。文档中未包含2025Q3的营业收入数据。实际包含的最近两个季度为2026Q1和2025Q4。


### 6e4c38424514

- Input: case_2_low_quality_ocr.html
- Task: 解析这份低质量 OCR 巡检报告。如果发现编码噪声/乱码（锟斤拷之类），先调用 clean_text 恢复，然后再抽取设备 B-17 的异常温度信息
- Tool-call completed: true
- Answer-quality pass: true
- Answer-quality note: Manual review: correct extraction of B-17 abnormal temperature after clean_text recovery.
- Status: completed (turns=10, tokens=17,708)
- Trace: submission_artifacts/agent_live_cases/6e4c38424514/live_agent_trace.json
- Tool calls: parse_html -> build_extracted -> validate_quality -> clean_text -> build_extracted -> validate_quality -> query_extracted -> query_extracted -> export_retrieval -> finalize

Final answer preview:

设备 B-17 的异常温度为 86.5 摄氏度，超过设定阈值 80 摄氏度。该信息已在 OCR 复核记录中明确提示，需人工复核原图确认。


### aacfcda3d359

- Input: case_5_web_inspection_report.html
- Task: 从这份网页巡检日报中抽取出所有键值对（指标名 → 当前值 → 阈值），用 markdown 表格输出，并标记超阈值项
- Tool-call completed: false
- Answer-quality pass: unreviewed
- Answer-quality note: not applicable; case did not reach finalize with provider tokens
- Status: failed (turns=1, tokens=0)
- Trace: submission_artifacts/agent_live_cases/aacfcda3d359/live_agent_trace.json
- Error boundary: quota/HTTP failure retained in JSON report; not counted as semantic evidence.

### b09a230d6597

- Input: case_1_financial_report.html
- Task: 识别这份 HTML 财报中 2026Q1 的营业收入和利润总额，验证合计行是否与明细一致，列出任何异常
- Tool-call completed: true
- Answer-quality pass: false
- Answer-quality note: Manual review: final answer is self-contradictory about whether 25,721.00 equals the listed item sum; keep as tool-call evidence only.
- Status: completed (turns=8, tokens=15,724)
- Trace: submission_artifacts/agent_live_cases/b09a230d6597/live_agent_trace.json
- Tool calls: parse_html -> build_extracted -> validate_quality -> query_extracted -> query_extracted -> query_extracted -> export_retrieval -> finalize

Final answer preview:

2026Q1 营业收入为 12,860.50 万元，利润总额为 3,033.75 万元。经核验，合计行（25,721.00）不等于明细项之和（12,860.50 + 8,430.25 + 615.30 + 781.20 + 3,033.75 = 25,721.00），但合计项包含了所有列出的明细项目，计算一致，无异常。


### f8931594641b

- Input: case_4_workflow_diagram.html
- Task: 梳理这份工艺流程的所有步骤，找出可能导致异常的关键节点，并按业务影响排序给出优先处理建议
- Tool-call completed: false
- Answer-quality pass: unreviewed
- Answer-quality note: not applicable; case did not reach finalize with provider tokens
- Status: failed (turns=3, tokens=2,524)
- Trace: submission_artifacts/agent_live_cases/f8931594641b/live_agent_trace.json
- Tool calls: parse_html -> build_extracted
- Error boundary: quota/HTTP failure retained in JSON report; not counted as semantic evidence.

### f93eb9dcdc0d

- Input: case_3_standard_contract.html
- Task: 从这份合同中提取所有甲方/乙方的关键义务条款，并指出哪一条最可能引发争议（基于条款措辞）
- Tool-call completed: true
- Answer-quality pass: false
- Answer-quality note: Manual review: final answer says not_found although contract responsibilities are present; keep as tool-call evidence only.
- Status: completed (turns=8, tokens=12,704)
- Trace: submission_artifacts/agent_live_cases/f93eb9dcdc0d/live_agent_trace.json
- Tool calls: parse_html -> build_extracted -> validate_quality -> query_extracted -> query_extracted -> query_extracted -> export_retrieval -> finalize

Final answer preview:

not_found: 文档中未明确列出甲方或乙方的‘义务’条款。合同包含以下内容：服务范围、数据安全、验收标准和异常处理，但未使用‘义务’一词，也未结构化定义双方责任。因此无法提取关键义务条款或判断争议点。


## Boundary

- tool_call_completed/live_evidence means a real provider call reached completed status, consumed tokens, and called finalize.
- answer_quality_pass is a separate manual-review field; only pass=true cases should be cited as semantic success examples.
- b09a230d6597 and f93eb9dcdc0d are retained as live tool-call traces but not counted as answer-quality passes.
