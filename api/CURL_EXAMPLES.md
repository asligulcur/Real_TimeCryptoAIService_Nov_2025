# API Testing with curl

## Quick Reference

```bash
# Base URL
BASE_URL="http://localhost:8000"
```

## 1. Health Check

```bash
curl -X GET http://localhost:8000/health | jq
```

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-26T10:30:45.123456",
  "model_loaded": true,
  "uptime_seconds": 123.45
}
```

---

## 2. Version Information

```bash
curl -X GET http://localhost:8000/version | jq
```

**Expected Response:**
```json
{
  "api_version": "1.0.0",
  "model_version": "1.0",
  "service_name": "crypto-volatility-api",
  "python_version": "3.13.0",
  "dependencies": {
    "fastapi": "0.115.0",
    "scikit-learn": "1.7.2",
    "pandas": "2.3.3",
    "numpy": "2.3.4"
  }
}
```

---

## 3. Single Prediction (Normal Volatility)

```bash
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

**Expected Response:**
```json
{
  "prediction": 0,
  "probability": 0.1234,
  "timestamp": "2025-11-26T10:30:45.123456",
  "model_version": "1.0"
}
```

---

## 4. Single Prediction (High Volatility - Likely Spike)

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "price": 91500.00,
    "bid": 91450.00,
    "ask": 91550.00,
    "spread": 100.0,
    "volatility_30s": 0.085,
    "volatility_60s": 0.092,
    "volatility_120s": 0.098,
    "return_10s": 0.015,
    "return_30s": 0.025,
    "return_60s": 0.032,
    "intensity_30s": 150.5,
    "intensity_60s": 280.3,
    "intensity_120s": 520.8
  }' | jq
```

**Expected Response:**
```json
{
  "prediction": 1,
  "probability": 0.8765,
  "timestamp": "2025-11-26T10:30:45.123456",
  "model_version": "1.0"
}
```

---

## 5. Batch Prediction

```bash
curl -X POST http://localhost:8000/predict/batch \
  -H "Content-Type: application/json" \
  -d '{
    "features": [
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
      },
      {
        "price": 91500.00,
        "bid": 91450.00,
        "ask": 91550.00,
        "spread": 100.0,
        "volatility_30s": 0.085,
        "volatility_60s": 0.092,
        "volatility_120s": 0.098,
        "return_10s": 0.015,
        "return_30s": 0.025,
        "return_60s": 0.032,
        "intensity_30s": 150.5,
        "intensity_60s": 280.3,
        "intensity_120s": 520.8
      }
    ]
  }' | jq
```

**Expected Response:**
```json
{
  "predictions": [
    {
      "prediction": 0,
      "probability": 0.1234,
      "timestamp": "2025-11-26T10:30:45.123456",
      "model_version": "1.0"
    },
    {
      "prediction": 1,
      "probability": 0.8765,
      "timestamp": "2025-11-26T10:30:45.789012",
      "model_version": "1.0"
    }
  ],
  "count": 2
}
```

---

## 6. Prometheus Metrics

```bash
curl -X GET http://localhost:8000/metrics
```

**Sample Output:**
```
# HELP predict_requests_total Total number of prediction requests
# TYPE predict_requests_total counter
predict_requests_total 15.0
# HELP predict_errors_total Total number of prediction errors
# TYPE predict_errors_total counter
predict_errors_total 0.0
# HELP predict_latency_seconds Prediction request latency in seconds
# TYPE predict_latency_seconds histogram
predict_latency_seconds_bucket{le="0.005"} 10.0
predict_latency_seconds_bucket{le="0.01"} 15.0
predict_latency_seconds_sum 0.0456
predict_latency_seconds_count 15.0
```

---

## 7. Interactive API Documentation

Open in browser:
```bash
open http://localhost:8000/docs
```

Or for ReDoc format:
```bash
open http://localhost:8000/redoc
```

---

## Performance Test

Test latency with 100 requests:

```bash
for i in {1..100}; do
  curl -s -X POST http://localhost:8000/predict \
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
    }' > /dev/null
done
echo "✅ Completed 100 predictions"
```

Then check metrics:
```bash
curl -s http://localhost:8000/metrics | grep predict_requests_total
curl -s http://localhost:8000/metrics | grep predict_latency
```

---

## Notes

- **Remove `| jq`** if you don't have jq installed (JSON formatter)
- **Port 8000** is the default - change if using different port
- **All timestamps** are in UTC ISO format
- **Probabilities** are for class 1 (spike), range 0.0-1.0
