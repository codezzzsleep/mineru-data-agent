# Optional API Contract

This document describes the optional local HTTP wrapper. The competition
submission is CLI-first; reviewers should treat `docs/CLI_CONTRACT.md` and the
`data-agent` command as the primary stable interface. The API is retained for
local integration tests and secondary engineering evidence.

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
| `runner` | `MINERU_DATA_AGENT_API_DEFAULT_RUNNER` or `agent-api` | `cli` or `agent-api` |
| `backend` | `pipeline` | MinerU backend when `runner=cli` |
| `method` | `auto` | MinerU parse method: `auto`, `ocr`, or `txt` |
| `lang` | `ch` | `ch` or `en` |
| `api_max_retries` | `2` | `0..10` for online Agent API transient retry |
| `llm` | `none` | `none`, `deepseek`, `modelscope` |
| `llm_model` | unset | Provider model override |
| `llm_timeout` | `60` | `0..600` seconds |
| `output_root` | `MINERU_DATA_AGENT_OUTPUT_DIR` or `runs/api` | Persistent output directory; always constrained by `MINERU_DATA_AGENT_ALLOWED_OUTPUT_BASE` |
| `cli_fallback_on_no_page_provenance` | `true` | Enables server-configured local CLI fallback when online API lacks page provenance and a CLI is available |
| `strict_page_provenance` | `false` | For PDF/image inputs, marks the result as `needs_review` with `strict_page_provenance_failed` if page-level provenance is still missing after recovery |

## Successful Response Schema

The response is the same JSON written to `result.json`, plus `api_output_root`.

Stable top-level fields:

| Field | Meaning |
| --- | --- |
| `schema_version` | Stable output schema contract version for downstream compatibility checks. |
| `run_id` | Stable run identifier. |
| `task` | Original task. |
| `profile` | Final profile after rule/LLM planning. |
| `input_file` | Saved input path. |
| `output_dir` | Persistent run directory. |
| `plan` | Ordered execution plan. |
| `execution_control` | Requested, initial, resolved, applied/ignored LLM control changes, planning rationale, adaptive task decision, agent action plan, and quality replan summary. |
| `extracted` | Structured output: sections, tables, key-values, field evidence, numeric facts, semantic signals, task result, content summary. |
| `quality` | Rule-based quality status, score, issue list, and issue counts. |
| `recovery_decision` | Decision, actions, attempts, selected attempt, initial issue codes, and optional LLM post-parse quality decision. |
| `retrieval_export` | Paths and stats for `retrieval_chunks.jsonl`, manifest, and retrieval quality report. |
| `llm_analysis` | Optional pre-execution and post-parse LLM analysis. |
| `artifacts` | MinerU/native parser artifact paths. |
| `trace_path` | Full execution trace path. |
| `summary_path` | Human-readable run summary path. |

Evidence fields reviewers should inspect:

- `execution_control.planning_rationale`: why profile, runner, backend, method, language, and recovery policy were selected.
- `execution_control.profile_inference`: configurable profile evidence, including keyword hits and lightweight deterministic token/character vector similarity. This is not a learned embedding model.
- `execution_control.adaptive_decision`: task intents, target schema, post-processors, quality thresholds, and recovery strategy chosen for this request.
- `execution_control.agent_action_plan`: subtask graph, selected tool registry, dynamic choices, replan triggers, and local memory policy.
- `execution_control.agent_action_plan.state_machine`: conditional DAG with dependency edges, quality-triggered recovery edges, runner/method changes, and loop policy.
- `execution_control.cross_run_memory`: local SQLite recovery statistics from previous runs under the same output root, disabled with `MINERU_DATA_AGENT_MEMORY=0`. This is deterministic statistics, not model fine-tuning or RL.
- `execution_control.runtime_recovery_plan`: recovery actions selected from the action plan, validator fallback policies, bounded LLM suggestions, and matching local memory recommendations before automatic recovery attempts are executed.
- `execution_control.replan_after_quality`: quality issue codes, considered actions, attempted actions, selected attempt, and next action if risk remains.
- `execution_control.strict_page_provenance`: whether strict page provenance was requested, whether it applied to this file type, and whether the final result satisfied it.
- `extracted.content_summary.provenance_level`: `page`, `document`, or `none`.
- `extracted.field_evidence[*]`: key, value, confidence proxy, evidence text, and line/page/block provenance when available.
- `extracted.task_result`: task-specific answers derived from the adaptive decision, such as growth ranking candidates, anomaly candidates, entity candidates, or evidence lists.
- `extracted.tables[*]`: headers, rows, `row_count`, `column_count`, source marker, optional header levels and inferred merged-cell metadata.
- `extracted.numeric_facts[*]`: line, text snippet, number tokens.
- `extracted.cross_page_references[*]`: detected references such as page/table/context references, with source section/page and target hints when resolvable.
- `quality.issues[*].code`: machine-readable risk flags.
- `recovery_decision.attempts[*]`: initial/retry/fallback quality and artifact paths.
- `recovery_decision.llm_quality_decision`: LLM post-parse risk counts, findings, suggested actions, and applied decision effects when LLM is enabled.
- `trace_path`: authoritative step/tool audit trail.

