# Coverage Report

Line coverage measured by coverage.py while running the local pytest suite.

## Aggregate

- Measured: true
- Line coverage: 81.69%
- Covered lines: 2748
- Statements: 3364
- Missing lines: 616
- Pytest command: `python.exe -m coverage run --source src/mineru_data_agent -m pytest -q`

## Lowest Coverage Files

| File | Coverage | Statements | Missing |
| --- | ---: | ---: | ---: |
| `src/mineru_data_agent/mineru_client.py` | 46.72% | 259 | 138 |
| `src/mineru_data_agent/llm_client.py` | 59.91% | 212 | 85 |
| `src/mineru_data_agent/retrieval_exporter.py` | 65.98% | 291 | 99 |
| `src/mineru_data_agent/cli.py` | 75.31% | 81 | 20 |
| `src/mineru_data_agent/extractors.py` | 84.86% | 700 | 106 |
| `src/mineru_data_agent/evaluation.py` | 86.31% | 241 | 33 |
| `src/mineru_data_agent/batch.py` | 86.89% | 61 | 8 |
| `src/mineru_data_agent/logging_utils.py` | 87.5% | 40 | 5 |
| `src/mineru_data_agent/planner.py` | 89.36% | 329 | 35 |
| `src/mineru_data_agent/agent.py` | 91.47% | 727 | 62 |
| `src/mineru_data_agent/api.py` | 92.78% | 194 | 14 |
| `src/mineru_data_agent/validators.py` | 93.53% | 170 | 11 |

## Command Log

| Command | Exit | Seconds |
| --- | ---: | ---: |
| `-m coverage erase` | 0 | 0.242 |
| `-m coverage run --source src/mineru_data_agent -m pytest -q` | 0 | 8.643 |
| `-m coverage json -o submission_artifacts/coverage/coverage_raw.json` | 0 | 0.797 |

## Notes

- This is source line coverage for the local test suite, not a live MinerU/LLM/GPU integration benchmark.
- The measured denominator is `src/mineru_data_agent`; scripts are excluded from the coverage target.
- Use the raw coverage JSON for exact missing-line lists.
