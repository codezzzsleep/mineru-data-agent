# API Load Smoke Report

Local in-process FastAPI concurrency smoke test; not an external production load test.

## Aggregate

- Requests: 8
- Success: 8
- Failed: 0
- Success rate: 100.0%
- Total elapsed seconds: 0.184157
- Throughput requests/second: 43.441265
- Latency seconds: `{"min": 0.038978, "p50": 0.084756, "p95": 0.131173, "max": 0.13208}`
- Complete artifact sets: 8/8
- Quality status counts: `{"pass": 8}`
- Minimum field evidence count: 5

## Requests

| # | Status | Seconds | Quality | Field Evidence | Trace |
| ---: | ---: | ---: | --- | ---: | --- |
| 0 | 200 | 0.13208 | pass | 5 | yes |
| 1 | 200 | 0.129031 | pass | 5 | yes |
| 2 | 200 | 0.129489 | pass | 5 | yes |
| 3 | 200 | 0.125497 | pass | 5 | yes |
| 4 | 200 | 0.044015 | pass | 5 | yes |
| 5 | 200 | 0.04291 | pass | 5 | yes |
| 6 | 200 | 0.038978 | pass | 5 | yes |
| 7 | 200 | 0.04011 | pass | 5 | yes |

## Boundary

- This uses FastAPI TestClient in-process to verify concurrent request handling and artifact persistence.
- It does not replace an external network load test, GPU stress test, or long-document soak test.
