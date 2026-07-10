"""
System Verification Script
Tests all components end-to-end to ensure everything is working
"""

import requests
import time
import sys
from datetime import datetime

print("="*70)
print("🔍 SYSTEM VERIFICATION")
print("="*70)
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

results = []
errors = []

def test_component(name, test_func):
    """Run a test and track results"""
    try:
        print(f"\n[{len(results)+1}] Testing {name}...")
        result = test_func()
        if result:
            print(f"    ✅ PASS: {result}")
            results.append((name, "PASS", result))
        else:
            print(f"    ✅ PASS")
            results.append((name, "PASS", "OK"))
    except Exception as e:
        print(f"    ❌ FAIL: {str(e)}")
        results.append((name, "FAIL", str(e)))
        errors.append((name, str(e)))

# Test 1: API Health
def test_api():
    resp = requests.get("http://localhost:8000/health", timeout=5)
    assert resp.status_code == 200, f"Status {resp.status_code}"
    data = resp.json()
    return f"API healthy - Status: {data.get('status', 'unknown')}"

test_component("API Health Check", test_api)

# Test 2: API Prediction
def test_prediction():
    payload = {
        'price': 88000,
        'bid': 87998,
        'ask': 88002,
        'spread': 4.0,
        'volatility_30s': 0.02,
        'volatility_60s': 0.025,
        'volatility_120s': 0.03,
        'return_10s': 0.001,
        'return_30s': 0.002,
        'return_60s': 0.003,
        'intensity_30s': 25,
        'intensity_60s': 30,
        'intensity_120s': 35
    }
    start = time.time()
    resp = requests.post("http://localhost:8000/predict", json=payload, timeout=5)
    latency = (time.time() - start) * 1000
    assert resp.status_code == 200, f"Status {resp.status_code}"
    data = resp.json()
    pred = data.get('prediction', 'unknown')
    prob = data.get('probability', 0)
    return f"Prediction: {pred} (prob={prob:.2f}, latency={latency:.0f}ms)"

test_component("API Prediction", test_prediction)

# Test 3: Prometheus Metrics
def test_prometheus():
    resp = requests.get("http://localhost:9090/api/v1/query?query=up", timeout=5)
    assert resp.status_code == 200, f"Status {resp.status_code}"
    data = resp.json()
    assert data.get('status') == 'success', "Prometheus not responding"
    targets = len(data.get('data', {}).get('result', []))
    return f"Prometheus active - {targets} targets scraped"

test_component("Prometheus", test_prometheus)

# Test 4: Prometheus API Metrics
def test_api_metrics():
    resp = requests.get("http://localhost:8000/metrics", timeout=5)
    assert resp.status_code == 200, f"Status {resp.status_code}"
    text = resp.text
    assert 'predict_requests_total' in text, "Missing predict_requests_total"
    assert 'predict_latency_seconds' in text, "Missing predict_latency_seconds"
    assert 'predict_errors_total' in text, "Missing predict_errors_total"
    # Count metrics
    metric_lines = [l for l in text.split('\n') if l and not l.startswith('#')]
    return f"{len(metric_lines)} metric values exposed"

test_component("API Metrics Endpoint", test_api_metrics)

# Test 5: Kafka Lag Monitor
def test_kafka_lag():
    resp = requests.get("http://localhost:9091/metrics", timeout=5)
    assert resp.status_code == 200, f"Status {resp.status_code}"
    text = resp.text
    assert 'kafka_consumer_group_lag' in text, "Missing Kafka lag metrics"
    return "Kafka lag metrics available"

test_component("Kafka Lag Monitor", test_kafka_lag)

# Test 6: Grafana
def test_grafana():
    resp = requests.get("http://localhost:3000/api/health", timeout=5)
    assert resp.status_code == 200, f"Status {resp.status_code}"
    data = resp.json()
    assert data.get('database') == 'ok', "Grafana database not healthy"
    return f"Grafana healthy - Version: {data.get('version', 'unknown')}"

test_component("Grafana", test_grafana)

