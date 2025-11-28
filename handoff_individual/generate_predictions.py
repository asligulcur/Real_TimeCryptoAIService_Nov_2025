#!/usr/bin/env python3
"""
Generate predictions file for handoff package.
Uses the production Random Forest model to generate predictions on the test set.
"""

import pandas as pd
import joblib
from pathlib import Path
import sys

def generate_predictions():
    """Generate predictions using the production model."""
    
    project_root = Path(__file__).parent.parent
    
    print("=" * 60)
    print("Generating Predictions for Handoff Package")
    print("=" * 60)
    
    # Paths
    model_path = project_root / "handoff" / "models" / "artifacts" / "random_forest.joblib"
    features_path = project_root / "handoff" / "data" / "features_10min_slice.parquet"
    output_path = project_root / "handoff" / "reports" / "predictions.csv"
    
    # Load model
    print(f"\n1. Loading model: {model_path.name}")
    model = joblib.load(model_path)
    print(f"   ✅ Model loaded: {type(model).__name__}")
    
    # Load features
    print(f"\n2. Loading features: {features_path.name}")
    df = pd.read_parquet(features_path)
    print(f"   ✅ Loaded {len(df):,} rows with {len(df.columns)} columns")
    
    # Prepare features (drop non-feature columns)
    non_feature_cols = ['timestamp', 'volatility_spike', 'symbol']
    feature_cols = [col for col in df.columns if col not in non_feature_cols]
    
    X = df[feature_cols]
    print(f"\n3. Feature columns ({len(feature_cols)}):")
    print(f"   {feature_cols}")
    
    # Generate predictions
    print(f"\n4. Generating predictions...")
    predictions = model.predict(X)
    probabilities = model.predict_proba(X)[:, 1]  # Probability of spike (class 1)
    
    print(f"   ✅ Predictions generated")
    print(f"   Predicted spikes: {predictions.sum():,} / {len(predictions):,} ({predictions.sum()/len(predictions)*100:.1f}%)")
    
    # Create output dataframe
    output_df = pd.DataFrame({
        'timestamp': df['timestamp'] if 'timestamp' in df.columns else range(len(df)),
        'prediction': predictions,
        'probability': probabilities,
        'predicted_label': ['SPIKE' if p == 1 else 'NORMAL' for p in predictions]
    })
    
    # Add actual label if available
    if 'volatility_spike' in df.columns:
        output_df['actual_label'] = df['volatility_spike']
        output_df['correct'] = output_df['prediction'] == output_df['actual_label']
        accuracy = output_df['correct'].mean()
        print(f"   Accuracy: {accuracy*100:.2f}%")
    
    # Save
    output_df.to_csv(output_path, index=False)
    print(f"\n5. Saved predictions to: {output_path}")
    print(f"   Rows: {len(output_df):,}")
    print(f"   Size: {output_path.stat().st_size / 1024:.1f} KB")
    
    # Show sample
    print(f"\n6. Sample predictions (first 10 rows):")
    print(output_df.head(10).to_string(index=False))
    
    print("\n" + "=" * 60)
    print("✅ Predictions Generation Complete!")
    print("=" * 60)
    
    return output_df

if __name__ == "__main__":
    try:
        generate_predictions()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
