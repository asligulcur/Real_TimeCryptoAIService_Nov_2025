# Crypto Volatility Detection API

**Real-time REST API for cryptocurrency volatility spike prediction**

---

## 📋 Overview

This FastAPI service provides a production-ready REST API for predicting Bitcoin volatility spikes in real-time. The API loads a pre-trained Random Forest model and exposes endpoints for health checks, predictions, versioning, and Prometheus metrics.

### Key Features

- ✅ **4 Core Endpoints**: `/health`, `/predict`, `/version`, `/metrics`
- ✅ **Batch Predictions**: Process multiple samples efficiently
- ✅ **Prometheus Metrics**: Built-in monitoring and observability
- ✅ **Auto-generated Docs**: Interactive Swagger UI at `/docs`
- ✅ **Production-ready**: Request validation, error handling, latency tracking
- ✅ **Fast**: <5ms prediction latency

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# From project root
pip install -r requirements.txt
```

Required packages:
- `fastapi==0.115.0`
- `uvicorn[standard]==0.32.0`
- `prometheus-client==0.21.0`
- `scikit-learn==1.7.2`
- `pandas==2.3.3`

### 2. Start the API

```bash
# Option A: Using the helper script
cd api
./start_api.sh

# Option B: Using uvicorn directly
cd api
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API will start on `http://localhost:8000`

### 3. Test the API

```bash
# Health check
curl http://localhost:8000/health

# Interactive docs
open http://localhost:8000/docs
```

---

## 📡 API Endpoints

### 1. **GET /** - Root/Welcome
Returns API information and available endpoints.

```bash
curl http://localhost:8000/
```

### 2. **GET /health** - Health Check
Check service status and model availability.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-26T10:30:45.123456",
  "model_loaded": true,
  "uptime_seconds": 123.45
}
```

### 3. **GET /version** - Version Information
Get API version, model version, and dependency versions.

**Response:**
```json
{
  "api_version": "1.0.0",
  "model_version": "1.0",
  "service_name": "crypto-volatility-api",
  "python_version": "3.13.0",
  "dependencies": {
    "fastapi": "0.115.0",
    "scikit-learn": "1.7.2"
  }
}
```

### 4. **POST /predict** - Make Prediction
Predict volatility spike for given features.

**Request Body:**
```json
{
  "price": 91234.56,
  "bid": 91234.00,
  "ask": 91235.00,
  "spread": 1.0,
  "volatility_30s": 0.0123,
  "volatility_60s": 0.0145,
  "volatility_120s": 0.0167,
  "return_10s": 0.0001,
  "return_30s": 0.0003,
  "return_60s": 0.0005,
  "intensity_30s": 15.2,
  "intensity_60s": 28.5,
  "intensity_120s": 52.3
}
```

**Response:**
```json
{
  "prediction": 0,
  "probability": 0.1234,
  "timestamp": "2025-11-26T10:30:45.123456",
  "model_version": "1.0"
}
```

- `prediction`: 0 = normal, 1 = spike
- `probability`: Confidence score (0.0-1.0) for spike prediction

### 5. **POST /predict/batch** - Batch Predictions
Process multiple predictions in one request.

**Request Body:**
```json
{
  "features": [
    { /* feature set 1 */ },
    { /* feature set 2 */ }
  ]
}
```

### 6. **GET /metrics** - Prometheus Metrics
Exposes metrics for monitoring (Prometheus format).

**Metrics Available:**
- `predict_requests_total` - Total prediction requests
- `predict_errors_total` - Total prediction errors
- `predict_latency_seconds` - Prediction latency histogram
- `health_requests_total` - Health check requests

---

## 🧪 Testing

### Automated Test Suite

```bash
cd api
python test_api.py
```

This runs 8 comprehensive tests covering all endpoints.

### Manual Testing with curl

See [`CURL_EXAMPLES.md`](./CURL_EXAMPLES.md) for detailed curl commands.

Quick test:
```bash
# Health
curl http://localhost:8000/health | jq

# Prediction
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "price": 91234.56,
    "bid": 91234.00,
    "ask": 91235.00,
    "spread": 1.0,
    "volatility_30s": 0.0123,
    "volatility_60s": 0.0145,
    "volatility_120s": 0.0167,
    "return_10s": 0.0001,
    "return_30s": 0.0003,
    "return_60s": 0.0005,
    "intensity_30s": 15.2,
    "intensity_60s": 28.5,
    "intensity_120s": 52.3
  }' | jq
