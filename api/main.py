"""
FastAPI service for real-time crypto volatility prediction.

This API provides endpoints for:
- Health checks
- Model predictions
- Version information
- Prometheus metrics

Author: CMU Heinz Team
Course: Operationalizing AI
Date: November 2025
"""

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import PlainTextResponse
from prometheus_client import Counter, Histogram, generate_latest
from pydantic import BaseModel, Field

# ============================================================================
# Configuration
# ============================================================================

# API Configuration
API_VERSION = "1.0.0"
MODEL_VERSION = "1.0"
SERVICE_NAME = "crypto-volatility-api"

# Model variant selection (ml or baseline)
MODEL_VARIANT = os.getenv("MODEL_VARIANT", "ml").lower()
if MODEL_VARIANT not in ["ml", "baseline"]:
    print(f"⚠️  Invalid MODEL_VARIANT '{MODEL_VARIANT}', defaulting to 'ml'")
    MODEL_VARIANT = "ml"

# Model paths (relative to project root)
PROJECT_ROOT = Path(__file__).parent.parent
MODEL_PATH = PROJECT_ROOT / "models" / "artifacts" / "random_forest.joblib"
BASELINE_MODEL_PATH = PROJECT_ROOT / "ml" / "baseline.py"

# Feature names (must match training data)
FEATURE_NAMES = [
    "price",
    "bid",
    "ask",
    "return_10s",
    "return_30s",
    "return_60s",
    "volatility_30s",
    "volatility_60s",
    "volatility_120s",
    "spread",
    "intensity_30s",
    "intensity_60s",
    "intensity_120s",
]

# ============================================================================
# Prometheus Metrics
# ============================================================================

# Request counters by endpoint and status
request_counter = Counter(
    "api_requests_total",
    "Total number of API requests",
    ["endpoint", "method", "status"],
)

predict_counter = Counter(
    "predict_requests_total",
    "Total number of prediction requests",
    ["model_version"],
)

predict_errors = Counter(
    "predict_errors_total",
    "Total number of prediction errors",
    ["error_type"],
)

# Response time histograms with buckets optimized for ML inference
predict_latency = Histogram(
    "predict_latency_seconds",
    "Prediction request latency in seconds",
    ["endpoint"],
    buckets=(
        0.005,
        0.01,
        0.025,
        0.05,
        0.1,
        0.25,
        0.5,
        1.0,
        2.5,
        5.0,
        10.0,
    ),  # 5ms to 10s
)

