# LLM Cost Report

LLM token and cost audit over saved submission artifacts.

## Aggregate

- LLM-enabled results: 2
- LLM trace tool calls: 3
- Tool calls with token usage: 0
- Results with token usage: 0
- Prompt tokens: 0
- Completion tokens: 0
- Total tokens: 0
- Cost-configured tool calls: 0
- Estimated cost USD: None

## LLM Results

| Result | Status | Usage Items | Has Tokens | Has Cost |
| --- | --- | ---: | --- | --- |
| submission_artifacts/llm_cases/case_llm_financial_review/result.json | completed | 0 | no | no |
| submission_artifacts/recovery_cases/case_pdf_llm_api_to_cli_fallback/result.json | completed | 0 | no | no |

## LLM Tool Calls

| Trace | Tool | Status | Tokens | Cost USD |
| --- | --- | --- | ---: | ---: |
| submission_artifacts/llm_cases/case_llm_financial_review/trace.json | modelscope-llm | completed | 0 | None |
| submission_artifacts/recovery_cases/case_pdf_llm_api_to_cli_fallback/trace.json | offline-llm-preplan | completed | 0 | None |
| submission_artifacts/recovery_cases/case_pdf_llm_api_to_cli_fallback/trace.json | offline-llm | completed | 0 | None |

## Pricing Configuration

- Provider-specific env vars: `MINERU_DATA_AGENT_DEEPSEEK_INPUT_USD_PER_MILLION_TOKENS`, `MINERU_DATA_AGENT_DEEPSEEK_OUTPUT_USD_PER_MILLION_TOKENS`, `MINERU_DATA_AGENT_MODELSCOPE_INPUT_USD_PER_MILLION_TOKENS`, `MINERU_DATA_AGENT_MODELSCOPE_OUTPUT_USD_PER_MILLION_TOKENS`
- Generic env vars: `MINERU_DATA_AGENT_LLM_INPUT_USD_PER_MILLION_TOKENS`, `MINERU_DATA_AGENT_LLM_OUTPUT_USD_PER_MILLION_TOKENS`

## Boundary

- New LLM runs record provider-returned token usage when the OpenAI-compatible API includes a usage object.
- Cost is computed only when token prices are configured through environment variables.
- Older saved LLM artifacts may show enabled LLM execution but missing token usage because they were generated before this instrumentation existed.
- This report does not claim a live DeepSeek/ModelScope cost benchmark unless saved artifacts contain provider usage.
