# Baseline and Tradeoff Comparison

Saved-artifact cost/speed/quality comparison across runner families and scenario groups. This is not a third-party OCR benchmark.

## Overall

- Cases: 17
- Field accuracy: 100.0%
- Text evidence accuracy: 100.0%
- Numeric evidence accuracy: 100.0%
- Table evidence accuracy: 100.0%
- Total tool elapsed seconds: 240.107
- Recovery executed cases: 4
- Provenance distribution: `{"document": 13, "page": 4}`

## Group Comparison

| Group | Cases | Labeled Checks | Accuracy | Avg Quality | Tool Seconds | Avg Steps | Page Prov. | Recovery |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Native HTML/Web fixtures | 4 | 12/12 | 100.0% | 100.0 | 0.0 | 6.25 | 0/4 | 1/4 |
| MinerU CLI PDF with page provenance | 2 | 6/6 | 100.0% | 100.0 | 172.06 | 5.0 | 2/2 | 0/2 |
| Native Office files | 2 | 6/6 | 100.0% | 100.0 | 0.0 | 6.0 | 1/2 | 0/2 |
| LLM plan plus recovery fallback | 1 | 3/3 | 100.0% | 100.0 | 8.38 | 9.0 | 1/1 | 1/1 |
| Challenge fixtures | 4 | 12/12 | 100.0% | 98.0 | 0.0 | 6.25 | 0/4 | 1/4 |
| Public real PDFs via online API | 4 | 45/45 | 100.0% | 82.0 | 59.667 | 6.25 | 0/4 | 1/4 |

## Reviewer Reading

- Native HTML/Web fixtures: Low-cost deterministic parser path for task planning, schema, trace, and retrieval checks.
- MinerU CLI PDF with page provenance: Full local MinerU artifact path with page-level provenance and saved middle/layout/model files.
- Native Office files: DOCX/PPTX structure path for non-PDF enterprise material.
- LLM plan plus recovery fallback: Agent scheduling/recovery evidence: online API warning triggers CLI fallback and accepted recovery.
- Challenge fixtures: Stress fixtures for cross-page tables, OCR noise, industry matrices, and workflow incidents.
- Public real PDFs via online API: Official public PDF evidence for real-world formatting and text/table evidence gates.

## Boundary

- Accuracy is computed from lightweight human labels, not full OCR character error rate.
- Tool elapsed time is read from saved trace tool calls; native parsers can show zero external-tool seconds.
- The comparison helps reviewers see tradeoffs between cheap native parsing, MinerU CLI provenance, online API PDFs, and recovery paths.
- A stronger future benchmark should add external baselines such as raw OCR, raw MinerU-only output, and direct LLM extraction on the same hidden label set.