api_latency = Histogram(
    "api_request_duration_seconds",
    "API request duration in seconds",
    ["endpoint", "method"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

# Gauges for current state
model_loaded_gauge = Counter(
    "model_loaded", "Model loaded status (1=loaded, 0=not loaded)"
)

# Kafka consumer lag (will be updated externally)
from prometheus_client import Gauge

consumer_lag_gauge = Gauge(
    "kafka_consumer_lag",
    "Kafka consumer lag in messages",
    ["topic", "partition", "consumer_group"],
)

# Model prediction distribution
prediction_distribution = Counter(
    "predictions_by_class_total",
    "Total predictions by class",
    ["class_label", "model_version"],
)

# Confidence distribution histogram
prediction_confidence = Histogram(
    "prediction_confidence",
    "Distribution of prediction confidence scores",
    ["prediction_class"],
    buckets=(0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0),
)

# Health check counter
health_counter = Counter(
    "health_requests_total", "Total number of health check requests"
)

# Model variant indicator
from prometheus_client import Info

model_info = Info("model", "Information about the active model")

# Model variant gauge (1 for active variant, 0 for inactive)
model_variant_gauge = Gauge(
    "model_variant_active",
    "Active model variant (1=active, 0=inactive)",
    ["variant"],
)

# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Crypto Volatility Detection API",
    description="Real-time API for predicting cryptocurrency volatility spikes",
    version=API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ============================================================================
# Pydantic Models (Request/Response Schemas)
# ============================================================================


class FeatureInput(BaseModel):
    """Input features for volatility prediction."""

    price: float = Field(..., description="Current BTC-USD price", example=91234.56)
    bid: float = Field(..., description="Best bid price", example=91234.00)
    ask: float = Field(..., description="Best ask price", example=91235.00)
    spread: float = Field(..., description="Bid-ask spread", example=1.0)
    volatility_30s: float = Field(
        ..., description="30-second volatility", example=0.0123
    )
    volatility_60s: float = Field(
        ..., description="60-second volatility", example=0.0145
    )
    volatility_120s: float = Field(
        ..., description="120-second volatility", example=0.0167
    )
    return_10s: float = Field(..., description="10-second return", example=0.0001)
    return_30s: float = Field(..., description="30-second return", example=0.0003)
    return_60s: float = Field(..., description="60-second return", example=0.0005)
    intensity_30s: float = Field(
        ..., description="30-second trade intensity", example=15.2
    )
    intensity_60s: float = Field(
        ..., description="60-second trade intensity", example=28.5
    )
    intensity_120s: float = Field(
        ..., description="120-second trade intensity", example=52.3
    )

    class Config:
        json_schema_extra = {
            "example": {
                "price": 91234.56,
                "bid": 91234.00,
                "ask": 91235.00,
                "spread": 1.0,
                "volatility_30s": 0.0123,
                "volatility_60s": 0.0145,
                "volatility_120s": 0.0167,
                "return_10s": 0.0001,
                "return_30s": 0.0003,
                "return_60s": 0.0005,
                "intensity_30s": 15.2,
                "intensity_60s": 28.5,
                "intensity_120s": 52.3,
            }
        }


class BatchFeatureInput(BaseModel):
    """Batch of feature inputs for predictions."""

    features: List[FeatureInput] = Field(..., description="List of feature sets")


class PredictionResponse(BaseModel):
    """Prediction response."""

    prediction: int = Field(..., description="0=normal, 1=spike")
    probability: float = Field(..., description="Probability of spike (0.0-1.0)")
    timestamp: str = Field(..., description="Prediction timestamp (ISO format)")
    model_version: str = Field(..., description="Model version used")

    class Config:
        json_schema_extra = {
            "example": {
                "prediction": 1,
                "probability": 0.87,
                "timestamp": "2025-11-26T10:30:45.123456",
                "model_version": "1.0",
            }
        }


class BatchPredictionResponse(BaseModel):
    """Batch prediction response."""

    predictions: List[PredictionResponse]
    count: int


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")
    timestamp: str = Field(..., description="Check timestamp")
    model_loaded: bool = Field(..., description="Is model loaded?")
    uptime_seconds: float = Field(..., description="Service uptime in seconds")


class VersionResponse(BaseModel):
    """Version information response."""

    api_version: str = Field(..., description="API version")
    model_version: str = Field(..., description="Model version")
    service_name: str = Field(..., description="Service name")
    python_version: str = Field(..., description="Python version")
    dependencies: Dict[str, str] = Field(..., description="Key dependency versions")


# ============================================================================
# Global State
# ============================================================================


class AppState:
    """Global application state."""

    def __init__(self):
        self.model = None
        self.model_loaded = False
        self.model_variant = MODEL_VARIANT
        self.start_time = time.time()

    def load_model(self):
        """Load the trained model based on MODEL_VARIANT."""
        try:
            if self.model_variant == "baseline":
                # Load baseline rule-based model
                print(f"📊 Loading BASELINE model (rule-based fallback)")
                sys.path.insert(0, str(PROJECT_ROOT / "ml"))
                from baseline import load_baseline_model
                
                self.model = load_baseline_model()
                self.model_loaded = True
                print(f"✅ Baseline model loaded successfully")
                
                # Set model info
                model_info.info({
                    'variant': 'baseline',
                    'version': 'baseline-1.0',
                    'type': 'rule_based',
                    'description': 'Simple threshold-based fallback model'
                })
                
            else:  # ml variant (default)
                # Load ML model
                if not MODEL_PATH.exists():
                    raise FileNotFoundError(f"Model not found at {MODEL_PATH}")
                
                print(f"🤖 Loading ML model from {MODEL_PATH}")
                self.model = joblib.load(MODEL_PATH)
                self.model_loaded = True
                print(f"✅ ML model loaded successfully from {MODEL_PATH}")
                
                # Set model info
                model_info.info({
                    'variant': 'ml',
                    'version': MODEL_VERSION,
                    'type': 'random_forest',
                    'description': 'Production Random Forest model'
                })
            
            # Set variant gauges
            model_variant_gauge.labels(variant="ml").set(1 if self.model_variant == "ml" else 0)
            model_variant_gauge.labels(variant="baseline").set(1 if self.model_variant == "baseline" else 0)
            
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            raise

    def get_uptime(self) -> float:
        """Get service uptime in seconds."""
        return time.time() - self.start_time


# Initialize application state
state = AppState()


# ============================================================================
# Startup Event
# ============================================================================


@app.on_event("startup")
async def startup_event():
    """Load model on startup."""
    print(f"🚀 Starting {SERVICE_NAME} v{API_VERSION}")
    print(f"🎯 Model variant: {MODEL_VARIANT.upper()}")
    if MODEL_VARIANT == "ml":
        print(f"📍 Model path: {MODEL_PATH}")
    else:
        print(f"📍 Using baseline rule-based model")

    try:
        state.load_model()
        # Initialize model loaded metric
        model_loaded_gauge.inc()
        print("✅ API ready to serve predictions")
    except Exception as e:
        print(f"⚠️  Warning: Could not load model: {e}")
        print("⚠️  API will start but predictions will fail")


# ============================================================================
# API Endpoints
# ============================================================================


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Monitoring"],
    summary="Health check endpoint",
    description="Check if the service is running and ready to serve requests",
)
async def health_check():
    """
    Health check endpoint.

    Returns:
        HealthResponse: Service health status
    """
    request_start = time.time()

    health_counter.inc()
    request_counter.labels(endpoint="/health", method="GET", status="200").inc()

    # Record latency
    latency = time.time() - request_start
    api_latency.labels(endpoint="/health", method="GET").observe(latency)

    return HealthResponse(
        status="healthy" if state.model_loaded else "degraded",
        timestamp=datetime.utcnow().isoformat(),
        model_loaded=state.model_loaded,
        uptime_seconds=state.get_uptime(),
    )


@app.get(
    "/version",
    response_model=VersionResponse,
    tags=["Information"],
    summary="Version information",
    description="Get API and model version information",
)
async def get_version():
    """
    Get version information.

    Returns:
        VersionResponse: Version details
    """
    import sys
    import sklearn
    import fastapi

    return VersionResponse(
        api_version=API_VERSION,
        model_version=MODEL_VERSION,
        service_name=SERVICE_NAME,
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        dependencies={
            "fastapi": fastapi.__version__,
            "scikit-learn": sklearn.__version__,
            "pandas": pd.__version__,
            "numpy": np.__version__,
        },
    )


@app.post(
    "/predict",
    response_model=PredictionResponse,
    tags=["Prediction"],
    summary="Make a prediction",
    description="Predict volatility spike for given features",
    status_code=status.HTTP_200_OK,
)
async def predict(features: FeatureInput):
    """
    Make a single prediction.

    Args:
        features: Input features

    Returns:
        PredictionResponse: Prediction result

    Raises:
        HTTPException: If model not loaded or prediction fails
    """
    # Time the entire request
    request_start = time.time()

    # Increment request counter
    predict_counter.labels(model_version=MODEL_VERSION).inc()
    request_counter.labels(endpoint="/predict", method="POST", status="processing").inc()

    # Check if model is loaded
    if not state.model_loaded:
        predict_errors.labels(error_type="model_not_loaded").inc()
        request_counter.labels(endpoint="/predict", method="POST", status="503").inc()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not loaded. Service not ready.",
        )

    try:
        # Convert input to appropriate format
        feature_dict = features.dict()
        
        if state.model_variant == "baseline":
            # Baseline model expects dict input
            prediction = int(state.model.predict(feature_dict))
            proba = state.model.predict_proba(feature_dict)
            probability = float(proba[1])  # Prob of class 1 (spike)
        else:
            # ML model expects DataFrame
            df = pd.DataFrame([feature_dict], columns=FEATURE_NAMES)
            prediction = int(state.model.predict(df)[0])
            probability = float(
                state.model.predict_proba(df)[0][1]
            )  # Prob of class 1 (spike)

        # Record prediction distribution
        class_label = "spike" if prediction == 1 else "normal"
        prediction_distribution.labels(
            class_label=class_label, model_version=MODEL_VERSION
        ).inc()

        # Record confidence distribution
        prediction_confidence.labels(prediction_class=class_label).observe(probability)

        # Record latency
        latency = time.time() - request_start
        predict_latency.labels(endpoint="/predict").observe(latency)
        api_latency.labels(endpoint="/predict", method="POST").observe(latency)

        # Record successful request
        request_counter.labels(endpoint="/predict", method="POST", status="200").inc()

        return PredictionResponse(
            prediction=prediction,
            probability=round(probability, 4),
            timestamp=datetime.utcnow().isoformat(),
            model_version=MODEL_VERSION,
        )

    except ValueError as e:
        predict_errors.labels(error_type="invalid_input").inc()
        request_counter.labels(endpoint="/predict", method="POST", status="400").inc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid input: {str(e)}",
        )
    except Exception as e:
        predict_errors.labels(error_type="internal_error").inc()
        request_counter.labels(endpoint="/predict", method="POST", status="500").inc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {str(e)}",
        )


