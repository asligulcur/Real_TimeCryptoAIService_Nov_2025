"""
Unit tests for the rule-based baseline model (the rollback fallback).

Pure logic — no server, no sklearn, no model artifact required.
Run: pytest tests/test_baseline.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ml.baseline import BaselineVolatilityPredictor  # noqa: E402

CALM = {
    "volatility_30s": 0.001, "volatility_60s": 0.001,
    "return_60s": 0.0001, "intensity_60s": 5.0,
}
STRONG_SPIKE = {
    "volatility_30s": 0.08, "volatility_60s": 0.09,
    "return_60s": 0.03, "intensity_60s": 280.0,
}
# Volatility signal alone = weight 0.5, which is NOT > 0.5 → must stay 'normal'
VOL_ONLY = {
    "volatility_30s": 0.08, "volatility_60s": 0.09,
    "return_60s": 0.0001, "intensity_60s": 5.0,
}


def test_calm_market_predicts_normal():
    assert BaselineVolatilityPredictor().predict(CALM) == 0


def test_strong_signals_predict_spike():
    assert BaselineVolatilityPredictor().predict(STRONG_SPIKE) == 1


def test_volatility_signal_alone_is_below_threshold():
    # score == 0.5 exactly, and the rule requires score > 0.5, so no spike
    assert BaselineVolatilityPredictor().predict(VOL_ONLY) == 0


def test_missing_features_default_to_normal():
    assert BaselineVolatilityPredictor().predict({}) == 0


def test_predict_proba_is_valid_distribution():
    proba = BaselineVolatilityPredictor().predict_proba(STRONG_SPIKE)
    assert len(proba) == 2
    assert abs(float(proba[0]) + float(proba[1]) - 1.0) < 1e-6


def test_predict_proba_spike_prob_higher_for_spike_than_calm():
    m = BaselineVolatilityPredictor()
    assert float(m.predict_proba(STRONG_SPIKE)[1]) > float(m.predict_proba(CALM)[1])
