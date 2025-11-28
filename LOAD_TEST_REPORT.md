# Load Test Report - Crypto Volatility API

**Date:** 2025-11-26 12:06:18
**Target:** http://localhost:8000
**Configuration:** 20 requests, 4 workers

## Summary

- **Total Requests:** 20
- **Successful:** 20 ✅
- **Failed:** 0
- **Success Rate:** 100.00%

## Performance

- **Total Time:** 0.66 seconds
- **Throughput:** 30.09 req/sec

## Latency Statistics

| Metric | Value (ms) |
|--------|------------|
| Minimum | 104.88 |
| Maximum | 189.42 |
| Mean | 124.43 |
| Median (p50) | 120.10 |
| **p95** | **189.42** |
| **p99** | **189.42** |
| Std Dev | 18.80 |

## SLA Compliance

- p95 < 100ms: ❌ FAIL (189.42ms)
- Success Rate > 99%: ✅ PASS (100.00%)

