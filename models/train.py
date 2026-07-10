"""
Model Training Script for Crypto Volatility Detection
Author: Asli Gulcur

This script trains baseline and ML models for volatility spike prediction.
Logs all experiments to MLflow for tracking and comparison.
"""

import warnings
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

warnings.filterwarnings("ignore")

# Configuration
RANDOM_STATE = 42
THRESHOLD_95TH = 0.041799  # 95th percentile threshold
# MLFLOW_TRACKING_URI = "http://localhost:5001" # Commented out to use local file tracking
DATA_DIR = (
    Path(__file__).parent.parent / "data" / "processed"
)  # Fixed: Point to data/processed/
ARTIFACTS_DIR = Path(__file__).parent / "artifacts"

# Ensure directories exist
ARTIFACTS_DIR.mkdir(exist_ok=True)


def load_data():
    """Load preprocessed train and test data created by scripts/create_train_test_split.py.

    The train/test split is generated from data/processed/features.parquet using
    stratified sampling (80/20) to maintain the same spike rate (~5%) in both sets.
    """
    print("📂 Loading pre-split train and test data...")
    train_df = pd.read_parquet(DATA_DIR / "train.parquet")
    test_df = pd.read_parquet(DATA_DIR / "test.parquet")

    # The label column in the parquet files is 'volatility_spike'
    label_col = "volatility_spike"

    # Separate features and labels
    feature_cols = [
        col for col in train_df.columns if col not in [label_col, "timestamp", "symbol"]
    ]

    X_train = train_df[feature_cols]
    y_train = train_df[label_col]
    X_test = test_df[feature_cols]
    y_test = test_df[label_col]

    print(
        f"   Train: {len(X_train):,} samples, {y_train.sum():,} positive ({y_train.mean()*100:.2f}%)"
    )
    print(
        f"   Test:  {len(X_test):,} samples, {y_test.sum():,} positive ({y_test.mean()*100:.2f}%)"
    )

    return X_train, X_test, y_train, y_test, feature_cols


def evaluate_model(y_true, y_pred, y_proba=None):
    """Calculate comprehensive evaluation metrics."""
    metrics = {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred),
        "recall": recall_score(y_true, y_pred),
        "f1_score": f1_score(y_true, y_pred),
    }

    if y_proba is not None:
        metrics["roc_auc"] = roc_auc_score(y_true, y_proba)
        metrics["pr_auc"] = average_precision_score(y_true, y_proba)

    return metrics


def train_baseline_zscore(X_train, X_test, y_train, y_test):
    """Train baseline z-score rule-based model."""
    print("\n🎯 Training Baseline #1: Z-Score Rule-Based Detector")

    with mlflow.start_run(run_name="z_score_baseline"):
        # Log parameters
        mlflow.log_param("model_type", "Z-Score Rule-Based")
        mlflow.log_param("threshold", THRESHOLD_95TH)
        mlflow.log_param("z_threshold", 2.0)

        # Apply z-score rule on test set
        volatility_col = "volatility_60s"
        mean_vol = X_train[volatility_col].mean()
        std_vol = X_train[volatility_col].std()

        z_scores = (X_test[volatility_col] - mean_vol) / std_vol
        y_pred = (z_scores > 2.0).astype(int)
        y_proba = z_scores / z_scores.max()  # Normalize for PR-AUC

        # Evaluate
        metrics = evaluate_model(y_test, y_pred, y_proba)

        # Log metrics
        for name, value in metrics.items():
            mlflow.log_metric(name, value)

        print(f"   ✅ F1 Score: {metrics['f1_score']:.4f}")
        print(f"   ✅ PR-AUC:   {metrics['pr_auc']:.4f}")

        return metrics


def train_logistic_regression(X_train, X_test, y_train, y_test):
    """Train baseline logistic regression model."""
    print("\n🎯 Training Baseline #2: Logistic Regression")

    with mlflow.start_run(run_name="baseline_logistic_regression"):
        # Log parameters
        mlflow.log_param("model_type", "Logistic Regression")
        mlflow.log_param("random_state", RANDOM_STATE)
        mlflow.log_param("max_iter", 1000)

        # Train model
        lr_model = LogisticRegression(random_state=RANDOM_STATE, max_iter=1000)
        lr_model.fit(X_train, y_train)

        # Predictions
        y_pred = lr_model.predict(X_test)
        y_proba = lr_model.predict_proba(X_test)[:, 1]

        # Evaluate
        metrics = evaluate_model(y_test, y_pred, y_proba)

        # Log metrics
        for name, value in metrics.items():
            mlflow.log_metric(name, value)

        # Save model
        model_path = ARTIFACTS_DIR / "logistic_regression.joblib"
        joblib.dump(lr_model, model_path)
        mlflow.log_artifact(str(model_path))
        mlflow.sklearn.log_model(lr_model, "model")

        print(f"   ✅ F1 Score: {metrics['f1_score']:.4f}")
        print(f"   ✅ PR-AUC:   {metrics['pr_auc']:.4f}")

        return metrics, lr_model


