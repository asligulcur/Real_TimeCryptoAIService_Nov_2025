#!/usr/bin/env python3
"""
Data drift detection using Evidently AI.

This script:
1. Loads reference data (training/baseline)
2. Loads current production data (from Kafka or database)
3. Generates drift detection report
4. Saves HTML report and summary
5. Alerts if significant drift detected

Author: Asli Gulcur
Date: November 2025
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Tuple

import pandas as pd
from evidently.pipeline.column_mapping import ColumnMapping
from evidently.metric_preset import DataDriftPreset, DataQualityPreset
from evidently.report import Report


# ============================================================================
# Configuration
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports" / "drift"
DATA_DIR = PROJECT_ROOT / "data"

# Feature columns (matching training data)
FEATURE_COLUMNS = [
    "price",
    "bid",
    "ask",
    "spread",
    "volatility_30s",
    "volatility_60s",
    "volatility_120s",
    "return_10s",
    "return_30s",
    "return_60s",
    "intensity_30s",
    "intensity_60s",
    "intensity_120s",
]

TARGET_COLUMN = "target"

# Drift detection thresholds
DRIFT_THRESHOLD = 0.5  # Drift score threshold (0-1)
WARNING_FEATURES_COUNT = 3  # Number of drifted features to trigger warning


# ============================================================================
# Data Loading Functions
# ============================================================================


def load_reference_data() -> pd.DataFrame:
    """
    Load reference dataset (training data baseline).
    
    Returns:
        DataFrame with reference/baseline data
    """
    # Try multiple possible locations
    possible_paths = [
        DATA_DIR / "processed" / "train.parquet",
        DATA_DIR / "processed" / "train.csv",
        DATA_DIR / "train.parquet",
        DATA_DIR / "train.csv",
    ]
    
    for path in possible_paths:
        if path.exists():
            print(f"📂 Loading reference data from: {path}")
            if path.suffix == ".parquet":
                df = pd.read_parquet(path)
            else:
                df = pd.read_csv(path)
            
            # Take a sample for faster processing (last 10,000 rows)
            if len(df) > 10000:
                df = df.tail(10000).copy()
                print(f"   Sampled to 10,000 rows for efficiency")
            
            print(f"   Reference data shape: {df.shape}")
            return df
    
    # If no training data found, create synthetic reference data
    print("⚠️  No training data found. Creating synthetic reference data...")
    return create_synthetic_reference_data()


def create_synthetic_reference_data(n_samples: int = 1000) -> pd.DataFrame:
    """
    Create synthetic reference data for demonstration.
    
    Args:
        n_samples: Number of samples to generate
    
    Returns:
        DataFrame with synthetic baseline data
    """
    import numpy as np
    
    np.random.seed(42)
    
    data = {
        "price": np.random.normal(88000, 2000, n_samples),
        "bid": np.random.normal(87995, 2000, n_samples),
        "ask": np.random.normal(88005, 2000, n_samples),
        "spread": np.random.uniform(0.5, 3.0, n_samples),
        "volatility_30s": np.random.exponential(0.015, n_samples),
        "volatility_60s": np.random.exponential(0.020, n_samples),
        "volatility_120s": np.random.exponential(0.025, n_samples),
        "return_10s": np.random.normal(0, 0.001, n_samples),
        "return_30s": np.random.normal(0, 0.003, n_samples),
        "return_60s": np.random.normal(0, 0.005, n_samples),
        "intensity_30s": np.random.uniform(5, 30, n_samples),
        "intensity_60s": np.random.uniform(10, 50, n_samples),
        "intensity_120s": np.random.uniform(20, 80, n_samples),
        "target": np.random.choice([0, 1], n_samples, p=[0.8, 0.2]),
    }
    
    df = pd.DataFrame(data)
    print(f"   Synthetic reference data shape: {df.shape}")
    return df


def load_production_data(days: int = 1) -> pd.DataFrame:
    """
    Load recent production data for drift comparison.
    
    Args:
        days: Number of recent days to load
    
    Returns:
        DataFrame with recent production data
    """
    # Try to load from processed production data
    possible_paths = [
        DATA_DIR / "production" / "recent.parquet",
        DATA_DIR / "production" / "recent.csv",
        DATA_DIR / "processed" / "test.parquet",
        DATA_DIR / "processed" / "test.csv",
    ]
    
    for path in possible_paths:
        if path.exists():
            print(f"📂 Loading production data from: {path}")
            if path.suffix == ".parquet":
                df = pd.read_parquet(path)
            else:
                df = pd.read_csv(path)
            
            # Take recent sample
            if len(df) > 5000:
                df = df.tail(5000).copy()
                print(f"   Sampled to 5,000 most recent rows")
            
            print(f"   Production data shape: {df.shape}")
            return df
    
    # If no production data found, create synthetic current data with drift
    print("⚠️  No production data found. Creating synthetic current data with drift...")
    return create_synthetic_current_data()


def create_synthetic_current_data(n_samples: int = 1000) -> pd.DataFrame:
    """
    Create synthetic current data with intentional drift for demonstration.
    
    Args:
        n_samples: Number of samples to generate
    
    Returns:
        DataFrame with synthetic current data (with drift)
    """
    import numpy as np
    
    np.random.seed(123)  # Different seed for drift
    
    # Introduce drift: higher prices, higher volatility, different intensity
    data = {
        "price": np.random.normal(92000, 2500, n_samples),  # Price increased
        "bid": np.random.normal(91995, 2500, n_samples),
        "ask": np.random.normal(92005, 2500, n_samples),
        "spread": np.random.uniform(0.8, 4.0, n_samples),  # Wider spreads
        "volatility_30s": np.random.exponential(0.025, n_samples),  # Higher volatility
        "volatility_60s": np.random.exponential(0.030, n_samples),
        "volatility_120s": np.random.exponential(0.035, n_samples),
        "return_10s": np.random.normal(0, 0.0015, n_samples),
        "return_30s": np.random.normal(0, 0.004, n_samples),
        "return_60s": np.random.normal(0, 0.006, n_samples),
        "intensity_30s": np.random.uniform(10, 40, n_samples),  # Higher intensity
        "intensity_60s": np.random.uniform(20, 60, n_samples),
        "intensity_120s": np.random.uniform(30, 100, n_samples),
        "target": np.random.choice([0, 1], n_samples, p=[0.75, 0.25]),  # More spikes
    }
    
    df = pd.DataFrame(data)
    print(f"   Synthetic current data shape: {df.shape}")
    return df


# ============================================================================
# Drift Detection
# ============================================================================


def generate_drift_report(
    reference_data: pd.DataFrame,
    current_data: pd.DataFrame,
    output_path: Path,
) -> Report:
    """
    Generate Evidently drift detection report.
    
    Args:
        reference_data: Baseline/training data
        current_data: Recent production data
        output_path: Path to save HTML report
    
    Returns:
        Evidently Report object
    """
    print("\n🔍 Generating drift detection report...")
    
    # Configure column mapping
    column_mapping = ColumnMapping(
        target=TARGET_COLUMN if TARGET_COLUMN in reference_data.columns else None,
        numerical_features=FEATURE_COLUMNS,
        categorical_features=[],
    )
    
    # Create report with drift and data quality presets
    report = Report(metrics=[
        DataDriftPreset(),
        DataQualityPreset(),
    ])
    
    # Run the report
    print("   Analyzing data drift...")
    report.run(
        reference_data=reference_data,
        current_data=current_data,
        column_mapping=column_mapping,
    )
    
    # Save HTML report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report.save_html(str(output_path))
    print(f"✅ Report saved to: {output_path}")
    
    return report


def extract_drift_metrics(report: Report) -> Dict:
    """
    Extract key drift metrics from Evidently report.
    
    Args:
        report: Evidently Report object
    
    Returns:
        Dictionary with drift metrics
    """
    # Get report as dict
    report_dict = report.as_dict()
    
    # Extract drift metrics
    metrics = {
        "timestamp": datetime.now().isoformat(),
        "dataset_drift_detected": False,
        "number_of_drifted_features": 0,
        "share_of_drifted_features": 0.0,
        "drifted_features": [],
        "drift_by_feature": {},
    }
    
    # Parse metrics from report
    for metric in report_dict.get("metrics", []):
        metric_type = metric.get("metric")
        
        # Dataset-level drift
        if metric_type == "DatasetDriftMetric":
            result = metric.get("result", {})
            metrics["dataset_drift_detected"] = result.get("dataset_drift", False)
            metrics["number_of_drifted_features"] = result.get("number_of_drifted_columns", 0)
            metrics["share_of_drifted_features"] = result.get("share_of_drifted_columns", 0.0)
            
            # Extract drifted feature names
            drift_by_columns = result.get("drift_by_columns", {})
            for col, drift_info in drift_by_columns.items():
                if isinstance(drift_info, dict) and drift_info.get("drift_detected", False):
                    metrics["drifted_features"].append(col)
                    metrics["drift_by_feature"][col] = {
                        "drift_score": drift_info.get("drift_score", 0),
                        "stattest_name": drift_info.get("stattest_name", "unknown"),
                    }
    
    return metrics


# ============================================================================
# Alerting and Summary
# ============================================================================


def analyze_drift_severity(metrics: Dict) -> Tuple[str, str]:
    """
    Analyze drift severity and generate alert level.
    
    Args:
        metrics: Drift metrics dictionary
    
    Returns:
        Tuple of (severity_level, message)
    """
    n_drifted = metrics["number_of_drifted_features"]
    drift_detected = metrics["dataset_drift_detected"]
    
    if not drift_detected:
        return "INFO", "No significant drift detected. Model performance expected to be stable."
    
    if n_drifted >= 5:
        return "CRITICAL", f"Severe drift detected in {n_drifted} features! Immediate model retraining recommended."
    elif n_drifted >= WARNING_FEATURES_COUNT:
        return "WARNING", f"Moderate drift detected in {n_drifted} features. Monitor model performance closely."
    else:
        return "INFO", f"Minor drift detected in {n_drifted} feature(s). Continue monitoring."


def create_drift_summary(metrics: Dict, output_path: Path) -> None:
    """
    Create human-readable drift summary document.
    
    Args:
        metrics: Drift metrics dictionary
        output_path: Path to save summary markdown
    """
    severity, message = analyze_drift_severity(metrics)
    
    # Emoji indicators
    severity_emoji = {
        "INFO": "✅",
        "WARNING": "⚠️",
        "CRITICAL": "🚨",
    }
    
    emoji = severity_emoji.get(severity, "ℹ️")
    
    summary = f"""# Data Drift Detection Summary

