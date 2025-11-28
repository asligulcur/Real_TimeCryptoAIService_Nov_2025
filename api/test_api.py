"""
Test script for the Crypto Volatility API.

Tests all endpoints with sample data.
"""

import requests
import json
import time
from datetime import datetime

# API configuration
BASE_URL = "http://localhost:8000"

# Sample feature data (matches your test data)
SAMPLE_FEATURES = {
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
    "intensity_120s": 52.3,
}

# High volatility sample (likely to predict spike)
HIGH_VOLATILITY_FEATURES = {
    "price": 91500.00,
    "bid": 91450.00,
    "ask": 91550.00,
    "spread": 100.0,
    "volatility_30s": 0.085,  # High volatility
    "volatility_60s": 0.092,
    "volatility_120s": 0.098,
    "return_10s": 0.015,
    "return_30s": 0.025,
    "return_60s": 0.032,
    "intensity_30s": 150.5,
    "intensity_60s": 280.3,
    "intensity_120s": 520.8,
}


def print_section(title):
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print("=" * 60)


def test_root():
    """Test root endpoint."""
    print_section("TEST 1: Root Endpoint (GET /)")

    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Status Code: {response.status_code}")
        print(f"Response:\n{json.dumps(response.json(), indent=2)}")

        assert response.status_code == 200, "Root endpoint failed"
        print("✅ Root endpoint working")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_health():
    """Test health endpoint."""
    print_section("TEST 2: Health Check (GET /health)")

    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status Code: {response.status_code}")

        data = response.json()
        print(f"Response:\n{json.dumps(data, indent=2)}")

        assert response.status_code == 200, "Health check failed"
        assert data["status"] in ["healthy", "degraded"], "Invalid status"
        assert "model_loaded" in data, "Missing model_loaded field"

        print(f"\n✅ Health check working")
        print(f"   Status: {data['status']}")
        print(f"   Model Loaded: {data['model_loaded']}")
        print(f"   Uptime: {data['uptime_seconds']:.2f}s")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_version():
    """Test version endpoint."""
    print_section("TEST 3: Version Info (GET /version)")

    try:
        response = requests.get(f"{BASE_URL}/version")
        print(f"Status Code: {response.status_code}")

        data = response.json()
        print(f"Response:\n{json.dumps(data, indent=2)}")

        assert response.status_code == 200, "Version endpoint failed"
        assert "api_version" in data, "Missing api_version"
        assert "model_version" in data, "Missing model_version"

        print(f"\n✅ Version endpoint working")
        print(f"   API Version: {data['api_version']}")
        print(f"   Model Version: {data['model_version']}")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_predict_normal():
    """Test prediction endpoint with normal volatility."""
    print_section("TEST 4: Prediction - Normal Volatility (POST /predict)")

    try:
        print("Input Features:")
        print(json.dumps(SAMPLE_FEATURES, indent=2))

        response = requests.post(
            f"{BASE_URL}/predict",
            json=SAMPLE_FEATURES,
            headers={"Content-Type": "application/json"},
        )

        print(f"\nStatus Code: {response.status_code}")

        data = response.json()
        print(f"Response:\n{json.dumps(data, indent=2)}")

        assert response.status_code == 200, "Prediction failed"
        assert "prediction" in data, "Missing prediction"
        assert "probability" in data, "Missing probability"

        print(f"\n✅ Prediction working")
        print(f"   Prediction: {'SPIKE' if data['prediction'] == 1 else 'NORMAL'}")
        print(f"   Probability: {data['probability']:.4f}")
        print(f"   Model Version: {data['model_version']}")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_predict_spike():
    """Test prediction endpoint with high volatility."""
    print_section("TEST 5: Prediction - High Volatility (POST /predict)")

    try:
        print("Input Features (High Volatility):")
        print(json.dumps(HIGH_VOLATILITY_FEATURES, indent=2))

        response = requests.post(
            f"{BASE_URL}/predict",
            json=HIGH_VOLATILITY_FEATURES,
            headers={"Content-Type": "application/json"},
        )

        print(f"\nStatus Code: {response.status_code}")

        data = response.json()
        print(f"Response:\n{json.dumps(data, indent=2)}")

        assert response.status_code == 200, "Prediction failed"

        print(f"\n✅ High volatility prediction working")
        print(f"   Prediction: {'SPIKE' if data['prediction'] == 1 else 'NORMAL'}")
        print(f"   Probability: {data['probability']:.4f}")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_predict_batch():
    """Test batch prediction endpoint."""
    print_section("TEST 6: Batch Prediction (POST /predict/batch)")

    try:
        batch_data = {"features": [SAMPLE_FEATURES, HIGH_VOLATILITY_FEATURES]}

        print("Batch Input: 2 feature sets")

        response = requests.post(
            f"{BASE_URL}/predict/batch",
            json=batch_data,
            headers={"Content-Type": "application/json"},
        )

        print(f"\nStatus Code: {response.status_code}")

        data = response.json()
        print(f"Response count: {data['count']} predictions")

        for i, pred in enumerate(data["predictions"]):
            print(f"\nPrediction {i+1}:")
            print(f"  Result: {'SPIKE' if pred['prediction'] == 1 else 'NORMAL'}")
            print(f"  Probability: {pred['probability']:.4f}")

        assert response.status_code == 200, "Batch prediction failed"
        assert data["count"] == 2, "Wrong number of predictions"

        print(f"\n✅ Batch prediction working")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_metrics():
    """Test metrics endpoint."""
    print_section("TEST 7: Prometheus Metrics (GET /metrics)")

    try:
        response = requests.get(f"{BASE_URL}/metrics")
        print(f"Status Code: {response.status_code}")

        metrics_text = response.text
        print(f"\nSample Metrics (first 500 chars):")
        print(metrics_text[:500])
        print("...")

        assert response.status_code == 200, "Metrics endpoint failed"
        assert "predict_requests_total" in metrics_text, "Missing prediction metrics"

        print(f"\n✅ Metrics endpoint working")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_latency():
    """Test prediction latency."""
    print_section("TEST 8: Latency Test (10 predictions)")

    try:
        latencies = []

        for i in range(10):
            start = time.time()
            response = requests.post(f"{BASE_URL}/predict", json=SAMPLE_FEATURES)
            latency = (time.time() - start) * 1000  # Convert to ms
            latencies.append(latency)

            if response.status_code != 200:
                print(f"❌ Request {i+1} failed")
                return False

        avg_latency = sum(latencies) / len(latencies)
        min_latency = min(latencies)
        max_latency = max(latencies)

        print(f"Completed 10 predictions:")
        print(f"  Average: {avg_latency:.2f}ms")
        print(f"  Min: {min_latency:.2f}ms")
        print(f"  Max: {max_latency:.2f}ms")

        print(f"\n✅ Latency test passed")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("  CRYPTO VOLATILITY API - TEST SUITE")
    print("=" * 60)
    print(f"Testing API at: {BASE_URL}")
    print(f"Time: {datetime.now().isoformat()}")

    # Check if API is reachable
    try:
        response = requests.get(f"{BASE_URL}/", timeout=2)
        print("✅ API is reachable")
    except Exception as e:
        print(f"\n❌ Cannot reach API at {BASE_URL}")
        print(f"Error: {e}")
        print("\nMake sure the API is running:")
        print("  cd api && ./start_api.sh")
        return

    # Run all tests
    tests = [
        test_root,
        test_health,
        test_version,
        test_predict_normal,
        test_predict_spike,
        test_predict_batch,
        test_metrics,
        test_latency,
    ]

    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
            time.sleep(0.5)  # Brief pause between tests
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)

    # Summary
    print_section("TEST SUMMARY")
    passed = sum(results)
    total = len(results)

    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")

    if passed == total:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
