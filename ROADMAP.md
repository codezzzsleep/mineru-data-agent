# Roadmap

## v0.2

- Add more public real PDFs with field-level labels.
- Add external parser comparisons for Docling, Marker, PyMuPDF/pdfplumber where licenses and runtime allow.
- Add stricter retrieval validation with a fixed embedding model and human relevance labels.
- Add more live LLM on/off cases with token/cost accounting.

## v0.3

- Add plugin-style parser backends beyond MinerU.
- Add smarter long-document chunk boundaries and overlap/context stitching.
- Add production metrics endpoint and deployment examples for Kubernetes.
- Add larger low-quality OCR and table-cell benchmarks.

## Current Boundaries

- Current public labels are lightweight, not a full OCR character/table-cell benchmark.
- Current HTTP load tests are local loopback, not public-network or GPU soak tests.
- Current offline Agent decision cases are regression tests, not live LLM autonomy evidence.
