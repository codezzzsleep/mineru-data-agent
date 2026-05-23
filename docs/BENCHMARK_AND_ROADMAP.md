# Benchmark and Roadmap

This document answers two reviewer questions:

1. What is this project compared against?
2. What remains to be proven before making stronger accuracy or production claims?

## 1. Current Evidence Position

The current submission focuses on a MinerU-based Data Agent with saved artifacts for:

- task planning and profile routing
- online API / local CLI / native Office and HTML execution paths
- traceable result, summary, retrieval, and recovery artifacts
- lightweight labeled evaluation across saved cases
- live local HTTP API smoke testing

Current labels cover selected key fields, text evidence, numeric evidence, table fragments, profile routing, quality gates, provenance gates, and recovery gates. OCR character-level and table cell-level benchmark labels can be added with the schema below.

## 2. Baseline Matrix

The next formal benchmark should compare the same documents and labels across these baselines:

| Baseline | Purpose | Expected Strength | Expected Weakness |
| --- | --- | --- | --- |
| Raw MinerU output only | Measures value added by the Agent layer | Strong OCR/layout extraction | No task planning, recovery policy, schema audit, or field evidence normalization |
| MinerU Data Agent without LLM | Measures deterministic pipeline quality and cost | Stable and cheap; easy to reproduce | Less flexible schema alignment and semantic risk review |
| MinerU Data Agent with LLM | Measures LLM scheduling/review lift | Better schema suggestions, validation focus, and risk review | Requires token/cost tracking and live key availability |
| Direct LLM extraction from text | Tests whether tool-first Agent is needed | Flexible schema generation | Higher hallucination/provenance risk; harder to audit |
| Marker or similar parser | External parser baseline for PDF-to-Markdown | Good open-source comparison point | Different artifact contract; may not preserve same provenance |
| PyMuPDF/PyPDF2 text extraction | Minimal low-cost baseline | Very cheap and fast | Weak tables, layout, scans, and OCR |

The repository now includes `submission_artifacts/baseline_comparison/`, but that report is a saved-artifact tradeoff view, not the full external baseline matrix above.

## 3. Real-Document Benchmark Target

For an award-focused follow-up, use a compact but stronger public benchmark:

| Track | Target Size | Required Labels | Primary Metrics |
| --- | ---: | --- | --- |
| Financial reports | 20-30 PDFs | company, period, key line items, totals/subtotals, table headers, evidence pages | field accuracy, numeric recall, total-check precision, table fragment accuracy |
| Low-quality scans | 10-20 PDFs/images | document id/date, critical fields, noisy spans, recovery expected action | recovery lift, field accuracy before/after recovery, manual-review trigger precision |
| Contracts/standards | 10-20 PDFs/DOCX | clause ids, effective dates, parties/owners, obligations, exception terms | field accuracy, section recall, provenance coverage |
| Workflow/diagram reports | 5-10 PDFs/PPTX | process nodes, risk points, responsible role, action item | structural recall, evidence coverage, manual visual-review trigger precision |

Minimum metric set:

- field-level accuracy
- text evidence recall
- numeric evidence recall
- table fragment or cell-level accuracy where labels permit it
- page-level provenance coverage
- recovery execution rate and recovery lift
- average runtime per document and per page
- LLM calls, tokens, and cost per document when LLM is enabled

## 4. LLM Cost Roadmap

The code now records LLM usage when the OpenAI-compatible provider returns a `usage` object. Cost is computed only when token price environment variables are configured.

Recommended live evaluation setup:

```bash
export MINERU_DATA_AGENT_DEEPSEEK_INPUT_USD_PER_MILLION_TOKENS="<input-price>"
export MINERU_DATA_AGENT_DEEPSEEK_OUTPUT_USD_PER_MILLION_TOKENS="<output-price>"
export DEEPSEEK_API_KEY="<key>"
```

Then run a fixed benchmark set twice:

1. `--llm none`
2. `--llm deepseek`

Compare:

- accuracy lift
- recovery lift
- additional latency
- token count
- estimated cost per document

Current saved artifacts include older LLM runs that predate token instrumentation. Regenerating those cases with live provider responses fills the token and cost fields.

## 5. Engineering Roadmap

Near-term items with high competition value:

1. Regenerate the LLM case with a live DeepSeek/ModelScope key so `llm_usage` and cost appear in trace and result artifacts.
2. Add 10-20 more public real PDFs with lightweight but explicit labels.
3. Add at least one field-level financial table benchmark with totals/subtotals.
4. Run one long PDF with local MinerU CLI in a GPU environment and report pages/second.
5. Run a real HTTP API test with at least 100 requests and concurrency 20 on HeyWhale or another reachable service.

Medium-term maintainability items:

1. Move profile-specific validation thresholds into declarative config.
2. Add a plugin-like profile extension guide.
3. Add external baselines for raw MinerU, PyMuPDF/PyPDF2 text, Marker, and direct LLM extraction.
4. Publish a small benchmark label schema for community contributions.

## 6. Next Measurements

The following measurements would support stronger public claims:

- OCR character-level accuracy
- table cell-level benchmark results
- public internet production load capacity
- GPU high-throughput stability
- live full-chain LLM + MinerU CLI recovery in the target environment

The benchmark and live runs above define how to collect those measurements.
