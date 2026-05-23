# HTTP Load Smoke Report

Live HTTP load smoke against a running FastAPI server over TCP loopback.

## Aggregate

- Base URL: `http://127.0.0.1:8080`
- Health: `{"status_code": 200, "elapsed_seconds": 1.056278, "json": {"status": "healthy", "version": "0.1.0"}}`
- Requests: 12
- Success: 12
- Failed: 0
- Success rate: 100.0%
- Total elapsed seconds: 3.026565
- Throughput requests/second: 3.96489
- Latency seconds: `{"min": 1.050836, "p50": 1.260617, "p95": 1.4195, "max": 1.514177}`
- Complete artifact sets: 12/12
- Endpoint counts: `{"jobs": 6, "parse": 6}`
- Quality status counts: `{"pass": 12}`
- Minimum field evidence count: 5

## Requests

| # | Endpoint | Status | Job | Seconds | Quality | Evidence | Artifacts |
| ---: | --- | ---: | --- | ---: | --- | ---: | --- |
| 0 | parse | 200 | - | 1.099448 | pass | 5 | trace/result/summary |
| 1 | jobs | 202 | completed | 1.514177 | pass | 5 | trace/result/summary |
| 2 | parse | 200 | - | 1.252802 | pass | 5 | trace/result/summary |
| 3 | jobs | 202 | completed | 1.281704 | pass | 5 | trace/result/summary |
| 4 | parse | 200 | - | 1.252192 | pass | 5 | trace/result/summary |
| 5 | jobs | 202 | completed | 1.268433 | pass | 5 | trace/result/summary |
| 6 | parse | 200 | - | 1.124986 | pass | 5 | trace/result/summary |
| 7 | jobs | 202 | completed | 1.342037 | pass | 5 | trace/result/summary |
| 8 | parse | 200 | - | 1.050836 | pass | 5 | trace/result/summary |
| 9 | jobs | 202 | completed | 1.324073 | pass | 5 | trace/result/summary |
| 10 | parse | 200 | - | 1.087031 | pass | 5 | trace/result/summary |
| 11 | jobs | 202 | completed | 1.273504 | pass | 5 | trace/result/summary |

## Boundary

- This is a real HTTP loopback smoke test, stronger than in-process TestClient evidence.
- It is still not a public internet deployment, GPU saturation test, or long-running production soak test.
- The committed run uses small HTML input to keep CI and reviewer reproduction inexpensive.
