#!/usr/bin/env python3
"""
Test 2: Verify infer.py scores in < 2x real-time
"""

import time
import sys
import os
import pandas as pd

# Add models directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def test_inference_speed():
    """Test that inference is faster than 2x real-time"""
    
    print("=" * 60)
    print("TEST 2: infer.py scores in < 2x real-time")
    print("=" * 60)
    
    # Load test data to get timing info
    data_path = "../data/processed/test.parquet"  # Fixed: Point to data/processed/
    
    if not os.path.exists(data_path):
        print(f"\n❌ FAILED: Test data not found at {data_path}")
        return False
    
    test_df = pd.read_parquet(data_path)
    num_records = len(test_df)
    
    # Calculate real-time duration
    # Assume data was collected at ~1 record per second (adjust based on your data)
    # Check if timestamp column exists
    if 'timestamp' in test_df.columns:
        test_df['timestamp'] = pd.to_datetime(test_df['timestamp'])
        real_time_seconds = (test_df['timestamp'].max() - test_df['timestamp'].min()).total_seconds()
    else:
        # Estimate: assume ~1 record per second
        real_time_seconds = num_records
    
    print(f"\n📊 Test Dataset Info:")
    print(f"   Records: {num_records:,}")
    print(f"   Real-time duration: {real_time_seconds:,.1f} seconds ({real_time_seconds/3600:.2f} hours)")
    print(f"   Required inference time: < {2*real_time_seconds:,.1f} seconds (2x real-time)")
    
    # Run inference and time it
    print(f"\n⏱️  Running inference...")
    
    from models.infer import load_model, predict
    
    start_time = time.time()
    
    try:
        # Load model
        model = load_model()
        
        # Prepare features (drop label if exists)
        feature_cols = [col for col in test_df.columns if col not in ['label', 'is_volatile', 'timestamp']]
        X_test = test_df[feature_cols]
        
        # Run predictions
        predictions = predict(model, X_test)
        
        inference_time = time.time() - start_time
        
        print(f"\n✓ Inference completed in {inference_time:.2f} seconds")
        print(f"✓ Scored {num_records:,} records")
        print(f"✓ Throughput: {num_records/inference_time:,.0f} records/second")
        
        # Check if within 2x real-time
        max_allowed_time = 2 * real_time_seconds
        
        print(f"\n📈 Performance Analysis:")
        print(f"   Inference time: {inference_time:.2f} seconds")
        print(f"   Max allowed: {max_allowed_time:,.2f} seconds (2x real-time)")
        print(f"   Speedup: {real_time_seconds/inference_time:.1f}x faster than real-time")
        
        if inference_time < max_allowed_time:
            print("\n" + "=" * 60)
            print(f"✅ TEST 2 PASSED: Inference is {max_allowed_time/inference_time:.1f}x faster than required!")
            print("=" * 60)
            return True
        else:
            print("\n" + "=" * 60)
            print(f"❌ TEST 2 FAILED: Inference too slow!")
            print(f"   Required: < {max_allowed_time:.2f}s")
            print(f"   Actual: {inference_time:.2f}s")
            print("=" * 60)
            return False
            
    except Exception as e:
        print(f"\n❌ FAILED: Error during inference")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_inference_speed()
    exit(0 if success else 1)
