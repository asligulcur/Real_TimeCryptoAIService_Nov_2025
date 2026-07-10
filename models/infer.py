"""
Model Inference Script for Crypto Volatility Detection
Author: Asli Gulcur

This script loads the trained model and performs real-time inference.
Must score in < 2x real-time for the given window size.
"""

import argparse
import time
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)


class VolatilityPredictor:
    """Real-time volatility spike predictor."""

    def __init__(self, model_path=None):
        """
        Initialize predictor with trained model.

        Args:
            model_path: Path to saved model file (.joblib)
        """
        if model_path is None:
            # Default to Random Forest (best model)
            model_path = Path(__file__).parent / "artifacts" / "random_forest.joblib"

        self.model_path = Path(model_path)
        self.model = None
        self.load_model()

    def load_model(self):
        """Load the trained model from disk."""
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found: {self.model_path}")

        print(f"📦 Loading model from: {self.model_path.name}")
        self.model = joblib.load(self.model_path)
        print(f"✅ Model loaded: {type(self.model).__name__}")

    def predict(self, X):
        """
        Predict volatility spikes for input features.

        Args:
            X: DataFrame or array with feature columns

        Returns:
            predictions: Binary predictions (0=normal, 1=spike)
            probabilities: Probability of spike [0-1]
        """
        if self.model is None:
            raise ValueError("Model not loaded. Call load_model() first.")

        predictions = self.model.predict(X)
        probabilities = self.model.predict_proba(X)[:, 1]

        return predictions, probabilities

    def predict_single(self, features_dict):
        """
        Predict for a single observation.

        Args:
            features_dict: Dictionary of feature names and values

        Returns:
            prediction: 0 or 1
            probability: Spike probability [0-1]
        """
        df = pd.DataFrame([features_dict])
        pred, proba = self.predict(df)
        return pred[0], proba[0]

    def benchmark_inference_speed(self, X, window_seconds=60):
        """
        Benchmark inference speed vs real-time requirement.

        Args:
            X: Test data
            window_seconds: Window size in seconds (default 60s for 60s windows)

        Returns:
            metrics: Dictionary with timing statistics
        """
        print("\n⏱️  Benchmarking inference speed...")
        print(f"   Window size: {window_seconds}s")
        print(f"   Test samples: {len(X):,}")

        # Time predictions
        start_time = time.time()
        predictions, probabilities = self.predict(X)
        inference_time = time.time() - start_time

        # Calculate metrics
        samples_per_second = len(X) / inference_time
        time_per_sample = inference_time / len(X) * 1000  # ms

        # Real-time requirement: must process window_seconds of data in < 2x window_seconds
        max_allowed_time = 2 * window_seconds
        speedup = max_allowed_time / inference_time

        metrics = {
            "total_samples": len(X),
            "inference_time_seconds": inference_time,
            "samples_per_second": samples_per_second,
            "time_per_sample_ms": time_per_sample,
            "window_seconds": window_seconds,
            "max_allowed_seconds": max_allowed_time,
            "speedup_vs_realtime": speedup,
            "meets_requirement": inference_time < max_allowed_time,
        }

        # Print results
        print("\n   📊 Results:")
        print(f"      Total inference time: {inference_time:.3f}s")
        print(f"      Time per sample:      {time_per_sample:.3f}ms")
        print(f"      Throughput:           {samples_per_second:.0f} samples/sec")
        print(f"      Max allowed time:     {max_allowed_time:.1f}s (2x real-time)")
        print(f"      Speedup:              {speedup:.1f}x real-time")

        if metrics["meets_requirement"]:
            print(f"\n   ✅ PASS: Inference is {speedup:.1f}x faster than real-time!")
        else:
            print(f"\n   ❌ FAIL: Too slow for real-time (need < {max_allowed_time}s)")

        return metrics

    def evaluate_predictions(self, y_true, y_pred, y_proba):
        """
        Evaluate predictions against ground truth labels.

        Args:
            y_true: True labels
            y_pred: Predicted labels
            y_proba: Predicted probabilities

        Returns:
            metrics: Dictionary with evaluation metrics
        """
        print("\n📊 Evaluating Model Performance...")

        # Calculate metrics
        metrics = {
            "precision": precision_score(y_true, y_pred),
            "recall": recall_score(y_true, y_pred),
            "f1_score": f1_score(y_true, y_pred),
            "pr_auc": average_precision_score(y_true, y_proba),
        }

        # Confusion matrix
        cm = confusion_matrix(y_true, y_pred)
        tn, fp, fn, tp = cm.ravel()

        metrics["confusion_matrix"] = {
            "true_negative": int(tn),
            "false_positive": int(fp),
            "false_negative": int(fn),
            "true_positive": int(tp),
        }

        # Print results
        print("\n   🎯 Classification Metrics:")
        print(f"      Precision:  {metrics['precision']:.4f}")
        print(f"      Recall:     {metrics['recall']:.4f}")
        print(f"      F1 Score:   {metrics['f1_score']:.4f}")
        print(f"      PR-AUC:     {metrics['pr_auc']:.4f}")

        print("\n   📊 Confusion Matrix:")
        print(f"      True Negatives:  {tn:,}")
        print(f"      False Positives: {fp:,}")
        print(f"      False Negatives: {fn:,}")
        print(f"      True Positives:  {tp:,}")

        # Classification report
        print("\n   📋 Classification Report:")
        print(classification_report(y_true, y_pred, target_names=["Normal", "Spike"]))

        return metrics


