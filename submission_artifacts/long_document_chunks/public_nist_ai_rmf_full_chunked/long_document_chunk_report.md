# Long Document Chunked API Smoke

This report shows how the Data Agent handles a public long PDF when the MinerU online Agent API enforces a 20-page per-call limit.

## Aggregate

- Input: `examples/public_real_documents/files/nist_ai_rmf_1_0.pdf`
- Page count: 48
- Chunk size: 20
- Chunks completed: 3/3
- Success rate: 100.0%
- Elapsed seconds: 42.418
- Total retrieval chunks: 58
- Quality status counts: `{"pass_with_warnings": 3}`
- Provenance level counts: `{"document": 3}`

## Chunks

| Chunk | Pages | Status | Quality | Provenance | Retrieval Chunks | Seconds |
| --- | --- | --- | --- | --- | ---: | ---: |
| p001_020 | 1-20 | completed | pass_with_warnings (92) | document | 23 | 14.387 |
| p021_040 | 21-40 | completed | pass_with_warnings (92) | document | 26 | 20.174 |
| p041_048 | 41-48 | completed | pass_with_warnings (92) | document | 9 | 7.793 |

## Boundary

- This is a real online MinerU Agent API long-document chunking smoke. The API enforces a 20-page maximum per call, so the Data Agent splits page ranges and records each chunk's artifacts. It is not a local MinerU CLI/GPU benchmark or public internet production load test.
