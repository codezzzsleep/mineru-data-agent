# Long Document Risk Report

Long-document chunking risk review based on the saved NIST AI RMF online API run.

## Saved Run

- Source report: `submission_artifacts/long_document_chunks/public_nist_ai_rmf_full_chunked/long_document_chunk_report.json`
- Pages: 48
- Chunk size: 20
- Chunks: 3/3 completed
- Failed chunks: 0
- Elapsed seconds: 42.418
- Retrieval chunks: 58
- Quality status counts: `{"pass_with_warnings": 3}`
- Issue counts: `{"no_page_provenance": 3}`
- Provenance levels: `{"document": 3}`

## Chunks

| Chunk | Pages | Status | Seconds | Quality | Issues | Retrieval Chunks | Provenance |
| --- | --- | --- | ---: | --- | --- | ---: | --- |
| p001_020 | 1-20 | completed | 14.387 | pass_with_warnings (92) | no_page_provenance | 23 | document |
| p021_040 | 21-40 | completed | 20.174 | pass_with_warnings (92) | no_page_provenance | 26 | document |
| p041_048 | 41-48 | completed | 7.793 | pass_with_warnings (92) | no_page_provenance | 9 | document |

## Risks And Mitigations

- `document_level_provenance`: All saved chunks completed but reported document-level provenance and `no_page_provenance`. Impact: Reviewers cannot audit field-level answers to exact pages or bboxes on this online API path. Mitigation: Use local MinerU CLI for audit-grade PDF runs, or rerun with an API variant that emits page/block provenance.
- `cross_chunk_context`: The online API page limit forces 1-20, 21-40, and 41-48 page ranges. Impact: References that start in one chunk and resolve in another need a merge/review layer. Mitigation: Keep chunk manifests, expose page ranges in retrieval metadata, and add cross-chunk entity/table merge tests.
- `single_long_document_sample`: The saved long-document run covers one 48-page public PDF. Impact: It validates the orchestration path, not long-document accuracy across many formats. Mitigation: Add 100+ page annual reports and standards with field/table labels in the benchmark set.
- `no_gpu_cli_long_run`: This artifact is an online API chunking run, not local MinerU CLI/GPU throughput. Impact: GPU pages/second and local artifact cost remain environment-specific. Mitigation: Run the same script in the HeyWhale MinerU GPU image and record pages/second, GPU hours, and page provenance coverage.

## Reviewer Takeaway

- The saved run shows the Agent can split, execute, and aggregate a 48-page public PDF across a 20-page API limit.
- It should be read as orchestration evidence, not as a full long-document accuracy benchmark.