**Report Generated:** {metrics['timestamp']}  
**Severity Level:** {emoji} **{severity}**

---

## Executive Summary

{message}

---

## Drift Detection Results

### Dataset-Level Drift
- **Dataset Drift Detected:** {'Yes 🚨' if metrics['dataset_drift_detected'] else 'No ✅'}
- **Number of Drifted Features:** {metrics['number_of_drifted_features']} out of {len(FEATURE_COLUMNS)}
- **Share of Drifted Features:** {metrics['share_of_drifted_features']:.1%}

### Drifted Features

"""
    
    if metrics["drifted_features"]:
        summary += "The following features show significant drift:\n\n"
        for feature in metrics["drifted_features"]:
            drift_info = metrics["drift_by_feature"].get(feature, {})
            drift_score = drift_info.get("drift_score", 0)
            stattest = drift_info.get("stattest_name", "unknown")
            summary += f"- **{feature}**\n"
            summary += f"  - Drift Score: {drift_score:.4f}\n"
            summary += f"  - Statistical Test: {stattest}\n"
            summary += "\n"
    else:
        summary += "✅ No features showing significant drift.\n\n"
    
    summary += """
---

## Recommended Actions

"""
    
    if severity == "CRITICAL":
        summary += """
### Immediate Actions Required

1. **Trigger Model Retraining** 🔄
   - Retrain model on recent production data
   - Update feature engineering pipeline if needed
   - Validate new model on holdout set

