#!/usr/bin/env python3
"""Generate fresh Evidently drift report - November 26, 2025"""

print("\n" + "="*60)
print("GENERATING FRESH EVIDENTLY DRIFT REPORT")
print("="*60 + "\n")

# Step 1: Imports
print("Step 1/5: Loading libraries...")
try:
    import pandas as pd
    import numpy as np
    from datetime import datetime
    from pathlib import Path
    from evidently.report import Report
    from evidently.metric_preset import DataDriftPreset
    print("✅ All libraries loaded\n")
except ImportError as e:
    print(f"❌ Missing library: {e}")
    print("Installing evidently...")
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "evidently"])
    from evidently.report import Report
    from evidently.metric_preset import DataDriftPreset
    print("✅ Evidently installed and loaded\n")

# Step 2: Create data
print("Step 2/5: Creating synthetic data...")
np.random.seed(42)

# Reference (training baseline) - Normal market
ref_data = pd.DataFrame({
    'price': np.random.normal(88000, 2000, 1000),
    'volatility': np.random.exponential(0.015, 1000),
    'volume': np.random.uniform(100, 1000, 1000),
})
print(f"✅ Reference data: {ref_data.shape}")
print(f"   Price mean: ${ref_data['price'].mean():.0f}")

# Current (production) - Market with drift
curr_data = pd.DataFrame({
    'price': np.random.normal(92000, 2500, 1000),  # DRIFT: +4.5%
    'volatility': np.random.exponential(0.025, 1000),  # DRIFT: +67%
    'volume': np.random.uniform(150, 1200, 1000),  # DRIFT: higher
})
print(f"✅ Current data: {curr_data.shape}")
print(f"   Price mean: ${curr_data['price'].mean():.0f}")
print(f"   Expected drift: {((curr_data['price'].mean()/ref_data['price'].mean()-1)*100):.1f}%\n")

# Step 3: Generate report
print("Step 3/5: Running Evidently analysis...")
print("   (This takes 10-20 seconds)...")

report = Report(metrics=[DataDriftPreset()])
report.run(reference_data=ref_data, current_data=curr_data)
print("✅ Analysis complete\n")

# Step 4: Save report
print("Step 4/5: Saving report...")
PROJECT_ROOT = Path(__file__).parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports" / "drift"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
html_path = REPORTS_DIR / f"evidently_drift_{timestamp}.html"

report.save_html(str(html_path))
size_kb = html_path.stat().st_size / 1024
print(f"✅ HTML report saved: {html_path.name}")
print(f"   Size: {size_kb:.1f} KB\n")

# Step 5: Extract results
print("Step 5/5: Extracting results...")
results = report.as_dict()
drift_found = False
num_drifted = 0

for metric in results.get("metrics", []):
    if metric.get("metric") == "DatasetDriftMetric":
        result = metric.get("result", {})
        drift_found = result.get("dataset_drift", False)
        num_drifted = result.get("number_of_drifted_columns", 0)

print(f"✅ Drift detected: {'YES' if drift_found else 'NO'}")
print(f"✅ Drifted columns: {num_drifted}/3\n")

# Summary
print("="*60)
print("✅ REPORT GENERATION COMPLETE")
print("="*60)
print(f"\n📄 View report:")
print(f"   open {html_path}\n")
print(f"Or manually open:")
print(f"   {html_path}\n")
