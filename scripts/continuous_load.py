#!/usr/bin/env python3
"""
Continuous load generator for Grafana dashboard population.
Sends API requests at regular intervals to maintain live metrics.
"""

import random
import time
from datetime import datetime

import requests


def generate_features():
    """Generate realistic crypto market features."""
    price = 88000 + random.uniform(-1000, 1000)
    return {
        "price": price,
        "bid": price - random.uniform(0.5, 2.0),
        "ask": price + random.uniform(0.5, 2.0),
        "spread": random.uniform(0.5, 3.0),
        "volatility_30s": random.uniform(0.001, 0.05),
        "volatility_60s": random.uniform(0.002, 0.06),
        "volatility_120s": random.uniform(0.003, 0.07),
        "return_10s": random.uniform(-0.002, 0.002),
        "return_30s": random.uniform(-0.005, 0.005),
        "return_60s": random.uniform(-0.01, 0.01),
        "intensity_30s": random.uniform(5, 30),
        "intensity_60s": random.uniform(10, 50),
        "intensity_120s": random.uniform(20, 80),
    }


def main():
    """Run continuous load for 1 hour."""
    url = "http://localhost:8000/predict"
    headers = {"Content-Type": "application/json"}
    
    # Run for 1 hour, 1 request every 5 seconds = 720 requests
    duration_seconds = 3600
    interval_seconds = 5
    total_requests = duration_seconds // interval_seconds
    
    print(f"🚀 Starting continuous load generator")
    print(f"⏱️  Duration: 1 hour ({total_requests} requests)")
    print(f"📊 Interval: {interval_seconds} seconds")
    print(f"🎯 Target: {url}")
    print(f"⏰ Started at: {datetime.now().strftime('%H:%M:%S')}\n")
    
    success_count = 0
    error_count = 0
    
    for i in range(total_requests):
        try:
            payload = generate_features()
            start = time.time()
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            latency = (time.time() - start) * 1000
            
            if response.status_code == 200:
                success_count += 1
                data = response.json()
                pred = data.get("prediction", "?")
                prob = data.get("probability", 0)
                
                # Print every 10th request to avoid spam
                if (i + 1) % 10 == 0:
                    print(
                        f"✅ {i+1}/{total_requests} | "
                        f"Success: {success_count} | "
                        f"Errors: {error_count} | "
                        f"Latest: {latency:.0f}ms (pred={pred}, p={prob:.2f})"
                    )
            else:
                error_count += 1
                if error_count <= 5:  # Only print first 5 errors
                    print(f"❌ {i+1}/{total_requests} | Status: {response.status_code}")
            
            time.sleep(interval_seconds)
            
        except KeyboardInterrupt:
            print(f"\n⚠️  Interrupted by user at request {i+1}/{total_requests}")
            break
        except Exception as e:
            error_count += 1
            if error_count <= 5:
                print(f"❌ {i+1}/{total_requests} | Error: {str(e)[:80]}")
            time.sleep(interval_seconds)
    
    print(f"\n✅ Load generation complete!")
    print(f"📊 Final stats:")
    print(f"   - Total requests: {i+1}")
    print(f"   - Successful: {success_count}")
    print(f"   - Errors: {error_count}")
    print(f"   - Success rate: {(success_count/(i+1)*100):.1f}%")
    print(f"⏰ Finished at: {datetime.now().strftime('%H:%M:%S')}")


if __name__ == "__main__":
    main()