2. **Review Feature Engineering** 🔧
   - Check if feature definitions have changed
   - Verify data collection pipeline integrity
   - Investigate root causes of drift

3. **Consider Model Rollback** ⏪
   - If retraining not immediately possible
   - Monitor performance metrics closely
   - Set up automated alerts for accuracy degradation

4. **Update Monitoring** 📊
   - Increase drift check frequency (daily → hourly)
   - Add more granular feature-level alerts
   - Track prediction confidence distribution
"""
    
    elif severity == "WARNING":
        summary += """
### Recommended Actions

1. **Monitor Model Performance** 📊
   - Track accuracy, precision, recall daily
   - Compare to SLO targets (F1 ≥ 0.75)
   - Set up alerts for performance degradation

2. **Plan Model Retraining** 📅
   - Schedule retraining within 1-2 weeks
   - Collect sufficient recent production data
   - Prepare validation strategy

3. **Investigate Drift Causes** 🔍
   - Review market conditions (volatility events?)
   - Check for upstream data issues
   - Validate feature calculation logic

4. **Document Findings** 📝
   - Record drift patterns and timing
   - Track correlation with business events
   - Update drift baseline if intentional changes
"""
    
    else:
        summary += """
### Ongoing Monitoring

1. **Continue Regular Checks** ✅
   - Run drift detection weekly
   - Monitor for emerging drift patterns
   - Keep reference data updated

