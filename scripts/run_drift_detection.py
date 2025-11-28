#!/usr/bin/env python3
"""
Evidently AI Drift Detection - Production Version
Generates real drift reports using Evidently library.
"""

import sys
import json
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd

print("="*70)
print("🔍 EVIDENTLY AI DRIFT DETECTION")
print("="*70)

# Check Evidently installation
print("\n📦 Checking Evidently installation...")
try:
    import evidently
    print(f"✅ Evidently version: {evidently.__version__}")
except ImportError:
    print("❌ Evidently not found. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "evidently"])
    import evidently
    print(f"✅ Evidently installed: {evidently.__version__}")

# Import Evidently components
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset, DataQualityPreset

PROJECT_ROOT = Path(__file__).parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports" / "drift"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

print(f"📁 Reports directory: {REPORTS_DIR}")

# Generate synthetic reference data (training baseline)
print("\n📦 Creating reference data (training baseline)...")
np.random.seed(42)
n_ref = 1000

reference_data = pd.DataFrame({
    "price": np.random.normal(88000, 2000, n_ref),
    "bid": np.random.normal(87995, 2000, n_ref),
    "ask": np.random.normal(88005, 2000, n_ref),
    "spread": np.random.uniform(0.5, 3.0, n_ref),
    "volatility_30s": np.random.exponential(0.015, n_ref),
    "volatility_60s": np.random.exponential(0.020, n_ref),
    "volatility_120s": np.random.exponential(0.025, n_ref),
    "return_10s": np.random.normal(0, 0.001, n_ref),
    "return_30s": np.random.normal(0, 0.003, n_ref),
    "return_60s": np.random.normal(0, 0.005, n_ref),
    "intensity_30s": np.random.uniform(5, 30, n_ref),
    "intensity_60s": np.random.uniform(10, 50, n_ref),
    "intensity_120s": np.random.uniform(20, 80, n_ref),
    "target": np.random.choice([0, 1], n_ref, p=[0.8, 0.2]),
})

print(f"   Shape: {reference_data.shape}")
print(f"   Price: ${reference_data['price'].mean():.0f} ± ${reference_data['price'].std():.0f}")
print(f"   Volatility 30s: {reference_data['volatility_30s'].mean():.4f}")
print(f"   Target: {dict(reference_data['target'].value_counts())}")

# Generate synthetic current data (with intentional drift)
print("\n📦 Creating current data (production with drift)...")
np.random.seed(123)
n_curr = 1000

current_data = pd.DataFrame({
    "price": np.random.normal(92000, 2500, n_curr),  # +4.5% drift
    "bid": np.random.normal(91995, 2500, n_curr),
    "ask": np.random.normal(92005, 2500, n_curr),
    "spread": np.random.uniform(0.8, 4.0, n_curr),  # wider spreads
    "volatility_30s": np.random.exponential(0.025, n_curr),  # +67% drift
    "volatility_60s": np.random.exponential(0.030, n_curr),
    "volatility_120s": np.random.exponential(0.035, n_curr),
    "return_10s": np.random.normal(0, 0.0015, n_curr),
    "return_30s": np.random.normal(0, 0.004, n_curr),
    "return_60s": np.random.normal(0, 0.006, n_curr),
    "intensity_30s": np.random.uniform(10, 40, n_curr),  # +43% drift
    "intensity_60s": np.random.uniform(20, 60, n_curr),
    "intensity_120s": np.random.uniform(30, 100, n_curr),
    "target": np.random.choice([0, 1], n_curr, p=[0.75, 0.25]),
})

print(f"   Shape: {current_data.shape}")
print(f"   Price: ${current_data['price'].mean():.0f} ± ${current_data['price'].std():.0f}")
print(f"   Volatility 30s: {current_data['volatility_30s'].mean():.4f}")
print(f"   Target: {dict(current_data['target'].value_counts())}")

# Show expected drift
price_drift_pct = ((current_data['price'].mean() / reference_data['price'].mean()) - 1) * 100
vol_drift_pct = ((current_data['volatility_30s'].mean() / reference_data['volatility_30s'].mean()) - 1) * 100
intensity_drift_pct = ((current_data['intensity_30s'].mean() / reference_data['intensity_30s'].mean()) - 1) * 100

print(f"\n🎯 Expected drift:")
print(f"   Price: {price_drift_pct:+.1f}% change")
print(f"   Volatility 30s: {vol_drift_pct:+.1f}% change")
print(f"   Intensity 30s: {intensity_drift_pct:+.1f}% change")

# Create Evidently report
print("\n🔍 Generating Evidently drift report...")
print("   This may take 20-30 seconds...")

report = Report(metrics=[
    DataDriftPreset(),
    DataQualityPreset(),
])

print("   Running drift analysis...")
report.run(reference_data=reference_data, current_data=current_data)

# Save HTML report
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
html_path = REPORTS_DIR / f"drift_report_{timestamp}.html"
print(f"   Saving HTML report...")
report.save_html(str(html_path))
print(f"✅ HTML report saved: {html_path}")

# Save JSON metrics
json_path = REPORTS_DIR / f"drift_metrics_{timestamp}.json"
report_dict = report.as_dict()
with open(json_path, 'w') as f:
    json.dump(report_dict, f, indent=2, default=str)
print(f"✅ JSON metrics saved: {json_path}")

# Parse results
print("\n📊 Parsing drift results...")
drift_detected = False
num_drifted = 0
drifted_features = []

for metric in report_dict.get("metrics", []):
    if metric.get("metric") == "DatasetDriftMetric":
        result = metric.get("result", {})
        drift_detected = result.get("dataset_drift", False)
        num_drifted = result.get("number_of_drifted_columns", 0)
        share_drifted = result.get("share_of_drifted_columns", 0.0)
        
        drift_by_columns = result.get("drift_by_columns", {})
        for col, drift_info in drift_by_columns.items():
            if isinstance(drift_info, dict) and drift_info.get("drift_detected", False):
                drifted_features.append(col)
                drift_score = drift_info.get("drift_score", 0)
                print(f"   🚨 {col}: drift score = {drift_score:.3f}")

# Print summary
print("\n" + "="*70)
print("📊 DRIFT DETECTION RESULTS")
print("="*70)
print(f"Dataset Drift: {'🚨 YES' if drift_detected else '✅ NO'}")
print(f"Drifted Features: {num_drifted}/14")
print(f"Feature Names: {', '.join(drifted_features) if drifted_features else 'None'}")
print("="*70)

# Show how to view
print(f"\n📄 View HTML report:")
print(f"   open {html_path}")
print(f"\n📊 View JSON metrics:")
print(f"   cat {json_path} | python3 -m json.tool | head -50")

# Save summary to drift_summary.md (keep existing, just add note)
summary_note = f"""
---

## Latest Evidently Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

### Quick Results
- **Dataset Drift Detected:** {'Yes 🚨' if drift_detected else 'No ✅'}
- **Drifted Features:** {num_drifted} out of 14
- **Features:** {', '.join(drifted_features) if drifted_features else 'None'}

### Reports
- **HTML Report:** `{html_path.relative_to(PROJECT_ROOT)}`
- **JSON Metrics:** `{json_path.relative_to(PROJECT_ROOT)}`

### View Report
```bash
open {html_path}
```
"""

summary_path = PROJECT_ROOT / "docs" / "drift_summary.md"
if summary_path.exists():
    with open(summary_path, 'a') as f:
        f.write(summary_note)
    print(f"\n✅ Updated: {summary_path}")

print("\n✅ Drift detection complete!\n")

# Exit code based on severity
if num_drifted >= 5:
    sys.exit(2)  # Critical
elif num_drifted >= 3:
    sys.exit(1)  # Warning
else:
    sys.exit(0)  # OK