@app.post(
    "/predict/batch",
    response_model=BatchPredictionResponse,
    tags=["Prediction"],
    summary="Make batch predictions",
    description="Predict volatility spikes for multiple feature sets",
)
async def predict_batch(batch: BatchFeatureInput):
    """
    Make batch predictions.

    Args:
        batch: Batch of input features

    Returns:
        BatchPredictionResponse: Batch prediction results
    """
    if not state.model_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not loaded. Service not ready.",
        )

    predictions = []

    for features in batch.features:
        try:
            result = await predict(features)
            predictions.append(result)
        except Exception as e:
            # Continue with other predictions even if one fails
            print(f"Warning: Prediction failed: {e}")

    return BatchPredictionResponse(predictions=predictions, count=len(predictions))


@app.get(
    "/metrics",
    response_class=PlainTextResponse,
    tags=["Monitoring"],
    summary="Prometheus metrics",
    description="Get Prometheus-formatted metrics for monitoring",
)
async def metrics():
    """
    Prometheus metrics endpoint.

    Returns:
        PlainTextResponse: Prometheus metrics
    """
    return generate_latest()


@app.get(
    "/",
    tags=["Information"],
    summary="Root endpoint",
    description="Welcome message and API information",
)
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Crypto Volatility Detection API",
        "version": API_VERSION,
        "status": "healthy" if state.model_loaded else "degraded",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "predict": "POST /predict",
            "batch_predict": "POST /predict/batch",
            "health": "GET /health",
            "version": "GET /version",
            "metrics": "GET /metrics",
        },
    }


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    # Run the API server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable auto-reload during development
        log_level="info",
    )