## Async Jobs

Use this path for longer documents or committee scripts that prefer polling.

`POST /v1/jobs` accepts the same `multipart/form-data` fields as `/v1/parse`.

Response:

```json
{
  "job_id": "0123456789abcdef0123456789abcdef",
  "status": "queued",
  "status_url": "/v1/jobs/0123456789abcdef0123456789abcdef"
}
```

`GET /v1/jobs/{job_id}` returns:

| Field | Meaning |
| --- | --- |
| `job_id` | Stable async job identifier. |
| `status` | `queued`, `running`, `completed`, or `failed`. |
| `created_at` / `started_at` / `ended_at` | UTC timestamps. |
| `input_path` | Saved upload path. |
| `output_root` | Persistent output root. |
| `config` | Non-secret parse configuration. |
| `result` | Full parse response when completed. |
| `error` | Structured error detail when failed. |
| `job_path` | Persisted job record path. |

## Error Responses

| HTTP | `detail.error` | Cause | Suggested handling |
| ---: | --- | --- | --- |
| 400 | `request_field_not_allowed` | Request tried to set server-side deployment fields such as `llm_base_url`, `mineru_executable`, or `fallback_mineru_executable`. | Configure these on the server with environment variables instead. |
| 400 | `invalid_runner` | `runner` is not `cli` or `agent-api`. | Use `agent-api` for CPU review or `cli` when local MinerU is installed. |
| 400 | `invalid_profile` / `invalid_backend` / `invalid_method` / `invalid_lang` | Parse option outside the documented allowlist. | Use the documented enum values. |
| 400 | `invalid_task` | Task is empty or too long. | Send a concise non-empty objective. |
| 400 | `invalid_llm` | `llm` is not `none`, `deepseek`, or `modelscope`. | Use `none` for deterministic runs unless provider credentials are configured. |
| 400 | `invalid_api_max_retries` | retry value outside `0..10`. | Lower retry count and rerun. |
| 400 | `invalid_llm_timeout` | timeout outside `0..600`. | Lower timeout and rerun. |
| 400 | `output_root_outside_allowed_base` | requested or server-default output directory violates `MINERU_DATA_AGENT_ALLOWED_OUTPUT_BASE`. | Choose an output root under the configured base directory. |
| 400 | `empty_upload` | uploaded file has zero bytes. | Re-upload a non-empty document. |
| 413 | `upload_too_large` | upload exceeds configured limit. | Split the file or raise the deployment upload limit. |
| 415 | `unsupported_upload_suffix` | Upload filename suffix is not one of PDF/image/HTML/DOCX/PPTX. | Upload a supported document type. |
| 404 | `job_not_found` | async job id was not found. | Check the job id or resubmit the job. |
| 500 | `parse_failed` | parser or agent execution failed. Includes `run_id`, `output_dir`, `trace_path`, `result_path`, and `summary_path` when available. | Inspect `trace_path`; if parser artifacts exist, treat the result as partial evidence and rerun with a safer runner or lower concurrency. |

Quality and recovery risks are returned with HTTP 200 when a parse completes but should not be auto-accepted. Examples include `no_page_provenance`, `strict_page_provenance_failed`, `short_text`, `possible_mojibake`, and `numeric_total_mismatch`.

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

This submission provides a local deterministic/LLM-preplan API and saved API smoke artifacts. It does not claim a permanently hosted public endpoint. The live tool-calling Agent is exposed only as the CLI command `data-agent agent-run`, not as an HTTP endpoint. Request-level LLM base URL, API key, and local executable overrides are deliberately rejected; configure provider endpoints and MinerU executables only on the server or local CLI environment. For public deployment, set upload limits, output base restrictions, and external authentication/rate limiting at the gateway or reverse proxy layer.
