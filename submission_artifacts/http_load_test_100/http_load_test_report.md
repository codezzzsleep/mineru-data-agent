# HTTP Load Smoke Report

Live HTTP load smoke against a running FastAPI server over TCP loopback.

## Aggregate

- Base URL: `http://127.0.0.1:8080`
- Health: `{"status_code": 200, "elapsed_seconds": 0.834941, "json": {"status": "healthy", "version": "0.1.0"}}`
- Requests: 100
- Success: 100
- Failed: 0
- Success rate: 100.0%
- Total elapsed seconds: 17.547587
- Throughput requests/second: 5.698789
- Latency seconds: `{"min": 1.594441, "p50": 3.077543, "p95": 4.205352, "max": 4.718233}`
- Complete artifact sets: 100/100
- Endpoint counts: `{"jobs": 50, "parse": 50}`
- Quality status counts: `{"pass": 100}`
- Minimum field evidence count: 5

## Requests

| # | Endpoint | Status | Job | Seconds | Quality | Evidence | Artifacts |
| ---: | --- | ---: | --- | ---: | --- | ---: | --- |
| 0 | parse | 200 | - | 4.058258 | pass | 5 | trace/result/summary |
| 1 | jobs | 202 | completed | 3.757732 | pass | 5 | trace/result/summary |
| 2 | parse | 200 | - | 4.053897 | pass | 5 | trace/result/summary |
| 3 | jobs | 202 | completed | 3.358225 | pass | 5 | trace/result/summary |
| 4 | parse | 200 | - | 2.75838 | pass | 5 | trace/result/summary |
| 5 | jobs | 202 | completed | 3.443163 | pass | 5 | trace/result/summary |
| 6 | parse | 200 | - | 3.460014 | pass | 5 | trace/result/summary |
| 7 | jobs | 202 | completed | 4.243354 | pass | 5 | trace/result/summary |
| 8 | parse | 200 | - | 4.203352 | pass | 5 | trace/result/summary |
| 9 | jobs | 202 | completed | 3.213274 | pass | 5 | trace/result/summary |
| 10 | parse | 200 | - | 2.893047 | pass | 5 | trace/result/summary |
| 11 | jobs | 202 | completed | 3.423495 | pass | 5 | trace/result/summary |
| 12 | parse | 200 | - | 3.493694 | pass | 5 | trace/result/summary |
| 13 | jobs | 202 | completed | 3.847348 | pass | 5 | trace/result/summary |
| 14 | parse | 200 | - | 3.59183 | pass | 5 | trace/result/summary |
| 15 | jobs | 202 | completed | 3.317849 | pass | 5 | trace/result/summary |
| 16 | parse | 200 | - | 2.830293 | pass | 5 | trace/result/summary |
| 17 | jobs | 202 | completed | 2.915601 | pass | 5 | trace/result/summary |
| 18 | parse | 200 | - | 3.715419 | pass | 5 | trace/result/summary |
| 19 | jobs | 202 | completed | 4.354396 | pass | 5 | trace/result/summary |
| 20 | parse | 200 | - | 1.807225 | pass | 5 | trace/result/summary |
| 21 | jobs | 202 | completed | 2.126064 | pass | 5 | trace/result/summary |
| 22 | parse | 200 | - | 2.184943 | pass | 5 | trace/result/summary |
| 23 | jobs | 202 | completed | 2.075811 | pass | 5 | trace/result/summary |
| 24 | parse | 200 | - | 2.408928 | pass | 5 | trace/result/summary |
| 25 | jobs | 202 | completed | 2.411943 | pass | 5 | trace/result/summary |
| 26 | parse | 200 | - | 2.390173 | pass | 5 | trace/result/summary |
| 27 | jobs | 202 | completed | 3.430372 | pass | 5 | trace/result/summary |
| 28 | parse | 200 | - | 2.484455 | pass | 5 | trace/result/summary |
| 29 | jobs | 202 | completed | 3.554805 | pass | 5 | trace/result/summary |
| 30 | parse | 200 | - | 2.544055 | pass | 5 | trace/result/summary |
| 31 | jobs | 202 | completed | 3.706791 | pass | 5 | trace/result/summary |
| 32 | parse | 200 | - | 3.541892 | pass | 5 | trace/result/summary |
| 33 | jobs | 202 | completed | 3.745853 | pass | 5 | trace/result/summary |
| 34 | parse | 200 | - | 3.66036 | pass | 5 | trace/result/summary |
| 35 | jobs | 202 | completed | 3.823361 | pass | 5 | trace/result/summary |
| 36 | parse | 200 | - | 3.64181 | pass | 5 | trace/result/summary |
| 37 | jobs | 202 | completed | 4.050414 | pass | 5 | trace/result/summary |
| 38 | parse | 200 | - | 3.890931 | pass | 5 | trace/result/summary |
| 39 | jobs | 202 | completed | 3.987901 | pass | 5 | trace/result/summary |
| 40 | parse | 200 | - | 2.592493 | pass | 5 | trace/result/summary |
| 41 | jobs | 202 | completed | 2.723551 | pass | 5 | trace/result/summary |
| 42 | parse | 200 | - | 2.838419 | pass | 5 | trace/result/summary |
| 43 | jobs | 202 | completed | 3.102232 | pass | 5 | trace/result/summary |
| 44 | parse | 200 | - | 2.671232 | pass | 5 | trace/result/summary |
| 45 | jobs | 202 | completed | 2.944421 | pass | 5 | trace/result/summary |
| 46 | parse | 200 | - | 2.732571 | pass | 5 | trace/result/summary |
| 47 | jobs | 202 | completed | 2.953387 | pass | 5 | trace/result/summary |
| 48 | parse | 200 | - | 2.712761 | pass | 5 | trace/result/summary |
| 49 | jobs | 202 | completed | 3.556035 | pass | 5 | trace/result/summary |
| 50 | parse | 200 | - | 3.539476 | pass | 5 | trace/result/summary |
| 51 | jobs | 202 | completed | 2.492552 | pass | 5 | trace/result/summary |
| 52 | parse | 200 | - | 3.708831 | pass | 5 | trace/result/summary |
| 53 | jobs | 202 | completed | 3.999425 | pass | 5 | trace/result/summary |
| 54 | parse | 200 | - | 3.511172 | pass | 5 | trace/result/summary |
| 55 | jobs | 202 | completed | 4.718233 | pass | 5 | trace/result/summary |
| 56 | parse | 200 | - | 2.502362 | pass | 5 | trace/result/summary |
| 57 | jobs | 202 | completed | 4.702088 | pass | 5 | trace/result/summary |
| 58 | parse | 200 | - | 2.461778 | pass | 5 | trace/result/summary |
| 59 | jobs | 202 | completed | 4.633052 | pass | 5 | trace/result/summary |
| 60 | parse | 200 | - | 3.877226 | pass | 5 | trace/result/summary |
| 61 | jobs | 202 | completed | 2.610937 | pass | 5 | trace/result/summary |
| 62 | parse | 200 | - | 3.994506 | pass | 5 | trace/result/summary |
| 63 | jobs | 202 | completed | 3.054473 | pass | 5 | trace/result/summary |
| 64 | parse | 200 | - | 3.991017 | pass | 5 | trace/result/summary |
| 65 | jobs | 202 | completed | 2.928788 | pass | 5 | trace/result/summary |
| 66 | parse | 200 | - | 2.648474 | pass | 5 | trace/result/summary |
| 67 | jobs | 202 | completed | 3.246194 | pass | 5 | trace/result/summary |
| 68 | parse | 200 | - | 2.728893 | pass | 5 | trace/result/summary |
| 69 | jobs | 202 | completed | 3.1803 | pass | 5 | trace/result/summary |
| 70 | parse | 200 | - | 2.590634 | pass | 5 | trace/result/summary |
| 71 | jobs | 202 | completed | 2.611649 | pass | 5 | trace/result/summary |
| 72 | parse | 200 | - | 3.517132 | pass | 5 | trace/result/summary |
| 73 | jobs | 202 | completed | 3.874333 | pass | 5 | trace/result/summary |
| 74 | parse | 200 | - | 2.186481 | pass | 5 | trace/result/summary |
| 75 | jobs | 202 | completed | 3.833502 | pass | 5 | trace/result/summary |
| 76 | parse | 200 | - | 3.526633 | pass | 5 | trace/result/summary |
| 77 | jobs | 202 | completed | 2.49528 | pass | 5 | trace/result/summary |
| 78 | parse | 200 | - | 3.329274 | pass | 5 | trace/result/summary |
| 79 | jobs | 202 | completed | 2.316615 | pass | 5 | trace/result/summary |
| 80 | parse | 200 | - | 2.739753 | pass | 5 | trace/result/summary |
| 81 | jobs | 202 | completed | 2.913369 | pass | 5 | trace/result/summary |
| 82 | parse | 200 | - | 3.046341 | pass | 5 | trace/result/summary |
| 83 | jobs | 202 | completed | 2.763892 | pass | 5 | trace/result/summary |
| 84 | parse | 200 | - | 3.100613 | pass | 5 | trace/result/summary |
| 85 | jobs | 202 | completed | 3.483738 | pass | 5 | trace/result/summary |
| 86 | parse | 200 | - | 3.160719 | pass | 5 | trace/result/summary |
| 87 | jobs | 202 | completed | 3.218226 | pass | 5 | trace/result/summary |
| 88 | parse | 200 | - | 3.036152 | pass | 5 | trace/result/summary |
| 89 | jobs | 202 | completed | 2.394326 | pass | 5 | trace/result/summary |
| 90 | parse | 200 | - | 2.383659 | pass | 5 | trace/result/summary |
| 91 | jobs | 202 | completed | 2.323191 | pass | 5 | trace/result/summary |
| 92 | parse | 200 | - | 2.308139 | pass | 5 | trace/result/summary |
| 93 | jobs | 202 | completed | 1.942472 | pass | 5 | trace/result/summary |
| 94 | parse | 200 | - | 1.816636 | pass | 5 | trace/result/summary |
| 95 | jobs | 202 | completed | 2.29221 | pass | 5 | trace/result/summary |
| 96 | parse | 200 | - | 1.603396 | pass | 5 | trace/result/summary |
| 97 | jobs | 202 | completed | 1.88487 | pass | 5 | trace/result/summary |
| 98 | parse | 200 | - | 1.660872 | pass | 5 | trace/result/summary |
| 99 | jobs | 202 | completed | 1.594441 | pass | 5 | trace/result/summary |

## Boundary

- This is a real HTTP loopback smoke test, stronger than in-process TestClient evidence.
- It is still not a public internet deployment, GPU saturation test, or long-running production soak test.
- The committed run uses small HTML input to keep CI and reviewer reproduction inexpensive.
