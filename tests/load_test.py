#!/usr/bin/env python3
"""
Load Test Script for Crypto Volatility API
===========================================
Sends burst requests to the API and measures performance.

Features:
- Concurrent burst requests (100 by default)
- Latency percentiles (p50, p95, p99, max)
- Success/failure rates
- Throughput calculation
- Beautiful report generation

Usage:
    python3 load_test.py
    python3 load_test.py --requests 200 --workers 10
"""

import argparse
import json
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple
import requests

# ============================================================================
# CONFIGURATION
# ============================================================================

API_BASE_URL = "http://localhost:8000"
DEFAULT_NUM_REQUESTS = 100
DEFAULT_WORKERS = 10
TIMEOUT_SECONDS = 10

# Sample feature data (low volatility scenario)
SAMPLE_FEATURES = {
    "price": 42000.0,
    "bid": 41999.5,
    "ask": 42000.5,
    "spread": 1.0,
    "volatility_30s": 0.008,
    "volatility_60s": 0.009,
    "volatility_120s": 0.01,
    "return_10s": 0.0001,
    "return_30s": 0.0002,
    "return_60s": 0.0003,
    "intensity_30s": 20.0,
    "intensity_60s": 40.0,
    "intensity_120s": 80.0,
}

# ============================================================================
# LOAD TEST FUNCTIONS
# ============================================================================


def make_prediction_request(request_id: int) -> Dict:
    """
    Make a single prediction request and measure latency.

    Args:
        request_id: Unique identifier for this request

    Returns:
        Dict with timing and result info
    """
    start_time = time.time()
    result = {
        "request_id": request_id,
        "success": False,
        "latency_ms": 0,
        "status_code": None,
        "error": None,
    }

    try:
        response = requests.post(
            f"{API_BASE_URL}/predict",
            json=SAMPLE_FEATURES,
            timeout=TIMEOUT_SECONDS,
        )

        result["status_code"] = response.status_code
        result["success"] = response.status_code == 200

        if not result["success"]:
            result["error"] = f"HTTP {response.status_code}"

    except requests.exceptions.Timeout:
        result["error"] = "Timeout"
    except requests.exceptions.ConnectionError:
        result["error"] = "Connection refused"
    except Exception as e:
        result["error"] = str(e)
    finally:
        result["latency_ms"] = (time.time() - start_time) * 1000

    return result


def run_load_test(num_requests: int, num_workers: int) -> List[Dict]:
    """
    Run load test with concurrent workers.

    Args:
        num_requests: Total number of requests to send
        num_workers: Number of concurrent workers

    Returns:
        List of result dictionaries
    """
    print(f"🚀 Starting load test...")
    print(f"   Requests: {num_requests}")
    print(f"   Workers: {num_workers}")
    print(f"   Target: {API_BASE_URL}")
    print()

    results = []
    start_time = time.time()

    # Use ThreadPoolExecutor for concurrent requests
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        # Submit all requests
        futures = {
            executor.submit(make_prediction_request, i): i
            for i in range(num_requests)
        }

        # Collect results as they complete
        completed = 0
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            completed += 1

            # Progress indicator
            if completed % 10 == 0 or completed == num_requests:
                print(f"   Progress: {completed}/{num_requests} requests completed")

    total_time = time.time() - start_time
    print(f"\n✅ Load test completed in {total_time:.2f} seconds\n")

    return results


def calculate_percentile(values: List[float], percentile: float) -> float:
    """Calculate percentile value."""
    if not values:
        return 0
    sorted_values = sorted(values)
    index = int(len(sorted_values) * percentile / 100)
    return sorted_values[min(index, len(sorted_values) - 1)]