```

---

## 📊 Performance

- **Latency**: <5ms per prediction (measured)
- **Throughput**: ~200 requests/second (single instance)
- **Model Load Time**: <1 second on startup

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│           FastAPI Application                │
│                                              │
│  ┌─────────┐  ┌─────────┐  ┌────────────┐ │
│  │ /health │  │/predict │  │  /metrics  │  │
│  └─────────┘  └─────────┘  └────────────┘  │
│                                              │
│  ┌──────────────────────────────────────┐  │
│  │   Random Forest Model (joblib)       │   │
│  │   - 100 estimators                   │   │
│  │   - 13 features                      │   │
│  │   - F1=0.9984, PR-AUC=1.0000         │   │
│  └──────────────────────────────────────┘  │
│                                              │
│  ┌──────────────────────────────────────┐  │
│  │   Prometheus Metrics                 │   │
│  │   - Request counters                 │   │
│  │   - Latency histograms               │   │
│  └──────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

---

## 🐳 Docker Deployment

### Dockerfile (create as `Dockerfile.api`)

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy API code
COPY api/ ./api/
COPY models/artifacts/ ./models/artifacts/

# Expose port
EXPOSE 8000

# Run API
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose Integration

Add to `docker-compose.yaml`:

```yaml
  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    container_name: crypto-api
    ports:
      - "8000:8000"
    volumes:
      - ./models/artifacts:/app/models/artifacts:ro
    environment:
      - MODEL_PATH=/app/models/artifacts/random_forest.joblib
    depends_on:
      - mlflow
    restart: unless-stopped
```

---

## 📝 Feature Schema

All 13 features required for prediction:

| Feature | Type | Description | Example |
|---------|------|-------------|---------|
| `price` | float | Current BTC-USD price | 91234.56 |
| `bid` | float | Best bid price | 91234.00 |
| `ask` | float | Best ask price | 91235.00 |
| `spread` | float | Bid-ask spread | 1.0 |
| `volatility_30s` | float | 30s rolling std dev | 0.0123 |
| `volatility_60s` | float | 60s rolling std dev | 0.0145 |
| `volatility_120s` | float | 120s rolling std dev | 0.0167 |
| `return_10s` | float | 10s price return | 0.0001 |
| `return_30s` | float | 30s price return | 0.0003 |
| `return_60s` | float | 60s price return | 0.0005 |
| `intensity_30s` | float | 30s trade intensity | 15.2 |
| `intensity_60s` | float | 60s trade intensity | 28.5 |
| `intensity_120s` | float | 120s trade intensity | 52.3 |

---

## 🔧 Configuration

### Environment Variables

- `MODEL_PATH`: Path to model file (default: `../models/artifacts/random_forest.joblib`)
- `API_PORT`: API port (default: 8000)
- `LOG_LEVEL`: Logging level (default: info)

### Model Configuration

The API loads the production Random Forest model:
- **Location**: `models/artifacts/random_forest.joblib`
- **Version**: 1.0
- **Performance**: F1=0.9984, PR-AUC=1.0000
- **Features**: 13 engineered features

---

## 🐛 Troubleshooting

### Model Not Found

```
Error: Model not found at /path/to/model
```

**Solution**: Ensure model file exists at `models/artifacts/random_forest.joblib`

```bash
ls -lh models/artifacts/random_forest.joblib
```

### Port Already in Use

```
Error: Address already in use
```

**Solution**: Kill process on port 8000 or use different port

```bash
# Find process
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port
uvicorn main:app --port 8001
```

### Import Errors

```
ModuleNotFoundError: No module named 'fastapi'
```

**Solution**: Install dependencies

```bash
pip install -r requirements.txt
```

---

## 📚 Additional Resources

- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Model Card**: `../docs/MODEL_CARD.md`
- **Feature Spec**: `../docs/feature_spec.md`

---

## 👥 Team

**CMU Heinz College - Operationalizing AI**  
Week 4 Deliverable: API Development

---

## 📄 License

Educational project for CMU Heinz College course.

---

**Need help?** Check the `/docs` endpoint or contact the team.
