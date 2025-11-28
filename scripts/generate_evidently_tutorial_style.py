"""
Evidently Drift Detection - Tutorial API Style
Uses Dataset and DataDefinition classes from the Evidently tutorial
"""

print("Step 1/5: Installing and importing libraries...")

# Auto-install evidently if needed
try:
    import evidently
except ImportError:
    print("📦 Installing evidently...")
    import subprocess
    subprocess.check_call(['pip', 'install', 'evidently', '--quiet'])
    print("✅ Evidently installed successfully")

import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

# Import using tutorial style
from evidently import Dataset
from evidently import DataDefinition
from evidently import Report
from evidently.presets import DataDriftPreset

print("✅ Libraries loaded successfully")

print("\nStep 2/5: Creating synthetic reference and current data...")

# Create synthetic reference data (baseline/training period)
np.random.seed(42)
reference_df = pd.DataFrame({
    'price': np.random.normal(88000, 2000, 1000),
    'volatility': np.random.normal(0.02, 0.005, 1000),
    'intensity': np.random.normal(30, 10, 1000),
    'spread': np.random.normal(1.5, 0.5, 1000)
})

# Create synthetic current data (production period with drift)
current_df = pd.DataFrame({
    'price': np.random.normal(92000, 2000, 1000),  # +4.5% drift
    'volatility': np.random.normal(0.025, 0.006, 1000),  # +25% drift
    'intensity': np.random.normal(35, 12, 1000),  # +16% drift
    'spread': np.random.normal(1.8, 0.6, 1000)  # +20% drift
})

print(f"✅ Reference data: {len(reference_df)} samples")
print(f"   - Price mean: ${reference_df['price'].mean():.2f}")
print(f"   - Volatility mean: {reference_df['volatility'].mean():.4f}")
print(f"✅ Current data: {len(current_df)} samples")
print(f"   - Price mean: ${current_df['price'].mean():.2f}")
print(f"   - Volatility mean: {current_df['volatility'].mean():.4f}")

print("\nStep 3/5: Defining data schema and creating Dataset objects...")

# Define schema using tutorial style
schema = DataDefinition(
    numerical_columns=['price', 'volatility', 'intensity', 'spread']
)

# Create Dataset objects using tutorial style
reference_dataset = Dataset.from_pandas(
    pd.DataFrame(reference_df),
    data_definition=schema
)

current_dataset = Dataset.from_pandas(
    pd.DataFrame(current_df),
    data_definition=schema
)

print("✅ Dataset objects created with schema definition")

print("\nStep 4/5: Running Evidently drift analysis...")

# Create report using tutorial style
report = Report([
    DataDriftPreset()
])

# Run analysis
my_eval = report.run(reference_dataset, current_dataset)

print("✅ Evidently analysis complete")

print("\nStep 5/5: Saving HTML report...")

# Create reports directory if needed
reports_dir = Path("reports/drift")
reports_dir.mkdir(parents=True, exist_ok=True)

# Save HTML report
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
html_path = reports_dir / f"evidently_drift_{timestamp}.html"

# Use save() method instead of save_html()
my_eval.save_html(str(html_path))

print(f"✅ HTML report saved: {html_path.name}")
print(f"\n📊 Full path: {html_path.absolute()}")

# Try to extract drift summary
try:
    report_dict = report.as_dict()
    metrics = report_dict.get('metrics', [])
    
    print("\n" + "="*60)
    print("📈 DRIFT DETECTION SUMMARY")
    print("="*60)
    
    # Find dataset drift metric
    for metric in metrics:
        if metric.get('metric') == 'DatasetDriftMetric':
            result = metric.get('result', {})
            drift_share = result.get('drift_share', 0)
            n_drifted = result.get('number_of_drifted_columns', 0)
            n_total = result.get('number_of_columns', 0)
            
            print(f"\n🎯 Dataset Drift Detected: {drift_share:.1%}")
            print(f"   - Drifted Features: {n_drifted}/{n_total}")
            
            # Show drifted columns
            drift_by_col = result.get('drift_by_columns', {})
            if drift_by_col:
                print(f"\n📋 Feature-Level Drift:")
                for col, info in drift_by_col.items():
                    if isinstance(info, dict):
                        drifted = info.get('drift_detected', False)
                        score = info.get('drift_score', 0)
                        status = "🔴 DRIFT" if drifted else "✅ OK"
                        print(f"   {status} {col}: score={score:.3f}")
    
    print("\n" + "="*60)
    print(f"✅ Report generated: {html_path.name}")
    print(f"📂 Open in browser: open {html_path.absolute()}")
    print("="*60)
    
except Exception as e:
    print(f"\n⚠️  Could not extract summary: {e}")
    print(f"✅ But HTML report was saved successfully!")

print("\n✨ Evidently drift detection complete!")
print(f"🌐 To view: open {html_path.absolute()}")
