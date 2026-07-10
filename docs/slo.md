# Service Level Objectives (SLOs)

**Document Version:** 1.0  
**Last Updated:** November 26, 2025  
**Owner:** CMU Heinz OAI Team

---

## Executive Summary

This document defines Service Level Objectives (SLOs) for the Crypto Volatility Detection API, establishing measurable targets for system performance, reliability, and data freshness. These SLOs guide operational decisions, inform alerting thresholds, and provide a framework for evaluating system health.

---

## 1. Primary SLO: API Latency

### Service Level Indicator (SLI)
**Metric:** p95 prediction latency (95th percentile response time)  
**Measurement:** `histogram_quantile(0.95, sum(rate(predict_latency_seconds_bucket[5m])) by (le))`

### Service Level Objective (SLO)
**Target:** ≤ 800ms (0.8 seconds)  
**Measurement Window:** 5-minute rolling average  
**Business Justification:** Real-time crypto volatility detection requires sub-second predictions to enable timely trading decisions. The 800ms target allows for:
- Network overhead (~50-100ms)
- Model inference (~200-400ms)
- Feature extraction and validation (~100-200ms)
- Response serialization (~50-100ms)

### Current Performance
**Status:** ⚠️ **Needs Improvement**  
**Baseline Measurement (Week 5):**
- p50: 685ms
- p95: 1,838ms
- p99: ~2,500ms (estimated)

**Recent Measurement (Week 6 - Live Testing):**
- p50: ~80-90ms
- p95: ~100-120ms
- Status: ✅ **MEETING SLO** (significant improvement after optimization)

### Error Budget
- **SLO:** 95% of requests ≤ 800ms
- **Error Budget:** 5% of requests may exceed 800ms
- **Budget Period:** 30 days
- **Current Consumption:** ~2% (based on recent testing)

### Alerting Thresholds
- **Warning:** p95 > 600ms for 5 minutes
- **Critical:** p95 > 800ms for 5 minutes
- **Severe:** p95 > 1,000ms for 2 minutes

### Improvement Actions
If SLO is breached:
1. Check model inference time (consider simpler model or quantization)
2. Review database query performance
3. Scale API horizontally (add more instances)
4. Implement caching for repeated predictions
5. Consider model rollback to baseline

---

## 2. SLO: Service Availability

### Service Level Indicator (SLI)
**Metric:** Request success rate (HTTP 2xx / total requests)  
**Measurement:** `rate(api_requests_total{status="200"}[5m]) / rate(api_requests_total[5m]) * 100`

### Service Level Objective (SLO)
**Target:** ≥ 99.0% (two nines)  
**Measurement Window:** 30-day rolling window  
**Business Justification:** High availability ensures traders can rely on the API during critical market events. 99% allows for:
- Planned maintenance: ~7.2 hours/month
- Unplanned downtime: ~0.5 hours/month
- Total allowable downtime: ~7.7 hours/month

### Current Performance
**Status:** ✅ **EXCEEDING SLO**  
**Baseline Measurement:**
- Success rate: 100% (120/120 requests during Week 5 load testing)
- Error rate: 0%

**Live Testing (Week 6):**
- Success rate: 100% (30/30 requests)
- Error rate: 0%

### Error Budget
- **SLO:** 99% uptime = 1% error budget
- **Monthly Budget:** ~7.7 hours downtime allowed
- **Current Consumption:** 0% (no errors observed)

### Alerting Thresholds
- **Warning:** Success rate < 99.5% for 5 minutes
- **Critical:** Success rate < 99.0% for 5 minutes
- **Severe:** Success rate < 95.0% for 1 minute

### Improvement Actions
If SLO is breached:
1. Review error logs for patterns (4xx vs 5xx errors)
2. Check downstream dependencies (MLflow, Kafka, database)
3. Implement circuit breakers for failing dependencies
4. Review rate limiting configuration
5. Consider failover to backup model

---

## 3. SLO: Data Freshness

### Service Level Indicator (SLI)
**Metric:** Kafka consumer lag (messages behind)  
**Measurement:** `kafka_consumer_group_lag_total{consumer_group="crypto-volatility-consumer"}`

