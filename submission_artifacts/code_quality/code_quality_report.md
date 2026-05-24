# Code Quality Report

Static repository quality summary generated from local files.

## Aggregate

- Python files: 51
- Physical lines: 13353
- Code lines: 11848
- Classes: 34
- Functions: 547
- Test files: 12
- Test functions: 76
- CI workflows: `[".github/workflows/tests.yml"]`
- Coverage measured: true
- Line coverage: 81.31
- Coverage report: `submission_artifacts/coverage/coverage_report.md`

## By Area

| Area | Files | Physical Lines | Code Lines | Classes | Functions | Test Functions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| src | 14 | 6141 | 5505 | 19 | 248 | 0 |
| scripts | 25 | 5597 | 4982 | 9 | 211 | 0 |
| tests | 12 | 1615 | 1361 | 6 | 88 | 76 |

## Largest Python Files

| File | Area | Code Lines | Functions | Classes |
| --- | --- | ---: | ---: | ---: |
| `src/mineru_data_agent/agent.py` | src | 1310 | 36 | 2 |
| `src/mineru_data_agent/planner.py` | src | 774 | 29 | 2 |
| `src/mineru_data_agent/extractors.py` | src | 615 | 42 | 1 |
| `src/mineru_data_agent/llm_client.py` | src | 509 | 19 | 3 |
| `src/mineru_data_agent/mineru_client.py` | src | 451 | 23 | 3 |
| `src/mineru_data_agent/evaluation.py` | src | 431 | 21 | 0 |
| `src/mineru_data_agent/retrieval_exporter.py` | src | 394 | 24 | 1 |
| `scripts/run_http_load_test.py` | scripts | 385 | 17 | 0 |
| `tests/test_agent_recovery.py` | tests | 383 | 18 | 6 |
| `src/mineru_data_agent/api.py` | src | 362 | 23 | 1 |
| `src/mineru_data_agent/validators.py` | src | 294 | 13 | 0 |
| `scripts/run_failure_recovery_cases.py` | scripts | 283 | 12 | 3 |

## Test Modules

| File | Tests |
| --- | ---: |
| `tests/test_agent_recovery.py` | 7 |
| `tests/test_api.py` | 11 |
| `tests/test_artifact_reports.py` | 6 |
| `tests/test_batch.py` | 2 |
| `tests/test_cli.py` | 3 |
| `tests/test_evaluation.py` | 1 |
| `tests/test_extractors.py` | 10 |
| `tests/test_llm_client.py` | 10 |
| `tests/test_mineru_client.py` | 6 |
| `tests/test_planner.py` | 4 |
| `tests/test_retrieval_exporter.py` | 5 |
| `tests/test_validators.py` | 11 |

## Notes

- This report counts files, lines, functions, tests, and CI workflow files. It reads coverage output when present but does not itself run coverage.
- Run `python scripts/build_coverage_report.py` before this script to refresh line coverage.
- The GitHub Actions workflow is in `.github/workflows/tests.yml`; the current CI status should be checked on GitHub for the submitted commit.
