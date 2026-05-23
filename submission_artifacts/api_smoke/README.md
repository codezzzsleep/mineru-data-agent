# API Smoke Evidence

This directory preserves a local FastAPI smoke test.

Boundary statement: this smoke test proves the FastAPI service contract, persistence of `trace_path`/`summary_path`, and retrieval artifact writing for uploaded HTML and PDF fixtures. It does not prove public internet deployment. The PDF smoke calls the CPU-friendly MinerU online Agent API and keeps the expected `no_page_provenance` warning.

- Health endpoint: `/health`
- Parse endpoint: `/v1/parse`
- Run id: `2478fc60f3b2`
- Stored run directory: `run_2478fc60f3b2/`
- Quality: `pass` (100/100)
- Recovery decision: `accept`
- Retrieval chunks: 2

The response keeps `trace_path`, `summary_path`, and artifact paths available after the request finishes.

## PDF Upload Smoke

- Endpoint: `/v1/parse`
- Runner: `agent-api`
- Input: `examples/real_pdfs/standard_contract_cross_page.pdf`
- Run id: `e1354b67a7d7`
- Stored run directory: `run_pdf_e1354b67a7d7/`
- Quality: `pass_with_warnings` (92/100)
- Recovery executed: `false`
- Retrieval chunks: 6
- Boundary: this is a local FastAPI PDF upload smoke that calls the CPU-friendly MinerU online Agent API; it is not a public internet deployment.

