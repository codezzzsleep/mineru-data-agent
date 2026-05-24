# CLI Contract

This project is submitted as a CLI-first MinerU Data Agent. Reviewers should
use the `data-agent` command as the stable interface. The HTTP API is an
optional wrapper and is not the primary competition surface.

## Commands

### `data-agent run`

Parse one document and write a run directory containing:

- `result.json`
- `trace.json`
- `summary.md`
- `retrieval/retrieval_chunks.jsonl`
- `retrieval/retrieval_manifest.json`

Example:

```bash
data-agent run \
  --input examples/cases/case_1_financial_report.html \
  --out runs/cli_demo \
  --task "抽取财报关键字段并检查合计行" \
  --profile auto
```

For PDF inputs in a CPU-only review environment, use the MinerU online Agent API
through the CLI:

```bash
data-agent run \
  --runner agent-api \
  --input demo.pdf \
  --out runs/pdf_api \
  --task "解析 PDF 并输出结构化结果和质量日志"
```

For audit-grade PDF artifacts and page-level provenance, use a local MinerU CLI
environment:

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

Run a JSON manifest. One failed task does not stop the whole batch.

```bash
data-agent batch \
  --manifest examples/batch_manifest.json \
  --out runs/batch_demo
```

The batch directory writes `batch_report.json` plus per-task run directories.

### `data-agent agent-run`

Run the live OpenAI-compatible tool-calling Agent path. Provider keys are read
only from environment variables and are not written to artifacts.

```bash
data-agent agent-run \
  --provider modelscope \
  --input examples/cases/case_2_low_quality_ocr.html \
  --out runs/agent_live \
  --task "发现乱码后先清理，再抽取设备 B-17 的异常温度"
```

The command writes:

- `result.json`
- `live_agent_trace.json`
- `live_agent_summary.md`

Evidence semantics:

- The live Agent is **skill-guided**: the LLM must call `select_skill` to choose
  a high-level strategy before executing tools, and it may switch skills if the
  evidence contradicts the initial plan.
- Current skills include `financial_total_audit`, `not_found_guard`,
  `text_recovery_then_extract`, `contract_clause_review`,
  `workflow_risk_review`, and `structured_extraction`.
- The LLM must call `validate_answer` before `finalize`. This tool checks
  unsupported numbers, simple arithmetic contradictions, missing evidence, and
  selected-skill not_found conflicts.
- The tool layer enforces the minimum loop: tools other than `select_skill` are
  rejected until a skill is selected, `validate_answer` is rejected until a
  document has been parsed, and `finalize` is rejected unless the exact answer
  and exact evidence list were already validated.
- `tool_call_completed=true`: a real provider call reached `finalize`, consumed
  provider tokens, and produced a completed trace.
- `answer_validation.ok=true`: built-in validation passed. This improves the
  evidence trail but still does not replace manual or benchmark review.
- `answer_quality_pass=true`: separate manual or benchmark review says the final
  answer is semantically correct.
- Tool-call completion must not be cited as semantic success unless
  `answer_quality_pass=true`.

## Stable Output Fields

Review scripts should inspect these top-level `result.json` fields:

| Field | Meaning |
| --- | --- |
| `schema_version` | Output schema version for compatibility checks. |
| `run_id` | Stable run identifier. |
| `task` | User task. |
| `profile` | Final profile selected by deterministic profile inference and optional LLM review. |
| `execution_control` | Planning rationale, action plan, memory, recovery plan, and applied/ignored controls. |
| `extracted` | Structured sections, tables, key-values, numeric facts, semantic signals, and task result. |
| `quality` | Quality status, score, issue codes, and warnings. |
| `recovery_decision` | Recovery attempts, selected attempt, and reason trail. |
| `retrieval_export` | Retrieval chunk paths and stats. |
| `trace_path` | Full execution trace. |
| `summary_path` | Human-readable run summary. |

## Non-Goals

- No public hosted API is required for the CLI submission.
- Saved API smoke/load artifacts are secondary engineering evidence only.
- Offline scripted decision cases are regression fixtures, not live LLM evidence.
- The saved live-agent pack currently contains 8 attempted provider runs, 4
  tool-call completions, and 2 manually reviewed answer-quality pass examples.
  It was generated before the stricter 2026-05-25 skill/validation gate, so it
  is legacy live-provider evidence, not proof that the new gate has completed a
  provider rerun.