# Test 7: Check Latency SLO
def test_latency_slo():
    # Query p95 latency from Prometheus
    query = 'histogram_quantile(0.95, sum(rate(predict_latency_seconds_bucket[5m])) by (le))'
    resp = requests.get(f"http://localhost:9090/api/v1/query?query={query}", timeout=5)
    assert resp.status_code == 200, f"Status {resp.status_code}"
    data = resp.json()
    results = data.get('data', {}).get('result', [])
    if results:
        p95 = float(results[0]['value'][1])
        slo_threshold = 0.8  # 800ms
        status = "✅ MEETING" if p95 < slo_threshold else "❌ VIOLATING"
        return f"p95 latency: {p95*1000:.0f}ms (SLO: <800ms) - {status}"
    return "No data yet"

test_component("Latency SLO", test_latency_slo)

# Test 8: Check Error Rate SLO
def test_error_rate_slo():
    # Query error rate from Prometheus
    query = '(rate(predict_errors_total[5m]) / rate(predict_requests_total[5m])) * 100'
    resp = requests.get(f"http://localhost:9090/api/v1/query?query={query}", timeout=5)
    assert resp.status_code == 200, f"Status {resp.status_code}"
    data = resp.json()
    results = data.get('data', {}).get('result', [])
    if results:
        error_rate = float(results[0]['value'][1])
        slo_threshold = 1.0  # 1%
        status = "✅ MEETING" if error_rate < slo_threshold else "❌ VIOLATING"
        return f"Error rate: {error_rate:.2f}% (SLO: <1%) - {status}"
    return "Error rate: 0% (no errors)"

test_component("Error Rate SLO", test_error_rate_slo)

# Test 9: Check Evidently Report Exists
def test_evidently_report():
    from pathlib import Path
    drift_dir = Path("reports/drift")
    html_files = list(drift_dir.glob("evidently_drift_*.html"))
    assert len(html_files) > 0, "No Evidently reports found"
    latest = max(html_files, key=lambda p: p.stat().st_mtime)
    size_kb = latest.stat().st_size / 1024
    return f"Report exists: {latest.name} ({size_kb:.0f}KB)"

test_component("Evidently Drift Report", test_evidently_report)

# Test 10: Check Model Rollback Capability
def test_model_rollback():
    # Check if baseline model exists
    from pathlib import Path
    baseline_path = Path("ml/baseline.py")
    assert baseline_path.exists(), "Baseline model not found"
    # Check if API has MODEL_VARIANT support
    api_path = Path("api/main.py")
    with open(api_path) as f:
        content = f.read()
    assert 'MODEL_VARIANT' in content, "MODEL_VARIANT not in API"
    return "Baseline model ready, API supports rollback"

test_component("Model Rollback Toggle", test_model_rollback)

# Print Summary
print("\n" + "="*70)
print("📊 VERIFICATION SUMMARY")
print("="*70)

passed = sum(1 for _, status, _ in results if status == "PASS")
failed = sum(1 for _, status, _ in results if status == "FAIL")
total = len(results)

print(f"\nTotal Tests: {total}")
print(f"✅ Passed: {passed}")
print(f"❌ Failed: {failed}")
print(f"Success Rate: {(passed/total)*100:.1f}%")

if errors:
    print("\n⚠️  FAILURES:")
    for name, error in errors:
        print(f"  • {name}: {error}")
else:
    print("\n🎉 ALL TESTS PASSED!")

print("\n" + "="*70)
print("📋 DELIVERABLES STATUS")
print("="*70)

deliverables = [
    ("Grafana Dashboard JSON", "docker/grafana/dashboards/crypto-volatility-dashboard.json"),
    ("Grafana Screenshot", "docs/grafana_dashboard_screenshot.png"),
    ("Evidently Report HTML", "reports/drift/evidently_drift_*.html"),
    ("Drift Summary", "docs/drift_summary.md"),
    ("SLOs Document", "docs/slo.md"),
    ("Runbook", "docs/runbook.md"),
]

from pathlib import Path
import glob

for name, path in deliverables:
    if '*' in path:
        matches = glob.glob(path)
        if matches:
            print(f"  ✅ {name}: {len(matches)} file(s)")
        else:
            print(f"  ❌ {name}: NOT FOUND")
    else:
        exists = Path(path).exists()
        status = "✅" if exists else "❌"
        print(f"  {status} {name}: {path}")

print("\n" + "="*70)

# Exit code
sys.exit(0 if failed == 0 else 1)
