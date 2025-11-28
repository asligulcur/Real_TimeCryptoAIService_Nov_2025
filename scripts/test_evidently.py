#!/usr/bin/env python3
"""Quick test to verify Evidently works"""
import sys

print("="*50)
print("EVIDENTLY API TEST")
print("="*50)

# Test 1: Import
print("\n1. Testing imports...")
try:
    from evidently.report import Report
    from evidently.metric_preset import DataDriftPreset, DataQualityPreset
    import evidently
    print(f"   ✅ Evidently v{evidently.__version__} imported successfully")
except ImportError as e:
    print(f"   ❌ Import failed: {e}")
    sys.exit(1)

# Test 2: Create synthetic data
print("\n2. Creating test data...")
try:
    import pandas as pd
    import numpy as np
    
    np.random.seed(42)
    ref_data = pd.DataFrame({
        'feature1': np.random.normal(0, 1, 100),
        'feature2': np.random.uniform(0, 10, 100),
    })
    
    curr_data = pd.DataFrame({
        'feature1': np.random.normal(0.5, 1, 100),  # slight drift
        'feature2': np.random.uniform(0, 10, 100),
    })
    
    print(f"   ✅ Reference data: {ref_data.shape}")
    print(f"   ✅ Current data: {curr_data.shape}")
except Exception as e:
    print(f"   ❌ Data creation failed: {e}")
    sys.exit(1)

# Test 3: Create and run report
print("\n3. Creating Evidently report...")
try:
    report = Report(metrics=[DataDriftPreset()])
    print("   ✅ Report object created")
    
    print("   Running analysis...")
    report.run(reference_data=ref_data, current_data=curr_data)
    print("   ✅ Analysis completed")
    
    # Get results
    results = report.as_dict()
    print(f"   ✅ Got {len(results.get('metrics', []))} metrics")
    
except Exception as e:
    print(f"   ❌ Report generation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Save report
print("\n4. Saving report...")
try:
    import tempfile
    from pathlib import Path
    
    with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
        test_path = Path(f.name)
    
    report.save_html(str(test_path))
    
    if test_path.exists() and test_path.stat().st_size > 0:
        print(f"   ✅ HTML saved: {test_path.stat().st_size} bytes")
        test_path.unlink()  # Clean up
    else:
        print(f"   ❌ HTML file empty or not created")
        sys.exit(1)
        
except Exception as e:
    print(f"   ❌ Save failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*50)
print("✅ ALL TESTS PASSED")
print("="*50)
print("\nEvidently is working correctly!")
print("Ready to run full drift detection.\n")
