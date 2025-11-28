# 🔧 Operations Runbook - Crypto Volatility Detection System

**Last Updated:** November 26, 2025  
**Version:** 1.0  
**Owner:** CMU Heinz OAI Team  
**Severity Levels:** 🟢 P4 (Info) | 🟡 P3 (Warning) | 🟠 P2 (Urgent) | 🔴 P1 (Critical)

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Quick Start](#quick-start)
3. [Monitoring & Dashboards](#monitoring--dashboards)
4. [Alert Response Playbooks](#alert-response-playbooks)
5. [Common Issues & Solutions](#common-issues--solutions)
6. [Deployment Procedures](#deployment-procedures)
7. [Model Rollback](#model-rollback)
8. [Emergency Procedures](#emergency-procedures)
9. [Post-Mortem Template](#post-mortem-template)

---

## System Overview

### Architecture Diagram

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Coinbase API   │────▶│  WS Ingestor    │────▶│  Kafka Broker   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                          │
                                                          ▼
                                                  ┌─────────────────┐
                                                  │  Consumer       │
                                                  │  (Feature Eng)  │
                                                  └─────────────────┘
                                                          │
                                                          ▼
                                                  ┌─────────────────┐
                                                  │  FastAPI        │◀──── HTTP Requests
                                                  │  (ML Model)     │
                                                  └─────────────────┘
                                                          │
                                                          ▼
                                                  ┌─────────────────┐
                                                  │  Prometheus     │
                                                  │  (Metrics)      │
                                                  └─────────────────┘
                                                          │
                                                          ▼
                                                  ┌─────────────────┐
                                                  │  Grafana        │
                                                  │  (Dashboards)   │
                                                  └─────────────────┘
```

### Components

| Component | Purpose | Port | Health Check |
|-----------|---------|------|--------------|
| **Zookeeper** | Kafka coordination | 2181 | `echo stat \| nc localhost 2181` |
| **Kafka** | Message broker | 9092, 29092 | `docker exec kafka kafka-topics.sh --list --bootstrap-server localhost:9092` |
| **MLflow** | Model registry | 5001 | `curl http://localhost:5001/health` |
| **FastAPI** | Prediction service | 8000 | `curl http://localhost:8000/health` |
| **Prometheus** | Metrics collection | 9090 | `curl http://localhost:9090/-/healthy` |
| **Grafana** | Dashboards | 3000 | `curl http://localhost:3000/api/health` |
| **Kafka Lag Monitor** | Consumer lag tracking | 9091 | `curl http://localhost:9091/metrics` |

### Key Metrics

- **API Latency (p95):** < 800ms (SLO target)
- **Error Rate:** < 1%
- **Consumer Lag:** < 1,000 messages
- **Availability:** > 99%

---

## Quick Start

### Prerequisites

- Docker & Docker Compose installed
- Python 3.9+ installed
- At least 8GB RAM available
- Port 8000, 3000, 5001, 9090-9092 available

### Starting All Services

```bash
# Navigate to project directory
cd "/Users/asligulcur/Library/CloudStorage/OneDrive-Personal/CMU Heinz Foundations of Operationalizing AI October 2025/Crypto Volatility Real Time"

# Start infrastructure (Kafka, MLflow, Prometheus, Grafana)
cd docker
docker-compose up -d

# Verify all containers are running
docker-compose ps

# Expected output: 6 containers running (zookeeper, kafka, mlflow, api, prometheus, grafana)
```

### Starting Data Pipeline

```bash
# Terminal 1: Start WebSocket ingestor (streams Bitcoin prices)
python3 scripts/ws_ingest_resilient.py

# Terminal 2: Start Kafka consumer (processes features)
python3 scripts/kafka_consumer_resilient.py

# Terminal 3: Start Kafka lag monitor (exposes metrics on port 9091)
python3 scripts/kafka_lag_monitor.py
```

### Verifying System Health

```bash
# Check API health
curl http://localhost:8000/health

# Expected: {"status":"healthy","timestamp":"...","model_loaded":true,"uptime_seconds":...}

# Check Grafana dashboard
open http://localhost:3000
# Login: admin / admin (default)

# Check Prometheus targets
open http://localhost:9090/targets
# All targets should show "UP"
```

---

## Monitoring & Dashboards

### Grafana Dashboard

**URL:** http://localhost:3000  
**Credentials:** admin / admin (change on first login)

**Dashboard:** "Crypto Volatility API - Production Monitoring"

#### Panels

1. **API Latency (p50 / p95)**
   - Shows median and 95th percentile latency
   - Green: < 500ms, Yellow: 500-800ms, Red: > 800ms
   - **Alert if:** p95 > 800ms for 5 minutes

2. **Error Rate (%)**
   - Shows percentage of failed requests
   - Green: < 0.5%, Yellow: 0.5-1%, Red: > 1%
   - **Alert if:** Error rate > 1% for 2 minutes

3. **Data Freshness - Kafka Consumer Lag**
   - Shows how far behind consumer is from producer
   - Green: < 1000, Yellow: 1000-5000, Orange: 5000-10000, Red: > 10000
   - **Alert if:** Lag > 10,000 for 10 minutes

### Prometheus Metrics

**URL:** http://localhost:9090

**Key PromQL Queries:**

```promql
# API p95 latency (last 5 minutes)
histogram_quantile(0.95, sum(rate(predict_latency_seconds_bucket[5m])) by (le))

# Error rate percentage
(rate(predict_errors_total[5m]) / rate(predict_requests_total[5m])) * 100

# Total consumer lag
kafka_consumer_group_lag_total{consumer_group="crypto-volatility-consumer"}

# Request rate (requests per second)
rate(predict_requests_total[1m])

# Model variant indicator (1 = active)
model_variant_active{variant="ml"}
```

### Log Locations

```bash
# Docker container logs
docker-compose logs -f api
docker-compose logs -f kafka
docker-compose logs -f prometheus
docker-compose logs -f grafana

# Application logs (if configured)
tail -f logs/app.log

# Kafka lag monitor logs
# (Check terminal where kafka_lag_monitor.py is running)
```

---

## Alert Response Playbooks

### 🔴 P1: API Down (503 Errors)

**Symptoms:**
- Health check returns 503
- Grafana shows 100% error rate
- Model not loaded

**Immediate Actions:**

1. **Check API container status:**
   ```bash
   docker-compose ps api
   docker-compose logs --tail=100 api
   ```

2. **Check model file exists:**
   ```bash
   ls -lh models/artifacts/random_forest.joblib
   ```

3. **Restart API container:**
   ```bash
   docker-compose restart api
   docker-compose logs -f api
   ```

4. **If model file missing:**
   ```bash
   # Rollback to baseline model (see Model Rollback section)
   export MODEL_VARIANT=baseline
   docker-compose restart api
   ```

5. **Escalate if not resolved in 5 minutes**

**Root Cause Investigation:**
- Check MLflow for model availability
- Check disk space: `df -h`
- Check memory: `free -h`
- Review recent deployments

---

### 🔴 P1: High Latency (p95 > 2000ms)

**Symptoms:**
- Grafana shows latency > 2000ms
- User complaints of slow predictions
- Timeout errors

**Immediate Actions:**

1. **Check system resources:**
   ```bash
   # CPU usage
   docker stats --no-stream api
   
   # Memory
   docker exec api free -h
   ```

2. **Check if model is loaded:**
   ```bash
   curl http://localhost:8000/health | jq '.model_loaded'
   ```

3. **Check for high request volume:**
   ```bash
   # Look at request rate in Prometheus
   open http://localhost:9090/graph?g0.expr=rate(predict_requests_total[1m])
   ```

4. **Temporary mitigation - scale horizontally:**
   ```bash
   # Add more API replicas
   docker-compose up -d --scale api=3
   ```

5. **Rollback to baseline model (faster inference):**
   ```bash
   export MODEL_VARIANT=baseline
   docker-compose restart api
   ```

**Root Cause Investigation:**
- Check for memory leaks
- Review model complexity
- Check database query performance (if applicable)
- Consider caching layer

---

### 🟠 P2: High Consumer Lag (> 10,000 messages)

**Symptoms:**
- Grafana shows consumer lag > 10,000
- Predictions based on stale data
- Data freshness SLO violated

**Immediate Actions:**

1. **Check consumer process:**
   ```bash
   # Is consumer running?
   ps aux | grep kafka_consumer_resilient.py
   
   # Check consumer logs
   # (View terminal where consumer is running)
   ```

2. **Check Kafka broker health:**
   ```bash
   docker-compose logs kafka | tail -50
   ```

3. **Restart consumer:**
   ```bash
   # Kill existing consumer
   pkill -f kafka_consumer_resilient.py
   
   # Restart consumer
   python3 scripts/kafka_consumer_resilient.py
   ```

4. **Increase consumer parallelism:**
   ```bash
   # Start multiple consumer instances
   python3 scripts/kafka_consumer_resilient.py &
   python3 scripts/kafka_consumer_resilient.py &
   ```

5. **Check ingestor rate:**
   ```bash
   # Is ingestor producing too fast?
   docker-compose logs kafka | grep "produced"
   ```

**Root Cause Investigation:**
- Consumer processing time per message
- Network latency to Kafka
- Feature engineering bottlenecks
- Consider increasing partition count

---

### 🟡 P3: Elevated Error Rate (1-5%)

**Symptoms:**
- Grafana shows 1-5% error rate
- Some predictions failing
- Occasional 400/500 errors

**Immediate Actions:**

1. **Check error types:**
   ```bash
   # View Prometheus metrics
   curl http://localhost:9090/api/v1/query?query=predict_errors_total | jq
   ```

2. **Check API logs for patterns:**
   ```bash
   docker-compose logs api | grep ERROR
   ```

3. **Test with known-good input:**
   ```bash
   curl -X POST http://localhost:8000/predict \
     -H "Content-Type: application/json" \
     -d '{
       "price": 88000,
       "bid": 87999,
       "ask": 88001,
       "spread": 2.0,
       "volatility_30s": 0.015,
       "volatility_60s": 0.020,
       "volatility_120s": 0.025,
       "return_10s": 0.001,
       "return_30s": 0.002,
       "return_60s": 0.003,
       "intensity_30s": 20,
       "intensity_60s": 35,
       "intensity_120s": 60
     }'
   ```

4. **Check for data quality issues:**
   ```bash
   # Review recent feature values
   # Check for NaN, inf, or out-of-range values
   ```

**Root Cause Investigation:**
- Input validation issues
- Feature engineering bugs
- Model input format changes
- Null/missing value handling

---

### 🟡 P3: Model Drift Detected

**Symptoms:**
- Evidently report shows > 50% features drifted
- F1 score declining below 0.75
- Prediction accuracy degraded

**Immediate Actions:**

1. **Review drift report:**
   ```bash
   # Generate fresh drift report
   python3 scripts/generate_evidently_now.py
   
   # Open report
   open reports/drift/evidently_drift_*.html
   ```

2. **Check SLO dashboard:**
   ```bash
   # View docs/slo.md for current metrics
   cat docs/slo.md
   ```

3. **Assess severity:**
   - **Low drift (< 30% features):** Monitor, schedule retraining
   - **Medium drift (30-50%):** Accelerate retraining, increase monitoring
   - **High drift (> 50%):** Consider rollback to baseline, emergency retraining

4. **Notify data science team:**
   - Share drift report
   - Request retraining with recent data

5. **If F1 < 0.70, consider rollback:**
   ```bash
   export MODEL_VARIANT=baseline
   docker-compose restart api
   ```

**Root Cause Investigation:**
- Market regime change (crypto volatility patterns shifted)
- Data quality issues
- Feature engineering changes
- Seasonality effects

---

## Common Issues & Solutions

### Issue: API Container Keeps Restarting

**Symptoms:**
```bash
docker-compose ps
# api container shows "Restarting (1) X seconds ago"
```

**Solutions:**

1. **Check logs for error:**
   ```bash
   docker-compose logs api | tail -50
   ```

2. **Common causes:**
   - **Model file missing:** Download/train model
   - **Port already in use:** Change API_PORT in .env
   - **Memory limit:** Increase Docker memory limit
   - **Python dependency:** Rebuild image

3. **Test locally first:**
   ```bash
   cd api
   python3 main.py
   ```

---

### Issue: Grafana Panels Show "No Data"

**Symptoms:**
- Dashboard loads but panels empty
- "No data" message in panels

**Solutions:**

1. **Check Prometheus targets:**
   ```bash
   open http://localhost:9090/targets
   # Ensure all targets are "UP"
   ```

2. **Check metric names:**
   ```bash
   # List available metrics
   curl http://localhost:9090/api/v1/label/__name__/values | jq
   ```

3. **Verify API is generating traffic:**
   ```bash
   # Send test request
   curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d '{"price":88000,"bid":87999,"ask":88001,"spread":2.0,"volatility_30s":0.015,"volatility_60s":0.020,"volatility_120s":0.025,"return_10s":0.001,"return_30s":0.002,"return_60s":0.003,"intensity_30s":20,"intensity_60s":35,"intensity_120s":60}'
   ```

4. **Check Grafana datasource:**
   - Go to Configuration → Data Sources
   - Test Prometheus connection
   - Verify URL is http://prometheus:9090

5. **Restart Grafana:**
   ```bash
   docker-compose restart grafana
   ```

---

### Issue: Consumer Lag Growing Indefinitely

**Symptoms:**
- Lag metric continuously increasing
- Never catches up to ingestor

**Solutions:**

1. **Check ingestor rate vs consumer rate:**
   ```bash
   # Ingestor should produce ~1 msg/sec
   # Consumer should process ~1-2 msg/sec
   ```

2. **Increase consumer instances:**
   ```bash
   # Start 2-3 consumers in parallel
   python3 scripts/kafka_consumer_resilient.py &
   python3 scripts/kafka_consumer_resilient.py &
   ```

3. **Increase Kafka partition count:**
   ```bash
   docker exec kafka kafka-topics.sh --alter \
     --bootstrap-server localhost:9092 \
     --topic ticks.raw \
     --partitions 3
   ```

4. **Optimize consumer code:**
   - Reduce feature computation time
   - Use batch processing
   - Cache intermediate results

---

### Issue: MLflow Connection Errors

**Symptoms:**
- API logs show "Cannot connect to MLflow"
- Model loading fails

**Solutions:**

1. **Check MLflow status:**
   ```bash
   curl http://localhost:5001/health
   docker-compose ps mlflow
   ```

2. **Restart MLflow:**
   ```bash
   docker-compose restart mlflow
   ```

3. **Check environment variable:**
   ```bash
   echo $MLFLOW_TRACKING_URI
   # Should be: http://localhost:5001
   ```

4. **Test connection:**
   ```bash
   python3 -c "import mlflow; mlflow.set_tracking_uri('http://localhost:5001'); print(mlflow.get_tracking_uri())"
   ```

---

## Deployment Procedures

### Standard Deployment (Blue-Green)

**Pre-deployment Checklist:**

- [ ] All tests passing in CI/CD
- [ ] Model trained and validated (F1 > 0.75)
- [ ] Drift report reviewed (< 30% features drifted)
- [ ] Runbook updated with changes
- [ ] Rollback plan prepared
- [ ] Stakeholders notified

**Deployment Steps:**

1. **Backup current state:**
   ```bash
   # Backup model
   cp models/artifacts/random_forest.joblib models/artifacts/random_forest.joblib.backup
   
   # Tag current version
   git tag -a v1.0.0 -m "Pre-deployment backup"
   ```

2. **Deploy new model to staging:**
   ```bash
   # Copy new model
   cp models/artifacts/random_forest_new.joblib models/artifacts/random_forest.joblib
   ```

3. **Test in staging:**
   ```bash
   # Run integration tests
   pytest tests/integration/
   
   # Load test
   python3 scripts/continuous_load.py
   ```

4. **Deploy to production:**
   ```bash
   # Restart API with new model
   docker-compose restart api
   
   # Verify health
   curl http://localhost:8000/health
   ```

5. **Monitor for 1 hour:**
   - Watch Grafana dashboard
   - Check error rate < 1%
   - Check latency p95 < 800ms
   - Verify predictions look reasonable

6. **If issues, rollback immediately** (see Model Rollback section)

---

### Hotfix Deployment

**For critical bugs requiring immediate fix:**

1. **Create hotfix branch:**
   ```bash
   git checkout -b hotfix/critical-bug
   ```

2. **Make minimal changes to fix bug**

3. **Test locally:**
   ```bash
   pytest tests/
   ```

4. **Deploy immediately:**
   ```bash
   docker-compose restart api
   ```

5. **Monitor closely for 15 minutes**

6. **Create post-mortem** (see template below)

---

## Model Rollback

### Quick Rollback to Baseline Model

**When to use:**
- ML model causing high latency (> 2000ms)
- ML model high error rate (> 5%)
- Model drift critical (> 50% features)
- Model file corrupted/missing

**Rollback Steps (< 2 minutes):**

1. **Set MODEL_VARIANT environment variable:**
   ```bash
   # Option A: Set in shell
   export MODEL_VARIANT=baseline
   
   # Option B: Update .env file
   echo "MODEL_VARIANT=baseline" >> .env
   ```

2. **Restart API:**
   ```bash
   docker-compose restart api
   ```

3. **Verify baseline model loaded:**
   ```bash
   docker-compose logs api | grep "Loading BASELINE model"
   # Should see: "📊 Loading BASELINE model (rule-based fallback)"
   ```

4. **Check Prometheus metric:**
   ```bash
   curl http://localhost:9090/api/v1/query?query=model_variant_active | jq
   # Should show: variant="baseline" value=1
   ```

5. **Test prediction:**
   ```bash
   curl -X POST http://localhost:8000/predict \
     -H "Content-Type: application/json" \
     -d '{"price":88000,"bid":87999,"ask":88001,"spread":2.0,"volatility_30s":0.045,"volatility_60s":0.050,"volatility_120s":0.055,"return_10s":0.001,"return_30s":0.002,"return_60s":0.015,"intensity_30s":80,"intensity_60s":85,"intensity_120s":90}'
   
   # Should return prediction from baseline model
   ```

**Expected Behavior:**
- **Latency:** Baseline is faster (< 100ms typically)
- **Accuracy:** Slightly lower than ML model (F1 ~0.70 vs 0.80)
- **Stability:** Very stable, no drift issues

---

### Rollback to Previous ML Model Version

**Rollback Steps (< 5 minutes):**

1. **List backup models:**
   ```bash
   ls -lh models/artifacts/*.backup
   ```

2. **Restore previous model:**
   ```bash
   cp models/artifacts/random_forest.joblib.backup models/artifacts/random_forest.joblib
   ```

3. **Ensure MODEL_VARIANT is set to ml:**
   ```bash
   export MODEL_VARIANT=ml
   ```

4. **Restart API:**
   ```bash
   docker-compose restart api
   ```

5. **Verify model loaded:**
   ```bash
   curl http://localhost:8000/health | jq '.model_loaded'
   # Should return: true
   ```

---

### When to Rollback

| Situation | Rollback Target | Urgency |
|-----------|----------------|---------|
| API latency > 2000ms | Baseline | Immediate |
| Error rate > 10% | Baseline | Immediate |
| Model file missing | Baseline | Immediate |
| F1 score < 0.70 | Previous ML version | Within 1 hour |
| Drift > 50% features | Baseline or retrain | Within 4 hours |
| Memory leak | Previous ML version | Within 2 hours |

---

## Emergency Procedures

### Complete System Restart

**Use when:**
- Multiple components failing
- Unknown root cause
- Last resort before escalation

**Steps:**

1. **Stop all services:**
   ```bash
   # Stop Docker services
   cd docker
   docker-compose down
   
   # Stop Python scripts
   pkill -f ws_ingest_resilient.py
   pkill -f kafka_consumer_resilient.py
   pkill -f kafka_lag_monitor.py
   ```

2. **Clear Kafka data (optional - will lose messages):**
   ```bash
   rm -rf docker/kafka-data/*
   rm -rf docker/zookeeper-data/*
   ```

3. **Restart infrastructure:**
   ```bash
   docker-compose up -d
   
   # Wait 30 seconds for Kafka to initialize
   sleep 30
   ```

4. **Verify services:**
   ```bash
   docker-compose ps
   # All should show "Up"
   ```

5. **Restart data pipeline:**
   ```bash
   python3 scripts/ws_ingest_resilient.py &
   python3 scripts/kafka_consumer_resilient.py &
   python3 scripts/kafka_lag_monitor.py &
   ```

6. **Verify health:**
   ```bash
   curl http://localhost:8000/health
   open http://localhost:3000
   ```

---

### Emergency Contacts

| Role | Contact | Escalation Time |
|------|---------|----------------|
| **On-Call Engineer** | [Your Contact] | Immediate |
| **Data Science Lead** | [Contact] | > 15 minutes |
| **Platform Lead** | [Contact] | > 30 minutes |
| **VP Engineering** | [Contact] | > 1 hour |

---

## Post-Mortem Template

**Use after any P1/P2 incident**

```markdown
# Post-Mortem: [Incident Title]

**Date:** YYYY-MM-DD  
**Duration:** [Start time] - [End time] ([Total minutes])  
**Severity:** P1 / P2 / P3  
**Author:** [Name]

## Summary

[1-2 sentence summary of what happened]

## Impact

- **User Impact:** [How many users affected? What functionality broken?]
- **Business Impact:** [Revenue loss? SLA violations?]
- **Systems Affected:** [List components]

## Timeline (UTC)

- **HH:MM** - [First alert/detection]
- **HH:MM** - [Action taken]
- **HH:MM** - [Resolution]

## Root Cause

[Detailed explanation of why it happened]

## Resolution

[What actions fixed the issue?]

## Prevention

### Immediate Actions (Complete within 1 week)

- [ ] [Action item 1]
- [ ] [Action item 2]

### Long-term Actions (Complete within 1 month)

- [ ] [Action item 1]
- [ ] [Action item 2]

## Lessons Learned

### What Went Well

- [Thing 1]
- [Thing 2]

### What Went Poorly

- [Thing 1]
- [Thing 2]

### Where We Got Lucky

- [Thing 1]

## Action Items

| Action | Owner | Due Date | Status |
|--------|-------|----------|--------|
| [Item 1] | [Name] | YYYY-MM-DD | Open |
| [Item 2] | [Name] | YYYY-MM-DD | Open |
```

---

## Appendix

### Useful Commands Reference

```bash
# === Docker ===
docker-compose ps                    # List all containers
docker-compose logs -f [service]     # Follow logs
docker-compose restart [service]     # Restart service
docker-compose down                  # Stop all services
docker-compose up -d                 # Start all services

# === API ===
curl http://localhost:8000/health    # Health check
curl http://localhost:8000/docs      # API documentation
curl http://localhost:8000/metrics   # Prometheus metrics

# === Kafka ===
# List topics
docker exec kafka kafka-topics.sh --list --bootstrap-server localhost:9092

# Describe topic
docker exec kafka kafka-topics.sh --describe --topic ticks.raw --bootstrap-server localhost:9092

# Consumer group status
docker exec kafka kafka-consumer-groups.sh --describe --group crypto-volatility-consumer --bootstrap-server localhost:9092

# === Prometheus ===
curl http://localhost:9090/-/healthy                  # Health
curl http://localhost:9090/api/v1/query?query=[PROMQL]  # Query

# === Grafana ===
curl http://localhost:3000/api/health  # Health

# === System ===
df -h          # Disk space
free -h        # Memory
top            # CPU/Memory usage
netstat -tulpn # Port usage
```

---

**Document History:**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-26 | OAI Team | Initial runbook creation |

---

**End of Runbook**
