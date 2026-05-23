# Contributing

Thanks for reviewing or extending this Data Agent project. The repository is a competition submission first, so contributions should preserve reproducibility and evidence quality.

## Development Setup

1. Create and activate a Python 3.10+ virtual environment.
2. Install the package with development dependencies:

```bash
pip install -e ".[dev]"
```

3. Run the test suite before submitting changes:

```bash
python -m pytest -q
```

## Evidence Rules

- Every new capability should include at least one runnable test, saved artifact, or documented case study.
- If a claim says "robust", "stable", "accurate", or "automatic", point to a file under `tests/`, `submission_artifacts/`, or `docs/`.
- Do not commit API keys, tokens, private documents, personal paths, or customer data.
- Public real-document examples must include source metadata and clear label boundaries.
- Synthetic fixtures are acceptable, but label them as fixtures and do not describe them as real customer data.

## Adding New Cases

When adding a new evaluation case:

1. Save the result, trace, summary, and retrieval outputs under `submission_artifacts/`.
2. Add lightweight labels to `examples/evaluation/labels.json`.
3. Rebuild the metrics:

```bash
python scripts/build_evaluation_report.py
python scripts/build_stability_report.py
```

4. Update `docs/CASE_STUDIES.md` if the case demonstrates a new scenario.

## Pull Request Checklist

- Tests pass locally.
- Evaluation metrics regenerate successfully.
- JSON artifacts are parseable.
- Documentation states both evidence and remaining limitations.
- No secrets or private paths are present.

