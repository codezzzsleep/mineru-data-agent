# API Contract

This document is the stable interface surface intended for competition review scripts.

## Health

`GET /health`

Response:

```json
{
  "status": "healthy",
  "version": "0.1.0"
}
```

## Parse

`POST /v1/parse` with `multipart/form-data`.

Required fields:

| Field | Type | Description |
| --- | --- | --- |
| `file` | file | PDF, image, HTML, DOCX, or PPTX input. |
| `task` | string | Natural-language data processing objective. |

Optional fields:

| Field | Default | Allowed / Meaning |
| --- | --- | --- |
| `profile` | `auto` | `auto`, `financial_report`, `standard_or_contract`, `workflow_or_diagram`, `low_quality_ocr`, `general_document` |
| `runner` | `cli` | `cli` or `agent-api` |
| `backend` | `pipeline` | MinerU backend when `runner=cli` |
| `method` | `auto` | MinerU parse method, usually `auto` or `ocr` |
| `lang` | `ch` | MinerU language hint |
| `api_max_retries` | `2` | `0..10` for online Agent API transient retry |
| `llm` | `none` | `none`, `deepseek`, `modelscope` |
| `llm_model` | unset | Provider model override |
| `llm_base_url` | provider default | Provider base URL override |
| `llm_timeout` | `60` | `0..600` seconds |
| `output_root` | `MINERU_DATA_AGENT_OUTPUT_DIR` or `runs/api` | Persistent output directory |
| `cli_fallback_on_no_page_provenance` | `true` | Enables local CLI fallback when online API lacks page provenance and a CLI is available |
| `fallback_mineru_executable` | unset | Explicit MinerU CLI path for fallback |

## Successful Response Schema

The response is the same JSON written to `result.json`, plus `api_output_root`.

Stable top-level fields:

| Field | Meaning |
| --- | --- |
| `run_id` | Stable run identifier. |
| `task` | Original task. |
| `profile` | Final profile after rule/LLM planning. |
| `input_file` | Saved input path. |
| `output_dir` | Persistent run directory. |
| `plan` | Ordered execution plan. |
| `execution_control` | Requested, initial, resolved, applied/ignored LLM control changes, and planning rationale. |
| `extracted` | Structured output: sections, tables, key-values, numeric facts, semantic signals, content summary. |
| `quality` | Rule-based quality status, score, issue list, and issue counts. |
| `recovery_decision` | Decision, actions, attempts, selected attempt, and initial issue codes. |
| `retrieval_export` | Paths and stats for `retrieval_chunks.jsonl`, manifest, and retrieval quality report. |
| `llm_analysis` | Optional pre-execution and post-parse LLM analysis. |
| `artifacts` | MinerU/native parser artifact paths. |
| `trace_path` | Full execution trace path. |
| `summary_path` | Human-readable run summary path. |

Evidence fields reviewers should inspect:

- `execution_control.planning_rationale`: why profile, runner, backend, method, language, and recovery policy were selected.
- `extracted.content_summary.provenance_level`: `page`, `document`, or `none`.
- `extracted.tables[*]`: headers, rows, `row_count`, `column_count`, source marker.
- `extracted.numeric_facts[*]`: line, text snippet, number tokens.
- `quality.issues[*].code`: machine-readable risk flags.
- `recovery_decision.attempts[*]`: initial/retry/fallback quality and artifact paths.
- `trace_path`: authoritative step/tool audit trail.

## Error Responses

| HTTP | `detail.error` | Cause |
| ---: | --- | --- |
| 400 | `invalid_runner` | `runner` is not `cli` or `agent-api`. |
| 400 | `invalid_llm` | `llm` is not `none`, `deepseek`, or `modelscope`. |
| 400 | `invalid_api_max_retries` | retry value outside `0..10`. |
| 400 | `invalid_llm_timeout` | timeout outside `0..600`. |
| 400 | `output_root_outside_allowed_base` | requested output directory violates `MINERU_DATA_AGENT_ALLOWED_OUTPUT_BASE`. |
| 400 | `empty_upload` | uploaded file has zero bytes. |
| 413 | `upload_too_large` | upload exceeds configured limit. |
| 500 | `parse_failed` | parser or agent execution failed. Includes `run_id`, `output_dir`, `trace_path`, `result_path`, and `summary_path` when available. |

## Review-Friendly cURL

```bash
curl -X POST http://127.0.0.1:8080/v1/parse \
  -F "file=@demo.pdf" \
  -F "task=Parse this PDF, extract tables, key facts, quality issues, and traceable retrieval chunks" \
  -F "runner=agent-api" \
  -F "profile=auto" \
  -F "api_max_retries=2"
```

## Current Boundary

This submission provides a local API and saved API smoke artifacts. It does not claim a permanently hosted public endpoint. For public deployment, set upload limits, output base restrictions, and external authentication/rate limiting at the gateway or reverse proxy layer.
