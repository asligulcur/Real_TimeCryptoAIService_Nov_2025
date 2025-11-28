# Docker Deployment Guide

## ✅ What We Just Created

1. **`Dockerfile.api`** - Containerizes your FastAPI service
2. **Updated `docker/compose.yaml`** - Added API service to your existing setup
3. **`docker/start_all.sh`** - One-command startup script

## 🚀 How to Run Everything

### Step 1: Start Docker Desktop
Make sure Docker Desktop is running on your Mac.

### Step 2: Start All Services
```bash
cd docker
./start_all.sh
```

This will start:
- Zookeeper (port 2181)
- Kafka (port 9092)
- MLflow (port 5001)
- **FastAPI** (port 8000) ← NEW!

### Step 3: Verify API is Running
```bash
# Check health
curl http://localhost:8000/health | python3 -m json.tool

# Get version
curl http://localhost:8000/version | python3 -m json.tool

# Make a prediction
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "volatility_30s": 0.025,
    "rsi_30s": 65.0,
    "macd_30s": 0.0015,
    "volume_30s": 250000.0,
    "price_change_pct_30s": 0.008,
    "bid_ask_spread_30s": 0.05,
    "trade_intensity_30s": 45.0,
    "volatility_60s": 0.022,
    "rsi_60s": 62.0,
    "macd_60s": 0.0012,
    "volume_60s": 480000.0,
    "price_change_pct_60s": 0.015,
    "price_momentum_30s": 0.003
  }' | python3 -m json.tool
```

## 📊 Useful Commands

### View Logs
```bash
# All services
docker compose logs -f

# Just the API
docker compose logs -f api

# Last 50 lines
docker compose logs --tail=50 api
```

### Check Status
```bash
docker compose ps
```

### Restart Just the API
```bash
docker compose restart api
```

### Stop Everything
```bash
docker compose down
```

### Rebuild API (after code changes)
```bash
docker compose up -d --build api
```

## 🌐 Access Points

| Service | URL | Purpose |
|---------|-----|---------|
| FastAPI Root | http://localhost:8000 | API welcome page |
| **Swagger Docs** | http://localhost:8000/docs | Interactive API documentation |
| Health Check | http://localhost:8000/health | Service health status |
| Version | http://localhost:8000/version | API/Model version info |
| Metrics | http://localhost:8000/metrics | Prometheus metrics |
| MLflow | http://localhost:5001 | Experiment tracking |

## 🔍 Troubleshooting

### "Cannot connect to Docker daemon"
- Start Docker Desktop application
- Wait for Docker to fully start (whale icon in menu bar should be stable)

### API Container Won't Start
```bash
# Check logs for errors
docker compose logs api

# Check if model file exists
docker compose exec api ls -lh /app/models/artifacts/
```

### Port Already in Use
If port 8000 is taken:
1. Edit `docker/compose.yaml`
2. Change `"8000:8000"` to `"8001:8000"` (or another port)
3. Run `docker compose up -d --build api`

### Model Not Loading
```bash
# Verify model file is mounted correctly
docker compose exec api ls -lh /app/models/artifacts/random_forest.joblib

# Check file permissions
ls -lh models/artifacts/random_forest.joblib
```

## 📦 What's in the Container?

```
/app/
├── api/
│   ├── main.py              # FastAPI application
│   ├── test_api.py          # Test suite
│   └── ...
├── models/
│   └── artifacts/
│       └── random_forest.joblib  # Your trained model (102KB)
└── requirements.txt         # Python dependencies
```

## 🎯 Week 4 Demo

For your Week 4 demo, just run:
```bash
cd docker
./start_all.sh
```

Then show:
1. **Health check**: `curl http://localhost:8000/health`
2. **Interactive docs**: Open http://localhost:8000/docs in browser
3. **Live prediction**: Use curl command from above
4. **Metrics**: `curl http://localhost:8000/metrics`

## ✅ Week 4 Checklist

- [x] Dockerfile.api created
- [x] docker-compose.yaml updated with API service
- [x] Health checks configured
- [x] Volume mounts for model artifacts
- [x] Port 8000 exposed
- [x] Startup script created
- [ ] Test with `docker compose up` (need Docker running)
- [ ] Team documentation (next step)