def train_random_forest(X_train, X_test, y_train, y_test, feature_cols):
    """Train production Random Forest model."""
    print("\n🎯 Training Production Model: Random Forest")

    with mlflow.start_run(run_name="random_forest"):
        # Hyperparameters
        params = {
            "n_estimators": 100,
            "max_depth": 10,
            "min_samples_split": 20,
            "min_samples_leaf": 10,
            "random_state": RANDOM_STATE,
            "n_jobs": -1,
        }

        # Log parameters
        mlflow.log_param("model_type", "Random Forest")
        for key, value in params.items():
            mlflow.log_param(key, value)

        # Train model
        rf_model = RandomForestClassifier(**params)
        rf_model.fit(X_train, y_train)

        # Predictions
        y_pred = rf_model.predict(X_test)
        y_proba = rf_model.predict_proba(X_test)[:, 1]

        # Evaluate
        metrics = evaluate_model(y_test, y_pred, y_proba)

        # Log metrics
        for name, value in metrics.items():
            mlflow.log_metric(name, value)

        # Feature importance
        feature_importance = pd.DataFrame(
            {"feature": feature_cols, "importance": rf_model.feature_importances_}
        ).sort_values("importance", ascending=False)

        print("\n   📊 Top 5 Features:")
        for _idx, row in feature_importance.head(5).iterrows():
            print(f"      {row['feature']}: {row['importance']:.4f}")

        # Save model
        model_path = ARTIFACTS_DIR / "random_forest.joblib"
        joblib.dump(rf_model, model_path)
        mlflow.log_artifact(str(model_path))
        mlflow.sklearn.log_model(rf_model, "model")

        # Save feature importance
        fi_path = ARTIFACTS_DIR / "feature_importance.csv"
        feature_importance.to_csv(fi_path, index=False)
        mlflow.log_artifact(str(fi_path))

        print(f"\n   ✅ F1 Score: {metrics['f1_score']:.4f}")
        print(f"   ✅ PR-AUC:   {metrics['pr_auc']:.4f}")

        return metrics, rf_model


def main():
    """Main training pipeline."""
    print("=" * 70)
    print("🚀 CRYPTO VOLATILITY MODEL TRAINING")
    print("=" * 70)

    # Set MLflow tracking URI to use a local directory
    mlflow.set_tracking_uri("file://" + str(Path(__file__).parent.parent / "mlruns"))
    mlflow.set_experiment("crypto_volatility_detection")

    # Load data
    X_train, X_test, y_train, y_test, feature_cols = load_data()

    # Train all models
    results = {}

    # 1. Z-Score Baseline
    results["zscore"] = train_baseline_zscore(X_train, X_test, y_train, y_test)

    # 2. Logistic Regression
    results["logistic"], lr_model = train_logistic_regression(
        X_train, X_test, y_train, y_test
    )

    # 3. Random Forest (Production)
    results["random_forest"], rf_model = train_random_forest(
        X_train, X_test, y_train, y_test, feature_cols
    )

    # Summary
    print("\n" + "=" * 70)
    print("📊 TRAINING COMPLETE - MODEL COMPARISON")
    print("=" * 70)
    print(f"\n{'Model':<25} {'F1':<8} {'PR-AUC':<8} {'Precision':<10} {'Recall':<8}")
    print("-" * 70)

    for model_name, metrics in results.items():
        print(
            f"{model_name:<25} {metrics['f1_score']:<8.4f} {metrics.get('pr_auc', 0):<8.4f} "
            f"{metrics['precision']:<10.4f} {metrics['recall']:<8.4f}"
        )

    # Best model
    best_model = max(results.items(), key=lambda x: x[1].get("pr_auc", 0))
    print(
        f"\n✅ Best Model: {best_model[0].upper()} (PR-AUC: {best_model[1]['pr_auc']:.4f})"
    )

    print(f"\n✅ Models saved to: {ARTIFACTS_DIR}")
    print("✅ View experiments in the 'mlruns' directory.")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
