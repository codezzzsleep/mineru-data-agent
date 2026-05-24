# PDF LLM Preplan + API-to-CLI Fallback Evidence

This case uses a real PDF fixture as input and runs the production Agent recovery path.

- Input: `examples/real_pdfs/standard_contract_cross_page.pdf`
- Initial parser: MinerU online Agent API
- Recovery trigger: `no_page_provenance`
- Fallback parser: cached local MinerU CLI artifact from `case_mineru_cli_contract_pdf`
- LLM preplanning: offline deterministic scheduler because no external LLM key is present in this environment
- Run id: `9cfdd736c9a1`
- Quality: `pass` (100/100)
- Recovery executed: `true`
- Selected attempt: `cli_fallback`

Boundary: this is a recovery evidence drill. It proves code-level automatic fallback and attempt selection. For a live LLM/CLI evidence run, set `MODELSCOPE_API_KEY` or `DEEPSEEK_API_KEY` and provide a real `mineru` executable.
