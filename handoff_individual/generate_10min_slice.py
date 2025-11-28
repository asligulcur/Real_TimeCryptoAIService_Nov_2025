#!/usr/bin/env python3
"""
Generate 10-minute data slice for team handoff package.
Extracts the first 10 minutes of data from the full dataset.
"""

import pandas as pd
from pathlib import Path
import sys

def generate_10min_slice():
    """Extract 10-minute slice from processed features."""
    
    # Paths
    project_root = Path(__file__).parent.parent
    features_path = project_root / "data" / "processed" / "features.parquet"
    output_dir = project_root / "handoff" / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("Generating 10-Minute Data Slice for Handoff Package")
    print("=" * 60)
    
    # Load full features dataset
    print(f"\n1. Loading features from: {features_path}")
    df = pd.read_parquet(features_path)
    print(f"   ✅ Loaded {len(df):,} rows")
    
    # Ensure timestamp column exists
    if 'timestamp' not in df.columns:
        print("   ⚠️  No 'timestamp' column found. Available columns:")
        print(f"   {list(df.columns)}")
        
        # Try to find a time-related column
        time_cols = [col for col in df.columns if 'time' in col.lower() or 'date' in col.lower()]
        if time_cols:
            print(f"   Using '{time_cols[0]}' as timestamp column")
            df['timestamp'] = pd.to_datetime(df[time_cols[0]])
        else:
            print("   ❌ Cannot find timestamp column. Using first 10% of rows instead.")
            slice_size = int(len(df) * 0.10)
            df_slice = df.head(slice_size)
            
            # Save features slice
            features_output = output_dir / "features_10min_slice.parquet"
            df_slice.to_parquet(features_output, index=False)
            print(f"\n✅ Saved {len(df_slice):,} rows to: {features_output}")
            return
    else:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Get time range
    start_time = df['timestamp'].min()
    end_time = df['timestamp'].max()
    duration_seconds = (end_time - start_time).total_seconds()
    
    print(f"\n2. Dataset time range:")
    print(f"   Start: {start_time}")
    print(f"   End:   {end_time}")
    print(f"   Duration: {duration_seconds:.1f} seconds ({duration_seconds/60:.1f} minutes)")
    
    # Extract 10-minute slice (600 seconds)
    slice_end_time = start_time + pd.Timedelta(seconds=600)
    df_slice = df[df['timestamp'] <= slice_end_time].copy()
    
    print(f"\n3. Extracting 10-minute slice:")
    print(f"   From: {start_time}")
    print(f"   To:   {slice_end_time}")
    print(f"   Rows: {len(df_slice):,} / {len(df):,} ({len(df_slice)/len(df)*100:.1f}%)")
    
    # Create raw slice (just essential columns)
    raw_cols = ['timestamp']
    price_cols = [col for col in df_slice.columns if col in ['price', 'bid', 'ask', 'symbol']]
    raw_cols.extend(price_cols)
    
    if all(col in df_slice.columns for col in raw_cols):
        df_raw = df_slice[raw_cols].copy()
        raw_output = output_dir / "raw_10min_slice.parquet"
        df_raw.to_parquet(raw_output, index=False)
        print(f"\n4. Saved raw slice: {raw_output}")
        print(f"   Columns: {list(df_raw.columns)}")
        print(f"   Size: {raw_output.stat().st_size / 1024:.1f} KB")
    else:
        print(f"\n4. ⚠️  Skipping raw slice (missing columns: {set(raw_cols) - set(df_slice.columns)})")
    
    # Save full features slice
    features_output = output_dir / "features_10min_slice.parquet"
    df_slice.to_parquet(features_output, index=False)
    print(f"\n5. Saved features slice: {features_output}")
    print(f"   Columns: {len(df_slice.columns)} features")
    print(f"   Size: {features_output.stat().st_size / 1024:.1f} KB")
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ 10-Minute Data Slice Generation Complete!")
    print("=" * 60)
    print(f"\nFiles created in: {output_dir}")
    if (output_dir / "raw_10min_slice.parquet").exists():
        print(f"  - raw_10min_slice.parquet ({len(df_raw):,} rows)")
    print(f"  - features_10min_slice.parquet ({len(df_slice):,} rows)")
    print("\nThese files are ready for the team handoff package.")
    
    return df_slice

if __name__ == "__main__":
    try:
        generate_10min_slice()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
