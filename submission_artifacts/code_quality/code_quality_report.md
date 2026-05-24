# Code Quality Report

Static repository quality summary generated from local files.

## Aggregate

- Python files: 47
- Physical lines: 11834
- Code lines: 10488
- Classes: 31
- Functions: 488
- Test files: 12
- Test functions: 71
- CI workflows: `[".github/workflows/tests.yml"]`
- Coverage measured: false

## By Area

| Area | Files | Physical Lines | Code Lines | Classes | Functions | Test Functions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| src | 14 | 5906 | 5283 | 19 | 243 | 0 |
| scripts | 21 | 4414 | 3929 | 6 | 162 | 0 |
| tests | 12 | 1514 | 1276 | 6 | 83 | 71 |

## Largest Python Files

| File | Area | Code Lines | Functions | Classes |
| --- | --- | ---: | ---: | ---: |
| `src/mineru_data_agent/agent.py` | src | 1222 | 34 | 2 |
| `src/mineru_data_agent/planner.py` | src | 667 | 27 | 2 |
| `src/mineru_data_agent/extractors.py` | src | 615 | 42 | 1 |
| `src/mineru_data_agent/llm_client.py` | src | 509 | 19 | 3 |
| `src/mineru_data_agent/mineru_client.py` | src | 451 | 23 | 3 |
| `src/mineru_data_agent/evaluation.py` | src | 431 | 21 | 0 |
| `src/mineru_data_agent/retrieval_exporter.py` | src | 394 | 24 | 1 |
| `scripts/run_http_load_test.py` | scripts | 385 | 17 | 0 |
| `tests/test_agent_recovery.py` | tests | 360 | 17 | 6 |
| `src/mineru_data_agent/api.py` | src | 354 | 23 | 1 |
| `src/mineru_data_agent/validators.py` | src | 294 | 13 | 0 |
| `scripts/run_long_document_chunks.py` | scripts | 274 | 13 | 1 |

## Test Modules

| File | Tests |
| --- | ---: |
| `tests/test_agent_recovery.py` | 6 |
| `tests/test_api.py` | 10 |
| `tests/test_artifact_reports.py` | 4 |
| `tests/test_batch.py` | 2 |
| `tests/test_cli.py` | 2 |
| `tests/test_evaluation.py` | 1 |
| `tests/test_extractors.py` | 10 |
| `tests/test_llm_client.py` | 10 |
| `tests/test_mineru_client.py` | 6 |
| `tests/test_planner.py` | 4 |
| `tests/test_retrieval_exporter.py` | 5 |
| `tests/test_validators.py` | 11 |

## Notes

- This report counts files, lines, functions, tests, and CI workflow files. It does not run a coverage tool.
- Run `python -m pytest -q` for functional validation and add pytest-cov if line coverage is required.
- The GitHub Actions workflow is in `.github/workflows/tests.yml`; the current CI status should be checked on GitHub for the submitted commit.
