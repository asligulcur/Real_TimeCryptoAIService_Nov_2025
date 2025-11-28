"""
Create Train/Test Split from Features
This script creates train.parquet and test.parquet files needed by models/train.py
"""

import pandas as pd
from pathlib import Path
import numpy as np

# Configuration
RANDOM_STATE = 42
THRESHOLD = 0.041799  # 95th percentile from feature spec
TRAIN_RATIO = 0.8

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "processed"
FEATURES_PATH = DATA_DIR / "features.parquet"
TRAIN_PATH = DATA_DIR / "train.parquet"
TEST_PATH = DATA_DIR / "test.parquet"

def main():
    print("=" * 70)
    print("Creating Train/Test Split for Model Training")
    print("=" * 70)
    
    # Load features
    print(f"\n📂 Loading features from: {FEATURES_PATH}")
    df = pd.read_parquet(FEATURES_PATH)
    print(f"   ✅ Loaded {len(df):,} records")
    print(f"   Shape: {df.shape}")
    print(f"   Columns: {list(df.columns)}")
    
    # Create volatility_spike label
    print(f"\n🎯 Creating volatility_spike label (threshold = {THRESHOLD})")
    df['volatility_spike'] = (df['volatility_60s'] > THRESHOLD).astype(int)
    
    spike_rate = df['volatility_spike'].mean() * 100
    print(f"   Spike rate: {spike_rate:.2f}%")
    print(f"   Total spikes: {df['volatility_spike'].sum():,}")
    print(f"   Total normal: {(df['volatility_spike'] == 0).sum():,}")
    
    # Stratified split (80/20) - ensures both sets have spikes
    print(f"\n✂️  Creating stratified split ({TRAIN_RATIO*100:.0f}/{(1-TRAIN_RATIO)*100:.0f})")
    print(f"   Using stratification to ensure spikes in both train and test sets")
    
    # Ensure timestamp is datetime
    if 'timestamp' not in df.columns:
        df['timestamp'] = df.index
    
    # Sort by timestamp to maintain temporal order
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    # Stratified split by volatility_spike
    from sklearn.model_selection import train_test_split
    
    train_df, test_df = train_test_split(
        df, 
        test_size=(1-TRAIN_RATIO),
        stratify=df['volatility_spike'],
        random_state=RANDOM_STATE
    )
    
    # Verify split
    print(f"\n📊 Split Summary:")
    print(f"   Train: {len(train_df):,} samples ({len(train_df)/len(df)*100:.1f}%)")
    print(f"      - Spikes: {train_df['volatility_spike'].sum():,} ({train_df['volatility_spike'].mean()*100:.2f}%)")
    print(f"      - Normal: {(train_df['volatility_spike']==0).sum():,}")
    print(f"      - Time range: {train_df['timestamp'].min()} to {train_df['timestamp'].max()}")
    
    print(f"\n   Test:  {len(test_df):,} samples ({len(test_df)/len(df)*100:.1f}%)")
    print(f"      - Spikes: {test_df['volatility_spike'].sum():,} ({test_df['volatility_spike'].mean()*100:.2f}%)")
    print(f"      - Normal: {(test_df['volatility_spike']==0).sum():,}")
    print(f"      - Time range: {test_df['timestamp'].min()} to {test_df['timestamp'].max()}")
    
    # Save to parquet
    print(f"\n💾 Saving split data...")
    train_df.to_parquet(TRAIN_PATH, index=False)
    print(f"   ✅ Train data saved to: {TRAIN_PATH}")
    print(f"      Size: {TRAIN_PATH.stat().st_size / 1024:.1f} KB")
    
    test_df.to_parquet(TEST_PATH, index=False)
    print(f"   ✅ Test data saved to: {TEST_PATH}")
    print(f"      Size: {TEST_PATH.stat().st_size / 1024:.1f} KB")
    
    print("\n" + "=" * 70)
    print("✅ Train/Test split created successfully!")
    print("=" * 70)
    print(f"\nNext steps:")
    print(f"  1. Run model training: python models/train.py")
    print(f"  2. Check MLflow UI: http://localhost:5001")
    print("=" * 70)

if __name__ == "__main__":
    main()