def analyze_results(results: List[Dict], total_time: float) -> Dict:
    """
    Analyze load test results and calculate statistics.

    Args:
        results: List of result dictionaries
        total_time: Total time taken for test

    Returns:
        Dictionary with analysis metrics
    """
    # Filter successful requests
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    # Get latencies (only from successful requests)
    latencies = [r["latency_ms"] for r in successful]

    # Calculate statistics
    analysis = {
        "total_requests": len(results),
        "successful_requests": len(successful),
        "failed_requests": len(failed),
        "success_rate": (len(successful) / len(results) * 100) if results else 0,
        "total_time_seconds": total_time,
        "requests_per_second": len(results) / total_time if total_time > 0 else 0,
    }

    # Latency statistics (only if we have successful requests)
    if latencies:
        analysis.update(
            {
                "latency_min_ms": min(latencies),
                "latency_max_ms": max(latencies),
                "latency_mean_ms": statistics.mean(latencies),
                "latency_median_ms": statistics.median(latencies),
                "latency_stddev_ms": (
                    statistics.stdev(latencies) if len(latencies) > 1 else 0
                ),
                "latency_p50_ms": calculate_percentile(latencies, 50),
                "latency_p95_ms": calculate_percentile(latencies, 95),
                "latency_p99_ms": calculate_percentile(latencies, 99),
            }
        )
    else:
        # No successful requests
        analysis.update(
            {
                "latency_min_ms": 0,
                "latency_max_ms": 0,
                "latency_mean_ms": 0,
                "latency_median_ms": 0,
                "latency_stddev_ms": 0,
                "latency_p50_ms": 0,
                "latency_p95_ms": 0,
                "latency_p99_ms": 0,
            }
        )

    # Error breakdown
    if failed:
        error_counts = {}
        for result in failed:
            error = result.get("error", "Unknown")
            error_counts[error] = error_counts.get(error, 0) + 1
        analysis["error_breakdown"] = error_counts
    else:
        analysis["error_breakdown"] = {}

    return analysis


def print_report(analysis: Dict):
    """
    Print beautiful load test report.

    Args:
        analysis: Analysis dictionary from analyze_results
    """
    print("=" * 70)
    print("📊 LOAD TEST REPORT")
    print("=" * 70)
    print()

    # Summary
    print("🎯 SUMMARY")
    print("-" * 70)
    print(f"  Total Requests:       {analysis['total_requests']}")
    print(f"  Successful:           {analysis['successful_requests']} ✅")
    print(f"  Failed:               {analysis['failed_requests']} ❌")
    print(
        f"  Success Rate:         {analysis['success_rate']:.2f}%"
    )
    print()

    # Performance
    print("⚡ PERFORMANCE")
    print("-" * 70)
    print(f"  Total Time:           {analysis['total_time_seconds']:.2f} seconds")
    print(f"  Throughput:           {analysis['requests_per_second']:.2f} req/sec")
    print()

    # Latency statistics
    print("⏱️  LATENCY STATISTICS (milliseconds)")
    print("-" * 70)
    print(f"  Minimum:              {analysis['latency_min_ms']:.2f} ms")
    print(f"  Maximum:              {analysis['latency_max_ms']:.2f} ms")
    print(f"  Mean:                 {analysis['latency_mean_ms']:.2f} ms")
    print(f"  Median (p50):         {analysis['latency_median_ms']:.2f} ms")
    print(f"  Std Deviation:        {analysis['latency_stddev_ms']:.2f} ms")
    print()
    print(f"  p50 (median):         {analysis['latency_p50_ms']:.2f} ms")
    print(f"  p95:                  {analysis['latency_p95_ms']:.2f} ms ⭐")
    print(f"  p99:                  {analysis['latency_p99_ms']:.2f} ms ⭐")
    print()

    # Performance assessment
    p95 = analysis["latency_p95_ms"]
    if p95 < 50:
        assessment = "🚀 EXCELLENT (< 50ms)"
    elif p95 < 100:
        assessment = "✅ GOOD (< 100ms)"
    elif p95 < 200:
        assessment = "⚠️  ACCEPTABLE (< 200ms)"
    else:
        assessment = "❌ NEEDS IMPROVEMENT (> 200ms)"

    print(f"  Assessment:           {assessment}")
    print()

    # Error breakdown
    if analysis["error_breakdown"]:
        print("❌ ERROR BREAKDOWN")
        print("-" * 70)
        for error, count in sorted(
            analysis["error_breakdown"].items(), key=lambda x: x[1], reverse=True
        ):
            print(f"  {error:30s} {count:4d} occurrences")
        print()

    # SLA compliance
    print("📋 SLA COMPLIANCE")
    print("-" * 70)
    sla_target = 100  # 100ms target
    p95_compliant = analysis["latency_p95_ms"] <= sla_target
    success_compliant = analysis["success_rate"] >= 99.0

    print(f"  p95 < {sla_target}ms:           {'✅ PASS' if p95_compliant else '❌ FAIL'} ({analysis['latency_p95_ms']:.2f}ms)")
    print(f"  Success Rate > 99%:   {'✅ PASS' if success_compliant else '❌ FAIL'} ({analysis['success_rate']:.2f}%)")
    print()

    print("=" * 70)


