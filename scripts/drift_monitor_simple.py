#!/usr/bin/env python3
"""
Simple drift detection using Evidently AI - Compatible with latest Evidently API.

This script generates a drift report comparing reference and current data.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# Import Evidently components
try:
    from evidently.report import Report
    from evidently.metric_preset import DataDriftPreset, DataQualityPreset
    print("✅ Evidently imported successfully")
except ImportError as e:
    print(f"❌ Error importing Evidently: {e}")
    print("Installing evidently...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "evidently"])
    from evidently.report import Report
    from evidently.metric_preset import DataDriftPreset, DataQualityPreset

PROJECT_ROOT = Path(__file__).parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports" / "drift"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

print("="*70)
print("🔍 EVIDENTLY DATA DRIFT DETECTION")
print("="*70)

# Create synthetic reference data (training baseline)
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

print(f"   Reference data shape: {reference_data.shape}")
print(f"   Price mean: ${reference_data['price'].mean():.2f}")
print(f"   Target distribution: {reference_data['target'].value_counts().to_dict()}")

# Create synthetic current data with drift
print("\n📦 Creating current data (with intentional drift)...")
np.random.seed(123)
n_curr = 1000

current_data = pd.DataFrame({
    "price": np.random.normal(92000, 2500, n_curr),  # DRIFT: Higher prices
    "bid": np.random.normal(91995, 2500, n_curr),
    "ask": np.random.normal(92005, 2500, n_curr),
    "spread": np.random.uniform(0.8, 4.0, n_curr),  # DRIFT: Wider spreads
    "volatility_30s": np.random.exponential(0.025, n_curr),  # DRIFT: Higher volatility
    "volatility_60s": np.random.exponential(0.030, n_curr),
    "volatility_120s": np.random.exponential(0.035, n_curr),
    "return_10s": np.random.normal(0, 0.0015, n_curr),
    "return_30s": np.random.normal(0, 0.004, n_curr),
    "return_60s": np.random.normal(0, 0.006, n_curr),
    "intensity_30s": np.random.uniform(10, 40, n_curr),  # DRIFT: Higher intensity
    "intensity_60s": np.random.uniform(20, 60, n_curr),
    "intensity_120s": np.random.uniform(30, 100, n_curr),
    "target": np.random.choice([0, 1], n_curr, p=[0.75, 0.25]),  # DRIFT: More spikes
})

print(f"   Current data shape: {current_data.shape}")
print(f"   Price mean: ${current_data['price'].mean():.2f}")
print(f"   Target distribution: {current_data['target'].value_counts().to_dict()}")

print("\n🔍 Expected drift in features:")
print(f"   - price: ${reference_data['price'].mean():.0f} → ${current_data['price'].mean():.0f} ({((current_data['price'].mean()/reference_data['price'].mean()-1)*100):.1f}%)")
print(f"   - volatility_30s: {reference_data['volatility_30s'].mean():.4f} → {current_data['volatility_30s'].mean():.4f}")
print(f"   - intensity_30s: {reference_data['intensity_30s'].mean():.1f} → {current_data['intensity_30s'].mean():.1f}")

# Generate drift report
print("\n🔍 Generating Evidently drift report...")
report = Report(metrics=[
    DataDriftPreset(),
    DataQualityPreset(),
])

print("   Running drift analysis...")
report.run(reference_data=reference_data, current_data=current_data)

# Save HTML report
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
html_path = REPORTS_DIR / f"drift_report_{timestamp}.html"
report.save_html(str(html_path))
print(f"✅ HTML report saved: {html_path}")

# Extract metrics
print("\n📊 Extracting drift metrics...")
report_dict = report.as_dict()

# Save full report as JSON
json_path = REPORTS_DIR / "drift_metrics.json"
with open(json_path, 'w') as f:
    json.dump(report_dict, f, indent=2, default=str)
print(f"✅ JSON metrics saved: {json_path}")

# Parse key metrics
drift_summary = {
    "timestamp": datetime.now().isoformat(),
    "dataset_drift_detected": False,
    "number_of_drifted_features": 0,
    "drifted_features": [],
}

for metric in report_dict.get("metrics", []):
    if metric.get("metric") == "DatasetDriftMetric":
        result = metric.get("result", {})
        drift_summary["dataset_drift_detected"] = result.get("dataset_drift", False)
        drift_summary["number_of_drifted_features"] = result.get("number_of_drifted_columns", 0)
        drift_summary["share_of_drifted_features"] = result.get("share_of_drifted_columns", 0.0)
        
        # Get drifted feature names
        drift_by_columns = result.get("drift_by_columns", {})
        for col, drift_info in drift_by_columns.items():
            if isinstance(drift_info, dict) and drift_info.get("drift_detected", False):
                drift_summary["drifted_features"].append(col)

print(f"\n{'='*70}")
print("📊 DRIFT DETECTION RESULTS")
print(f"{'='*70}")
print(f"Dataset Drift Detected: {'🚨 YES' if drift_summary['dataset_drift_detected'] else '✅ NO'}")
print(f"Number of Drifted Features: {drift_summary['number_of_drifted_features']}/13")
print(f"Drifted Features: {', '.join(drift_summary['drifted_features']) if drift_summary['drifted_features'] else 'None'}")
print(f"{'='*70}")

# Create summary document
summary_path = PROJECT_ROOT / "docs" / "drift_summary.md"
summary_content = f"""# Data Drift Detection Summary