2. **Track Trends** 📈
   - Log drift scores over time
   - Identify seasonal patterns
   - Establish normal drift ranges

3. **Maintain Documentation** 📋
   - Keep drift reports archived
   - Document any data pipeline changes
   - Update baseline when model retrained
"""
    
    summary += """
---

## Technical Details

### Feature Columns Monitored
"""
    for feature in FEATURE_COLUMNS:
        drift_status = "⚠️ DRIFTED" if feature in metrics["drifted_features"] else "✅ Stable"
        summary += f"- `{feature}` - {drift_status}\n"
    
    summary += f"""

### Drift Detection Configuration
- **Drift Threshold:** {DRIFT_THRESHOLD}
- **Warning Threshold:** {WARNING_FEATURES_COUNT} drifted features
- **Reference Data:** Training/baseline dataset
- **Current Data:** Recent production data (last 1-7 days)
- **Statistical Tests:** Kolmogorov-Smirnov, Chi-Square, etc. (auto-selected by Evidently)

---

## Related Reports

- **Full HTML Report:** `{REPORTS_DIR / 'drift_report.html'}`
- **Raw Metrics JSON:** `{REPORTS_DIR / 'drift_metrics.json'}`
- **SLO Document:** `docs/slo.md`
- **Runbook:** `docs/runbook.md`

---

## Next Steps

1. Review the full HTML drift report for detailed visualizations
2. Check model performance metrics in Grafana dashboard
3. Follow recommended actions based on severity level
4. Update this summary after taking action

---

**Report Status:** {severity}  
**Action Required:** {'Yes - See Recommended Actions' if severity in ['WARNING', 'CRITICAL'] else 'No - Continue monitoring'}
"""
    
    # Save summary
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(summary)
    print(f"✅ Drift summary saved to: {output_path}")


# ============================================================================
# Main Execution
# ============================================================================


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Generate data drift detection report using Evidently"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="Number of recent days of production data to analyze (default: 1)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPORTS_DIR,
        help="Output directory for reports",
    )
    
    args = parser.parse_args()
    
    print("="*70)
    print("🔍 EVIDENTLY DATA DRIFT DETECTION")
    print("="*70)
    print(f"Configuration:")
    print(f"  - Production data window: Last {args.days} day(s)")
    print(f"  - Output directory: {args.output_dir}")
    print(f"  - Drift threshold: {DRIFT_THRESHOLD}")
    print("="*70)
    
    try:
        # Load data
        print("\n📦 Loading data...")
        reference_data = load_reference_data()
        current_data = load_production_data(days=args.days)
        
        # Ensure same columns
        common_cols = [col for col in FEATURE_COLUMNS if col in reference_data.columns and col in current_data.columns]
        if TARGET_COLUMN in reference_data.columns and TARGET_COLUMN in current_data.columns:
            common_cols.append(TARGET_COLUMN)
        
        reference_data = reference_data[common_cols]
        current_data = current_data[common_cols]
        
        print(f"   Using {len(common_cols)} columns for drift detection")
        
        # Generate report
        report_path = args.output_dir / f"drift_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        report = generate_drift_report(reference_data, current_data, report_path)
        
        # Extract metrics
        print("\n📊 Extracting drift metrics...")
        metrics = extract_drift_metrics(report)
        
        # Save metrics as JSON
        metrics_path = args.output_dir / "drift_metrics.json"
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        metrics_path.write_text(json.dumps(metrics, indent=2))
        print(f"✅ Metrics saved to: {metrics_path}")
        
        # Create summary
        summary_path = PROJECT_ROOT / "docs" / "drift_summary.md"
        create_drift_summary(metrics, summary_path)
        
        # Print results
        severity, message = analyze_drift_severity(metrics)
        print("\n" + "="*70)
        print(f"📊 DRIFT DETECTION RESULTS: {severity}")
        print("="*70)
        print(f"Dataset Drift: {'Yes' if metrics['dataset_drift_detected'] else 'No'}")
        print(f"Drifted Features: {metrics['number_of_drifted_features']}/{len(FEATURE_COLUMNS)}")
        print(f"Message: {message}")
        print("="*70)
        print(f"\n📄 View full report: {report_path}")
        print(f"📝 View summary: {summary_path}")
        print()
        
        # Exit with appropriate code
        if severity == "CRITICAL":
            sys.exit(2)
        elif severity == "WARNING":
            sys.exit(1)
        else:
            sys.exit(0)
    
    except Exception as e:
        print(f"\n❌ Error during drift detection: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