### Service Level Objective (SLO)
**Target:** < 1,000 messages  
**Peak Traffic Target:** < 5,000 messages (acceptable during high-volume periods)  
**Measurement Window:** Real-time monitoring  
**Business Justification:** Low consumer lag ensures the model trains on recent market data and predictions reflect current market conditions. Lag thresholds:
- **Green (< 1,000):** Excellent - real-time processing
- **Yellow (1,000-5,000):** Acceptable - minor delay (~1-5 minutes at typical rates)
- **Orange (5,000-10,000):** Concerning - data staleness may impact model accuracy
- **Red (> 10,000):** Critical - significant lag, predictions may be outdated

### Current Performance
**Status:** 🔴 **NOT MEETING SLO**  
**Baseline Measurement (Week 6):**
- Consumer lag: ~15,110 messages (initial backlog)
- Trend: Increasing (ingestor producing faster than consumer can process)

**Contributing Factors:**
- High ingestion rate from Coinbase WebSocket (10,500+ messages ingested)
- Single consumer instance (not scaled)
- No consumer optimization yet implemented

### Error Budget
- **SLO:** Lag < 1,000 messages for 95% of time
- **Error Budget:** 5% of time lag may be 1,000-5,000 messages
- **Current Status:** Exceeding error budget (lag > 10,000 consistently)

### Alerting Thresholds
- **Warning:** Lag > 1,000 messages for 10 minutes
- **Critical:** Lag > 5,000 messages for 5 minutes
- **Severe:** Lag > 10,000 messages for 2 minutes OR lag increasing > 500 messages/minute

### Improvement Actions
If SLO is breached:
1. **Immediate:** Scale consumer horizontally (add more consumer instances)
2. **Short-term:** Optimize consumer processing logic (batch processing, async I/O)
3. **Medium-term:** Implement consumer auto-scaling based on lag
4. **Long-term:** Consider stream processing framework (Kafka Streams, Flink)
5. **Emergency:** Temporarily reduce ingestion rate or skip non-critical messages

---

## 4. SLO: Prediction Accuracy (Model Performance)

### Service Level Indicator (SLI)
**Metric:** Model F1 score on holdout test set  
**Measurement:** Periodic batch evaluation on recent production data

### Service Level Objective (SLO)
**Target:** F1 Score ≥ 0.75  
**Measurement Window:** Weekly evaluation on last 7 days of production data  
**Business Justification:** High accuracy ensures traders can trust the volatility predictions. F1 score balances precision (avoiding false alarms) and recall (catching real volatility spikes).

### Current Performance
**Status:** ✅ **MEETING SLO** (baseline model)  
**Baseline Measurement (Training):**
- F1 Score: ~0.80 (training set)
- Precision: ~0.82
- Recall: ~0.78

**Production Monitoring:**
- Live accuracy tracking not yet implemented (Week 6 Task 4 - Evidently)
- Will implement drift detection to monitor ongoing accuracy

### Error Budget
- **SLO:** F1 ≥ 0.75 for weekly evaluations
- **Error Budget:** F1 may drop to 0.70-0.75 for up to 2 consecutive weeks before requiring action
- **Breach Threshold:** F1 < 0.70 for 1 week = immediate model retraining required

### Alerting Thresholds
- **Warning:** F1 < 0.78 for 1 week
- **Critical:** F1 < 0.75 for 1 week
- **Severe:** F1 < 0.70 for 1 week OR sudden drop > 10% in 24 hours

### Improvement Actions
If SLO is breached:
1. **Immediate:** Trigger model retraining on recent data
2. **Investigate:** Check for data drift using Evidently reports
3. **Rollback:** Consider reverting to previous model version if new model underperforms
4. **Feature Engineering:** Evaluate if new features needed to capture market changes
5. **Model Selection:** Experiment with alternative algorithms (XGBoost, LightGBM, Neural Network)

---

## 5. Additional SLIs (Monitoring Only - No SLO Yet)

### 5.1 Error Rate by Type
**Metric:** Breakdown of errors by category  
**Measurement:**
- `rate(predict_errors_total{error_type="validation"}[5m])`
- `rate(predict_errors_total{error_type="model"}[5m])`
- `rate(predict_errors_total{error_type="timeout"}[5m])`

**Purpose:** Identify root causes of failures (client errors vs server errors)

### 5.2 Request Rate (Throughput)
**Metric:** Requests per second  
**Measurement:** `rate(predict_requests_total[1m])`

**Purpose:** Track API usage patterns and plan capacity

**Baseline:** ~10-20 req/sec during testing  
**Peak Capacity:** Unknown (requires load testing)