**Report Generated:** {drift_summary['timestamp']}  
**Severity Level:** {'🚨 **CRITICAL**' if drift_summary['number_of_drifted_features'] >= 5 else '⚠️ **WARNING**' if drift_summary['number_of_drifted_features'] >= 3 else '✅ **INFO**'}

---

## Executive Summary

{'Significant drift detected! Model retraining recommended.' if drift_summary['dataset_drift_detected'] else 'No significant drift detected. Model performance expected to be stable.'}

---

## Drift Detection Results

### Dataset-Level Drift
- **Dataset Drift Detected:** {'Yes 🚨' if drift_summary['dataset_drift_detected'] else 'No ✅'}
- **Number of Drifted Features:** {drift_summary['number_of_drifted_features']} out of 13
- **Share of Drifted Features:** {drift_summary.get('share_of_drifted_features', 0):.1%}

### Drifted Features

"""

if drift_summary["drifted_features"]:
    summary_content += "The following features show significant drift:\n\n"
    for feature in drift_summary["drifted_features"]:
        summary_content += f"- **{feature}**\n"
else:
    summary_content += "✅ No features showing significant drift.\n"

summary_content += f"""

---

## Recommended Actions

"""

if drift_summary['number_of_drifted_features'] >= 5:
    summary_content += """
### 🚨 Immediate Actions Required

1. **Trigger Model Retraining** - Retrain model on recent production data
2. **Review Feature Engineering** - Check if feature definitions have changed
3. **Consider Model Rollback** - If retraining not immediately possible
4. **Update Monitoring** - Increase drift check frequency

"""
elif drift_summary['number_of_drifted_features'] >= 3:
    summary_content += """
### ⚠️ Recommended Actions

1. **Monitor Model Performance** - Track accuracy, precision, recall daily
2. **Plan Model Retraining** - Schedule retraining within 1-2 weeks
3. **Investigate Drift Causes** - Review market conditions and data pipeline
4. **Document Findings** - Record drift patterns and timing

"""
else:
    summary_content += """
### ✅ Ongoing Monitoring

1. **Continue Regular Checks** - Run drift detection weekly
2. **Track Trends** - Log drift scores over time
3. **Maintain Documentation** - Keep drift reports archived

"""

summary_content += f"""
---

## Feature Statistics Comparison

### Reference Data (Training Baseline)
- **Size:** {len(reference_data)} samples
- **Price Mean:** ${reference_data['price'].mean():.2f} ± ${reference_data['price'].std():.2f}
- **Volatility 30s:** {reference_data['volatility_30s'].mean():.4f} ± {reference_data['volatility_30s'].std():.4f}
- **Target Balance:** {reference_data['target'].value_counts().to_dict()}

### Current Data (Production)
- **Size:** {len(current_data)} samples
- **Price Mean:** ${current_data['price'].mean():.2f} ± ${current_data['price'].std():.2f}
- **Volatility 30s:** {current_data['volatility_30s'].mean():.4f} ± {current_data['volatility_30s'].std():.4f}
- **Target Balance:** {current_data['target'].value_counts().to_dict()}

---

## Related Reports

- **Full HTML Report:** `{html_path.relative_to(PROJECT_ROOT)}`
- **Raw Metrics JSON:** `{json_path.relative_to(PROJECT_ROOT)}`
- **SLO Document:** `docs/slo.md`
- **Grafana Dashboard:** http://localhost:3000

---

## Monitoring Schedule

- **Frequency:** Weekly (automated via cron/scheduler)
- **Alerting:** Slack/Email notification if drift detected
- **Retention:** Keep last 12 reports (3 months)
- **Review:** Monthly drift trend analysis

---

**Report Status:** {'CRITICAL' if drift_summary['number_of_drifted_features'] >= 5 else 'WARNING' if drift_summary['number_of_drifted_features'] >= 3 else 'INFO'}  
**Action Required:** {'Yes - See Recommended Actions' if drift_summary['number_of_drifted_features'] >= 3 else 'No - Continue monitoring'}

---

## Technical Details

### Drift Detection Method
- **Library:** Evidently AI
- **Statistical Tests:** Kolmogorov-Smirnov (numerical), Chi-Square (categorical)
- **Confidence Level:** 95%
- **Drift Threshold:** Auto-calibrated by Evidently

### How to Re-run

```bash
# Run drift detection
python3 scripts/drift_monitor_simple.py

# View HTML report
open {html_path}

# Check JSON metrics
cat {json_path} | jq '.metrics[] | select(.metric == "DatasetDriftMetric")'
```

### Next Steps

1. Review the full HTML drift report for detailed visualizations
2. Check model performance metrics in Grafana dashboard
3. Follow recommended actions based on severity level
4. Schedule next drift detection run in 7 days
"""

summary_path.write_text(summary_content)
print(f"\n✅ Drift summary saved: {summary_path}")

print(f"\n📄 View full HTML report:")
print(f"   open {html_path}")
print(f"\n📝 View summary document:")
print(f"   cat {summary_path}")
print()

# Exit with appropriate code
if drift_summary['number_of_drifted_features'] >= 5:
    print("⚠️  Exit code: 2 (CRITICAL)")
    sys.exit(2)
elif drift_summary['number_of_drifted_features'] >= 3:
    print("⚠️  Exit code: 1 (WARNING)")
    sys.exit(1)
else:
    print("✅ Exit code: 0 (SUCCESS)")
    sys.exit(0)