def save_report_json(analysis: Dict, filename: str = "load_test_report.json"):
    """Save report as JSON file."""
    with open(filename, "w") as f:
        json.dump(analysis, f, indent=2)
    print(f"💾 Report saved to: {filename}")


def save_report_markdown(
    analysis: Dict, num_requests: int, num_workers: int, filename: str = "LOAD_TEST_REPORT.md"
):
    """Save report as Markdown file."""
    with open(filename, "w") as f:
        f.write("# Load Test Report - Crypto Volatility API\n\n")
        f.write(f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Target:** {API_BASE_URL}\n")
        f.write(f"**Configuration:** {num_requests} requests, {num_workers} workers\n\n")

        f.write("## Summary\n\n")
        f.write(f"- **Total Requests:** {analysis['total_requests']}\n")
        f.write(f"- **Successful:** {analysis['successful_requests']} ✅\n")
        f.write(f"- **Failed:** {analysis['failed_requests']}\n")
        f.write(f"- **Success Rate:** {analysis['success_rate']:.2f}%\n\n")

        f.write("## Performance\n\n")
        f.write(f"- **Total Time:** {analysis['total_time_seconds']:.2f} seconds\n")
        f.write(f"- **Throughput:** {analysis['requests_per_second']:.2f} req/sec\n\n")

        f.write("## Latency Statistics\n\n")
        f.write("| Metric | Value (ms) |\n")
        f.write("|--------|------------|\n")
        f.write(f"| Minimum | {analysis['latency_min_ms']:.2f} |\n")
        f.write(f"| Maximum | {analysis['latency_max_ms']:.2f} |\n")
        f.write(f"| Mean | {analysis['latency_mean_ms']:.2f} |\n")
        f.write(f"| Median (p50) | {analysis['latency_median_ms']:.2f} |\n")
        f.write(f"| **p95** | **{analysis['latency_p95_ms']:.2f}** |\n")
        f.write(f"| **p99** | **{analysis['latency_p99_ms']:.2f}** |\n")
        f.write(f"| Std Dev | {analysis['latency_stddev_ms']:.2f} |\n\n")

        # SLA Compliance
        p95_compliant = analysis["latency_p95_ms"] <= 100
        success_compliant = analysis["success_rate"] >= 99.0

        f.write("## SLA Compliance\n\n")
        f.write(f"- p95 < 100ms: {'✅ PASS' if p95_compliant else '❌ FAIL'} ({analysis['latency_p95_ms']:.2f}ms)\n")
        f.write(f"- Success Rate > 99%: {'✅ PASS' if success_compliant else '❌ FAIL'} ({analysis['success_rate']:.2f}%)\n\n")

        # Errors
        if analysis["error_breakdown"]:
            f.write("## Error Breakdown\n\n")
            for error, count in sorted(
                analysis["error_breakdown"].items(), key=lambda x: x[1], reverse=True
            ):
                f.write(f"- {error}: {count} occurrences\n")
            f.write("\n")

    print(f"📄 Markdown report saved to: {filename}")


# ============================================================================
# MAIN EXECUTION
# ============================================================================


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Load test the Crypto Volatility API")
    parser.add_argument(
        "--requests",
        type=int,
        default=DEFAULT_NUM_REQUESTS,
        help=f"Number of requests to send (default: {DEFAULT_NUM_REQUESTS})",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help=f"Number of concurrent workers (default: {DEFAULT_WORKERS})",
    )
    parser.add_argument(
        "--url",
        type=str,
        default=API_BASE_URL,
        help=f"API base URL (default: {API_BASE_URL})",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="LOAD_TEST_REPORT",
        help="Output filename prefix (default: LOAD_TEST_REPORT)",
    )

    args = parser.parse_args()

    # Check if API is reachable
    api_url = args.url
    print("🔍 Checking API availability...")
    try:
        response = requests.get(f"{api_url}/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ API is reachable at {api_url}\n")
        else:
            print(f"⚠️  API returned status {response.status_code}\n")
    except Exception as e:
        print(f"❌ Cannot reach API: {e}")
        print("Make sure the API is running: docker compose up -d\n")
        return

    # Run load test
    start_time = time.time()
    results = run_load_test(args.requests, args.workers)
    total_time = time.time() - start_time

    # Analyze results
    analysis = analyze_results(results, total_time)

    # Print report
    print_report(analysis)

    # Save reports
    save_report_json(analysis, f"{args.output}.json")
    save_report_markdown(
        analysis, args.requests, args.workers, f"{args.output}.md"
    )

    print()
    print("✅ Load test complete!")


if __name__ == "__main__":
    main()