### 5.3 Model Confidence Distribution
**Metric:** Distribution of prediction probabilities  
**Measurement:** `prediction_confidence` histogram

**Purpose:** Detect if model becomes overly confident or uncertain (potential drift signal)

### 5.4 Prediction Class Balance
**Metric:** Ratio of predicted spikes vs normal  
**Measurement:** `predictions_by_class_total{class_label="spike"} / predictions_by_class_total`

**Purpose:** Detect if model prediction distribution shifts (e.g., predicting too many/few spikes)

---

## 6. SLO Review and Adjustment Process

### Review Cadence
- **Weekly:** Review SLO compliance dashboard
- **Monthly:** Analyze error budget consumption and adjust thresholds if needed
- **Quarterly:** Comprehensive SLO review and update based on business needs

### Adjustment Criteria
SLOs should be adjusted if:
1. **Consistently met with margin:** If p95 latency is always < 400ms, consider tightening to 600ms
2. **Consistently missed despite efforts:** If lag always > 5,000, adjust SLO to 5,000 and plan long-term improvements
3. **Business requirements change:** New use cases may require stricter or relaxed SLOs
4. **Technology changes:** Infrastructure upgrades may enable better SLOs

### Stakeholder Communication
- **Green Status (Meeting SLOs):** Monthly summary email
- **Yellow Status (Approaching Breach):** Weekly updates with improvement plan
- **Red Status (Breaching SLOs):** Immediate notification + daily updates until resolved

---

## 7. SLO Implementation Checklist

### Monitoring Setup
- [x] Prometheus metrics instrumented
- [x] Grafana dashboards created
- [x] All SLIs measurable in real-time
- [ ] Alerting rules configured (Week 6 Task 6 - Runbook)
- [ ] PagerDuty/Slack integration (future)

### Documentation
- [x] SLO targets defined and documented
- [x] Measurement methodology documented
- [x] Improvement actions documented
- [ ] Runbook created with remediation steps (Week 6 Task 6)

### Process
- [ ] Weekly SLO review meeting scheduled
- [ ] On-call rotation established
- [ ] Incident response process documented
- [ ] Post-mortem template created

---

## 8. References

### Dashboards
- **Grafana Dashboard:** http://localhost:3000 → "Crypto Volatility API - Production Monitoring"
- **Prometheus:** http://localhost:9090

### Metrics Endpoints
- **API Metrics:** http://localhost:8000/metrics
- **Kafka Lag Monitor:** http://localhost:9091/metrics

### Related Documents
- `docs/runbook.md` - Operational procedures
- `docs/drift_summary.md` - Model drift detection
- `README.md` - System architecture and setup

### Industry References
- [Google SRE Book - SLOs](https://sre.google/sre-book/service-level-objectives/)
- [Atlassian SLA vs SLO vs SLI](https://www.atlassian.com/incident-management/kpis/sla-vs-slo-vs-sli)
- [AWS Well-Architected Framework - Performance Efficiency](https://aws.amazon.com/architecture/well-architected/)

---

## Appendix: Prometheus Queries

### Latency Queries
```promql
# p50 latency
histogram_quantile(0.50, sum(rate(predict_latency_seconds_bucket[5m])) by (le))

# p95 latency (SLO target)
histogram_quantile(0.95, sum(rate(predict_latency_seconds_bucket[5m])) by (le))

# p99 latency
histogram_quantile(0.99, sum(rate(predict_latency_seconds_bucket[5m])) by (le))
```

### Availability Queries
```promql
# Success rate percentage
(rate(predict_requests_total{model_version="1.0"}[5m]) - rate(predict_errors_total[5m])) / rate(predict_requests_total{model_version="1.0"}[5m]) * 100

# Error rate percentage
(rate(predict_errors_total[5m]) / rate(predict_requests_total[5m])) * 100
```

### Data Freshness Queries
```promql
# Consumer lag (total messages behind)
kafka_consumer_group_lag_total{consumer_group="crypto-volatility-consumer"}

# Consumer offset
kafka_consumer_offset{consumer_group="crypto-volatility-consumer"}

# Log end offset (total messages in topic)
kafka_log_end_offset{topic="ticks.raw"}
```

### Throughput Queries
```promql
# Requests per second
rate(predict_requests_total[1m])

# Requests per minute
rate(predict_requests_total[1m]) * 60
```

---

**Document Status:** ✅ **Complete**  
**Review Required:** Monthly  
**Next Review Date:** December 26, 2025
