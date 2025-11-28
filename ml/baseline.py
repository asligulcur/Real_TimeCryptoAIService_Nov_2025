"""
Simple baseline model for crypto volatility detection.

This baseline model uses simple rule-based logic as a fallback when the 
ML model is experiencing issues or during rollback scenarios.

Author: CMU Heinz OAI Team
Date: November 2025
"""

import numpy as np
from typing import Dict


class BaselineVolatilityPredictor:
    """
    Rule-based baseline model for volatility spike prediction.
    
    This model uses simple heuristics based on domain knowledge:
    - High volatility (> 0.03) → likely spike
    - Large price movements (return > 0.01) → likely spike
    - High trading intensity (> 50) → likely spike
    
    Combining these signals provides a reasonable baseline.
    """
    
    def __init__(self):
        """Initialize baseline model with thresholds."""
        self.model_version = "baseline-1.0"
        
        # Thresholds based on domain knowledge
        self.volatility_threshold = 0.03
        self.return_threshold = 0.01
        self.intensity_threshold = 50
        
        # Weights for combining signals
        self.volatility_weight = 0.5
        self.return_weight = 0.3
        self.intensity_weight = 0.2
    
    def predict(self, features: Dict[str, float]) -> int:
        """
        Predict volatility spike using rule-based logic.
        
        Args:
            features: Dictionary of feature values
            
        Returns:
            0 (normal) or 1 (spike)
        """
        # Extract key features
        volatility_30s = features.get('volatility_30s', 0)
        volatility_60s = features.get('volatility_60s', 0)
        return_60s = abs(features.get('return_60s', 0))
        intensity_60s = features.get('intensity_60s', 0)
        
        # Calculate weighted score
        score = 0.0
        
        # Volatility signal (average of 30s and 60s)
        avg_volatility = (volatility_30s + volatility_60s) / 2
        if avg_volatility > self.volatility_threshold:
            score += self.volatility_weight
        
        # Return signal (large price movement)
        if return_60s > self.return_threshold:
            score += self.return_weight
        
        # Intensity signal (high trading activity)
        if intensity_60s > self.intensity_threshold:
            score += self.intensity_weight
        
        # Threshold: if score > 0.5, predict spike
        return 1 if score > 0.5 else 0
    
    def predict_proba(self, features: Dict[str, float]) -> np.ndarray:
        """
        Return probability estimates.
        
        Args:
            features: Dictionary of feature values
            
        Returns:
            Array of [prob_normal, prob_spike]
        """
        # Extract key features
        volatility_30s = features.get('volatility_30s', 0)
        volatility_60s = features.get('volatility_60s', 0)
        return_60s = abs(features.get('return_60s', 0))
        intensity_60s = features.get('intensity_60s', 0)
        
        # Calculate weighted score (0 to 1)
        score = 0.0
        
        avg_volatility = (volatility_30s + volatility_60s) / 2
        if avg_volatility > self.volatility_threshold:
            score += self.volatility_weight
        
        if return_60s > self.return_threshold:
            score += self.return_weight
        
        if intensity_60s > self.intensity_threshold:
            score += self.intensity_weight
        
        # Return probabilities
        prob_spike = min(score, 1.0)
        prob_normal = 1.0 - prob_spike
        
        return np.array([prob_normal, prob_spike])
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Return feature importance (weights)."""
        return {
            'volatility': self.volatility_weight,
            'return': self.return_weight,
            'intensity': self.intensity_weight,
        }


def load_baseline_model():
    """Load the baseline model (just instantiate it)."""
    return BaselineVolatilityPredictor()


if __name__ == "__main__":
    # Test the baseline model
    print("Testing Baseline Volatility Predictor")
    print("=" * 50)
    
    model = BaselineVolatilityPredictor()
    
    # Test case 1: Normal market conditions
    normal_features = {
        'volatility_30s': 0.01,
        'volatility_60s': 0.015,
        'return_60s': 0.002,
        'intensity_60s': 20,
    }
    
    pred = model.predict(normal_features)
    proba = model.predict_proba(normal_features)
    print(f"\nTest 1 - Normal conditions:")
    print(f"  Prediction: {pred} (0=normal, 1=spike)")
    print(f"  Probability: {proba[1]:.2%}")
    
    # Test case 2: High volatility spike
    spike_features = {
        'volatility_30s': 0.045,
        'volatility_60s': 0.05,
        'return_60s': 0.015,
        'intensity_60s': 75,
    }
    
    pred = model.predict(spike_features)
    proba = model.predict_proba(spike_features)
    print(f"\nTest 2 - Volatility spike:")
    print(f"  Prediction: {pred} (0=normal, 1=spike)")
    print(f"  Probability: {proba[1]:.2%}")
    
    # Test case 3: Borderline case
    borderline_features = {
        'volatility_30s': 0.025,
        'volatility_60s': 0.028,
        'return_60s': 0.008,
        'intensity_60s': 45,
    }
    
    pred = model.predict(borderline_features)
    proba = model.predict_proba(borderline_features)
    print(f"\nTest 3 - Borderline case:")
    print(f"  Prediction: {pred} (0=normal, 1=spike)")
    print(f"  Probability: {proba[1]:.2%}")
    
    print("\n" + "=" * 50)
    print("✅ Baseline model working correctly")
