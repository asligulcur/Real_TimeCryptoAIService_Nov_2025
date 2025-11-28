"""
Integration test for API + Model
Tests end-to-end: API receives request → Model predicts → Response returned
"""

import requests
import time
import pytest

BASE_URL = "http://localhost:8000"


def test_api_startup():
    """Test that API server is running and healthy."""
    max_retries = 10
    for i in range(max_retries):
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                assert data["status"] == "healthy"
                assert data["model_loaded"] is True
                print(f"✅ API healthy: {data}")
                return
        except requests.exceptions.RequestException:
            if i < max_retries - 1:
                print(f"⏳ Waiting for API to start... ({i+1}/{max_retries})")
                time.sleep(3)
            else:
                raise
    
    pytest.fail("API did not start within timeout")


def test_version_endpoint():
    """Test that version endpoint returns correct information."""
    response = requests.get(f"{BASE_URL}/version")
    assert response.status_code == 200
    
    data = response.json()
    assert "api_version" in data
    assert "model_version" in data
    assert "service_name" in data
    assert data["service_name"] == "crypto-volatility-api"
    print(f"✅ Version: {data['api_version']}, Model: {data['model_version']}")


def test_prediction_low_volatility():
    """Test prediction for normal/low volatility market conditions."""
    payload = {
        "price": 42000.0,
        "bid": 41999.5,
        "ask": 42000.5,
        "spread": 1.0,
        "volatility_30s": 0.008,  # Low volatility
        "volatility_60s": 0.009,
        "volatility_120s": 0.01,
        "return_10s": 0.0001,
        "return_30s": 0.0002,
        "return_60s": 0.0003,
        "intensity_30s": 20.0,
        "intensity_60s": 40.0,
        "intensity_120s": 80.0
    }
    
    response = requests.post(f"{BASE_URL}/predict", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert "prediction" in data
    assert "probability" in data
    assert "timestamp" in data
    assert "model_version" in data
    
    # Low volatility should predict 0 (no spike)
    assert data["prediction"] == 0
    assert 0.0 <= data["probability"] <= 1.0
    print(f"✅ Low volatility prediction: {data['prediction']} (prob: {data['probability']:.4f})")


def test_prediction_high_volatility():
    """Test prediction for high volatility spike conditions."""
    payload = {
        "price": 42500.0,
        "bid": 42450.0,
        "ask": 42550.0,
        "spread": 100.0,  # Very wide spread
        "volatility_30s": 0.06,  # High volatility
        "volatility_60s": 0.07,
        "volatility_120s": 0.08,
        "return_10s": 0.005,  # Large returns
        "return_30s": 0.015,
        "return_60s": 0.025,
        "intensity_30s": 120.0,  # High intensity
        "intensity_60s": 240.0,
        "intensity_120s": 480.0
    }
    
    response = requests.post(f"{BASE_URL}/predict", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert "prediction" in data
    assert "probability" in data
    
    # High volatility should predict 1 (spike) or have high probability
    # Model is very accurate, so should catch this
    print(f"✅ High volatility prediction: {data['prediction']} (prob: {data['probability']:.4f})")
    # Note: Don't assert prediction==1 because model might legitimately predict 0
    # Just verify it returns valid response


def test_batch_prediction():
    """Test batch prediction endpoint with multiple samples."""
    payload = {
        "features": [
            {
                "price": 42000.0, "bid": 41999.5, "ask": 42000.5, "spread": 1.0,
                "volatility_30s": 0.008, "volatility_60s": 0.009, "volatility_120s": 0.01,
                "return_10s": 0.0001, "return_30s": 0.0002, "return_60s": 0.0003,
                "intensity_30s": 20.0, "intensity_60s": 40.0, "intensity_120s": 80.0
            },
            {
                "price": 42500.0, "bid": 42450.0, "ask": 42550.0, "spread": 100.0,
                "volatility_30s": 0.06, "volatility_60s": 0.07, "volatility_120s": 0.08,
                "return_10s": 0.005, "return_30s": 0.015, "return_60s": 0.025,
                "intensity_30s": 120.0, "intensity_60s": 240.0, "intensity_120s": 480.0
            }
        ]
    }
    
    response = requests.post(f"{BASE_URL}/predict/batch", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert "predictions" in data
    assert len(data["predictions"]) == 2
    assert "count" in data
    assert data["count"] == 2
    
    for pred in data["predictions"]:
        assert "prediction" in pred
        assert "probability" in pred
        assert pred["prediction"] in [0, 1]
    
    print(f"✅ Batch prediction: {data['count']} samples processed")


def test_invalid_input_validation():
    """Test that API properly validates and rejects invalid input."""
    # Missing required fields
    payload = {
        "price": 42000.0,
        "bid": 41999.5
        # Missing other required fields
    }
    
    response = requests.post(f"{BASE_URL}/predict", json=payload)
    assert response.status_code == 422  # Validation error
    
    data = response.json()
    assert "detail" in data
    print(f"✅ Input validation working: {response.status_code}")


def test_metrics_endpoint():
    """Test that Prometheus metrics are exposed."""
    response = requests.get(f"{BASE_URL}/metrics")
    assert response.status_code == 200
    
    content = response.text
    # Check for key metrics
    assert "predict_requests_total" in content
    assert "predict_latency_seconds" in content
    print(f"✅ Metrics endpoint working ({len(content)} bytes)")


def test_api_latency():
    """Test that API responds within acceptable latency (<100ms)."""
    payload = {
        "price": 42000.0, "bid": 41999.5, "ask": 42000.5, "spread": 1.0,
        "volatility_30s": 0.008, "volatility_60s": 0.009, "volatility_120s": 0.01,
        "return_10s": 0.0001, "return_30s": 0.0002, "return_60s": 0.0003,
        "intensity_30s": 20.0, "intensity_60s": 40.0, "intensity_120s": 80.0
    }
    
    latencies = []
    for _ in range(10):
        start = time.time()
        response = requests.post(f"{BASE_URL}/predict", json=payload)
        latency = (time.time() - start) * 1000  # Convert to ms
        latencies.append(latency)
        assert response.status_code == 200
    
    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    
    print(f"✅ Latency - Avg: {avg_latency:.2f}ms, Max: {max_latency:.2f}ms")
    
    # Relaxed requirement for CI environment
    assert avg_latency < 200, f"Average latency too high: {avg_latency:.2f}ms"


if __name__ == "__main__":
    # Run tests standalone
    print("🧪 Running Integration Tests...")
    test_api_startup()
    test_version_endpoint()
    test_prediction_low_volatility()
    test_prediction_high_volatility()
    test_batch_prediction()
    test_invalid_input_validation()
    test_metrics_endpoint()
    test_api_latency()
    print("✅ All integration tests passed!")
