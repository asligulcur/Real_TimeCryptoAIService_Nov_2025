# 🚀 Quick Setup Guide - Crypto Volatility Real-Time Detection

**Time to Setup: 10 minutes**

---

## Prerequisites

- Python 3.8+ installed
- Docker & Docker Compose installed
- Git installed

---

## 1️⃣ Clone & Configure (2 min)

```bash
# Clone repository
git clone <your-repo-url>
cd "Crypto Volatility Real Time"

# Create environment configuration
cp .env.example .env

# Edit .env with your values (optional - defaults work for local development)
nano .env
```

---

## 2️⃣ Start All Services (3 min)

```bash
# Start all 7 services (Kafka, Zookeeper, MLflow, API, Prometheus, Grafana, Kafka Lag Monitor)
cd docker
docker-compose up -d

# Verify all services are running
docker-compose ps

# Expected: 7 services in "Up" state
```

---

## 3️⃣ Install Dependencies (2 min)

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python packages
pip install -r requirements.txt
```

---

## 4️⃣ Start Data Pipeline (2 min)

**Note:** The API server is already running via Docker Compose from Step 2!

```bash
# Terminal 1: Start WebSocket producer
python scripts/ws_ingest_resilient.py

# Terminal 2: Start Kafka consumer
python scripts/kafka_consumer_resilient.py
```

---

## ✅ Verify Installation

```bash
# Check API health
curl http://localhost:8000/health

# Expected: {"status": "healthy"}

# Test prediction
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "price": 50000,
    "bid": 49995,
    "ask": 50005,
    "return_10s": 0.0001,
    "return_30s": 0.0003,
    "return_60s": 0.0005,
    "volatility_30s": 0.015,
    "volatility_60s": 0.02,
    "volatility_120s": 0.025,
    "spread": 10.0,
    "intensity_30s": 100,
    "intensity_60s": 200,
    "intensity_120s": 400
  }'

# Expected: {"is_volatile": false, "confidence": 0.85, ...}
```

---

## 📊 Access Dashboards

| Service | URL | Credentials | Description |
|---------|-----|-------------|-------------|
| **API Docs** | http://localhost:8000/docs | - | Interactive API documentation |
| **API Health** | http://localhost:8000/health | - | Health check endpoint |
| **API Metrics** | http://localhost:8000/metrics | - | Prometheus metrics endpoint |
| **MLflow** | http://localhost:5001 | - | Model tracking & experiments |
| **Prometheus** | http://localhost:9090 | - | Metrics collection & queries |
| **Grafana** | http://localhost:3000 | admin/admin | Real-time monitoring dashboards |
| **Kafka Lag** | http://localhost:9091/metrics | - | Consumer lag metrics |

---

## 🧪 Run Tests

```bash
# Unit tests
pytest tests/ -v

# Integration tests
pytest tests/test_integration.py -v

# Load tests
python3 tests/load_test.py --requests 100 --workers 10
```

---

## 🛑 Stop Services

```bash
# Stop all Docker services
docker-compose down

# Stop with cleanup
docker-compose down -v  # Also removes volumes
```

---

## 🔧 Configuration Options

### Environment Variables

Key configurations in `.env`:

- **KAFKA_BOOTSTRAP_SERVERS** - Kafka broker address (default: localhost:9092)
- **API_PORT** - FastAPI server port (default: 8000)
- **LOG_LEVEL** - Logging verbosity (INFO, DEBUG, WARNING, ERROR)
- **ENVIRONMENT** - Deployment environment (development, staging, production)

See `.env.example` for all available options.

---

## 📚 Documentation

### Core Documentation
- **README.md** - Complete project documentation (875 lines)
- **WEEK6_COMPLETION_SUMMARY.md** - Week 6 deliverables status

### Architecture & Operations
- **docs/architecture_diagram.md** - System architecture with Mermaid diagram
- **docs/slo.md** - Service Level Objectives (450+ lines)
- **docs/runbook.md** - Operations runbook (650+ lines)
- **docs/drift_summary.md** - Drift detection analysis (450+ lines)
- **docs/MODEL_CARD.md** - Model documentation

---

## 🆘 Troubleshooting

**Issue:** Kafka connection refused
```bash
# Check if Kafka is running
docker-compose ps kafka

# Restart Kafka
docker-compose restart kafka
```

**Issue:** API not responding
```bash
# Check API logs
docker-compose logs api

# Restart API
docker-compose restart api
```

**Issue:** Missing model file
```bash
# Train model first
python ml/train.py

# Or use pre-trained model from MLflow
```

**Issue:** Grafana dashboard not showing data
```bash
# Check Prometheus is scraping metrics
curl http://localhost:9090/api/v1/targets

# Restart Grafana
docker-compose restart grafana
```

---

## ⚡ Quick Commands Reference

```bash
# View all service logs
cd docker && docker-compose logs -f

# View specific service logs
docker-compose logs -f api
docker-compose logs -f kafka
docker-compose logs -f grafana

# Check Kafka topics
docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:9092

# Generate Evidently drift report
conda run -n evidently-env python scripts/generate_evidently_tutorial_style.py

# View drift report
open reports/drift/evidently_drift_*.html

# Check system health
python scripts/verify_week6_system.py

# Monitor Kafka lag
python scripts/kafka_lag_monitor.py

# Run code formatter
black api/ scripts/ tests/

# Run linter
ruff check api/ scripts/ tests/

# Generate coverage report
pytest --cov=api --cov-report=html
```

---

## 🎯 View Grafana Dashboard

1. Open http://localhost:3000
2. Login: `admin` / `admin`
3. Navigate to: **Dashboards** → **Crypto Volatility API - Production Monitoring**
4. View 3 panels: API Latency, Error Rate, Consumer Lag

---

**Total Setup Time:** ~10 minutes

**Status:** Production-ready monitoring system! 🎉