def main():
    """Main inference pipeline with testing."""
    # Define default path relative to this script file
    default_model_path = Path(__file__).parent / "artifacts" / "random_forest.joblib"
    default_test_data_path = (
        Path(__file__).parent.parent / "data" / "processed" / "test.parquet"
    )  # Fixed: Point to data/processed/

    parser = argparse.ArgumentParser(description="Crypto Volatility Inference")
    parser.add_argument(
        "--model", type=str, help="Path to model file", default=str(default_model_path)
    )
    parser.add_argument(
        "--test-data",
        type=str,
        help="Path to test data",
        default=str(default_test_data_path),
    )
    parser.add_argument(
        "--benchmark", action="store_true", help="Run inference speed benchmark"
    )
    parser.add_argument(
        "--window", type=int, default=60, help="Window size in seconds for benchmark"
    )
    args = parser.parse_args()

    print("=" * 70)
    print("🚀 CRYPTO VOLATILITY INFERENCE")
    print("=" * 70)

    # Initialize predictor
    predictor = VolatilityPredictor(model_path=args.model)

    # Load test data
    test_path = Path(args.test_data)
    if not test_path.exists():
        print(f"❌ Test data not found: {test_path}")
        return

    print(f"\n📂 Loading test data from: {test_path.name}")
    test_df = pd.read_parquet(test_path)

    # Prepare features
    feature_cols = [
        col
        for col in test_df.columns
        if col not in ["volatility_spike", "timestamp", "symbol"]
    ]
    X_test = test_df[feature_cols]

    if "volatility_spike" in test_df.columns:
        y_test = test_df["volatility_spike"]
        print(
            f"   Samples: {len(X_test):,} | Positive: {y_test.sum():,} ({y_test.mean()*100:.2f}%)"
        )
    else:
        print(f"   Samples: {len(X_test):,}")

    # Run predictions
    print("\n🔮 Running predictions...")
    predictions, probabilities = predictor.predict(X_test)

    spike_count = predictions.sum()
    print("   ✅ Predictions complete!")
    print(
        f"   📊 Detected {spike_count:,} volatility spikes ({spike_count/len(predictions)*100:.2f}%)"
    )

    # Show sample predictions
    print("\n   📋 Sample predictions (first 5):")
    for i in range(min(5, len(predictions))):
        label = (
            f"(Actual: {y_test.iloc[i]})"
            if "volatility_spike" in test_df.columns
            else ""
        )
        print(
            f"      Sample {i+1}: Pred={predictions[i]}, Prob={probabilities[i]:.4f} {label}"
        )

    # Evaluate if labels are available
    if "volatility_spike" in test_df.columns:
        predictor.evaluate_predictions(y_test, predictions, probabilities)

    # Benchmark if requested
    if args.benchmark:
        metrics = predictor.benchmark_inference_speed(
            X_test, window_seconds=args.window
        )

        # Save benchmark results
        benchmark_path = Path(__file__).parent / "artifacts" / "inference_benchmark.txt"
        benchmark_path.parent.mkdir(parents=True, exist_ok=True)
        with open(benchmark_path, "w") as f:
            f.write("Inference Speed Benchmark\n")
            f.write("=" * 50 + "\n")
            for key, value in metrics.items():
                f.write(f"{key}: {value}\n")
        print(f"\n   💾 Benchmark results saved to: {benchmark_path}")

    print("\n" + "=" * 70)
    print("✅ Inference complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
