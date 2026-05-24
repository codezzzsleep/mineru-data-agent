# Cost / Speed / Quality Tradeoff

Generated: 2026-05-24T19:07:58Z

## Scenario Price Inputs (Illustrative May 2026)

- GPU scenario input: ¥8.00/hour
- MinerU Agent API scenario input: ¥0.15/page
- DeepSeek V4-Flash scenario input: ¥1.00/1M input, ¥2.00/1M output tokens
- Assumed PDF size: 10 pages
- ModelScope Qwen3-235B scenario input: ¥0 for quota-limited/free-tier runs
- MinerU沐曦 GPU scenario input: ¥0 for allocated competition resources
- Boundary: Illustrative May 2026 scenario inputs for sensitivity analysis; replace with current provider quotes before production cost planning. ModelScope free-tier and competition GPU assumptions are quota/resource dependent.

## Tradeoff Matrix

| Path | Quality evidence | Illustrative ¥ per 100 docs | Time per 100 docs | Page provenance | Recovery |
| --- | --- | ---: | --- | --- | --- |
| Native HTML/Office (rule-based, CPU) | saved-label pass on covered fixtures | 0.0 | < 1 | document-level | encoding noise / OCR retry (rule-triggered) |
| MinerU Agent API (online, CPU) | same parser quality as CLI but no page-level provenance | 150.0 | 5–15 | no (API returns inline markdown without page break markers) | CLI fallback if page provenance required |
| MinerU CLI (local, GPU) | saved-label pass on covered CLI fixtures, with page provenance | 11.0 | 8–20 (5s per page @ 10pp doc) | full (page-level markers, middle/model artifacts) | OCR retry for low-quality pages |
| MinerU CLI (沐曦 competition GPU, free) | same as CLI above | 0.0 | 8–20 | full | same as CLI above |
| LLM-enabled (DeepSeek V4-Flash) | LLM-assisted review path; quality must be judged from saved answer-quality fields, not assumed from token use | 0.31 | 10–30 (LLM adds 15–30s per doc) | depends on underlying parser | LLM-driven: reads validator codes, decides clean_text or reparse, replans |
| LLM-enabled (Qwen3 via ModelScope free) | same LLM-assisted path; quota and answer quality vary by run | 0.0 | 10–30 | depends on underlying parser | same LLM-driven as above |

## Ablation Attempt: Rule-based vs LLM-driven (same fixture)

### rule_based
- mode: rule_based
- elapsed_seconds: 0.35
- quality_score: 100
- quality_status: pass
- issue_count: 2
- extracted_sections: 2
- extracted_tables: 1
- has_llm_analysis: False

### llm_driven
- mode: llm_driven
- elapsed_seconds: 36.14
- agent_status: failed
- turns: 1
- tokens_prompt: 0
- tokens_completion: 0
- tokens_total: 0
- llm_cost_estimate_cny: 0.0
- has_final_answer: False
- evidence_count: 0

## Decision Tree

- **Input is HTML/DOCX/PPTX** → rule-based agent (free, fast)
- **PDF, need page provenance** → local MinerU CLI (GPU or 沐曦)
- **PDF, CPU-only, no audit** → MinerU Agent API (cost depends on current provider/page pricing)
- **Complex task** (semantic judgment, schema generation, compliance) → LLM-assisted agent with answer-quality review
  - **Quota-limited low-cost trial** → Qwen3 via ModelScope when free-tier quota is available
  - **Production** → price from current provider quote and observed token usage, not this illustrative table alone