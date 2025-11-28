#!/usr/bin/env python3
"""
Test 1: Verify MLflow has at least 2 runs (baseline and ML model)
"""

import mlflow
from mlflow.tracking import MlflowClient

def test_mlflow_runs():
    """Check if MLflow has at least 2 runs logged"""
    
    print("=" * 60)
    print("TEST 1: MLflow UI shows at least 2 runs")
    print("=" * 60)
    
    # Set MLflow tracking URI
    mlflow.set_tracking_uri("http://localhost:5001")
    
    # Get client
    client = MlflowClient()
    
    # Get experiment (assuming default experiment ID 1)
    try:
        experiment_id = "1"
        runs = client.search_runs(experiment_ids=[experiment_id])
        
        print(f"\n✓ Connected to MLflow at http://localhost:5001")
        print(f"✓ Found {len(runs)} runs in experiment {experiment_id}")
        
        if len(runs) < 2:
            print(f"\n❌ FAILED: Only {len(runs)} run(s) found. Need at least 2 (baseline + ML).")
            return False
        
        print(f"\n✅ PASSED: Found {len(runs)} runs (≥ 2 required)")
        print("\nRun Details:")
        print("-" * 60)
        
        for i, run in enumerate(runs, 1):
            run_name = run.data.tags.get('mlflow.runName', 'Unknown')
            pr_auc = run.data.metrics.get('pr_auc', 'Not logged')
            f1 = run.data.metrics.get('test_f1', 'Not logged')
            
            print(f"\n{i}. Run: {run_name}")
            print(f"   Run ID: {run.info.run_id}")
            print(f"   PR-AUC: {pr_auc}")
            print(f"   F1 Score: {f1}")
            print(f"   Status: {run.info.status}")
        
        print("\n" + "=" * 60)
        print("✅ TEST 1 PASSED: MLflow has required runs")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ FAILED: Error connecting to MLflow")
        print(f"Error: {e}")
        print("\nMake sure MLflow is running: docker compose ps")
        return False

if __name__ == "__main__":
    success = test_mlflow_runs()
    exit(0 if success else 1)
