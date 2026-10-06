"""Interpretable Tabular Baselines: Logistic Regression and XGBoost with probability calibration."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
import xgboost as xgb


class LogisticRegressionFraudModel:
    """Interpretable L2-penalized linear baseline with probability calibration."""

    def __init__(self, c_param: float = 1.0):
        self.c_param = c_param
        self.scaler = StandardScaler()
        self.base_model = LogisticRegression(
            C=c_param,
            max_iter=1000,
            class_weight="balanced",
            random_state=42,
        )
        self.calibrated_model: Optional[CalibratedClassifierCV] = None
        self.is_fitted = False

    def fit(self, X: np.ndarray, y: np.ndarray) -> LogisticRegressionFraudModel:
        X_scaled = self.scaler.fit_transform(X)
        # Fit calibrated classifier with sigmoid (Platt scaling)
        self.calibrated_model = CalibratedClassifierCV(estimator=self.base_model, method="sigmoid", cv=3)
        self.calibrated_model.fit(X_scaled, y)
        self.is_fitted = True
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before predict_proba.")
        X_scaled = self.scaler.transform(X)
        probs = self.calibrated_model.predict_proba(X_scaled)
        return probs[:, 1]  # Return P(Fraud)

    def get_feature_weights(self, feature_names: List[str]) -> Dict[str, float]:
        """Returns normalized feature weights from underlying linear model."""
        if not self.is_fitted:
            return {}
        # Extract underlying estimators
        first_est = self.calibrated_model.calibrated_classifiers_[0].estimator
        coefs = first_est.coef_[0]
        return {name: round(float(w), 4) for name, w in zip(feature_names, coefs)}


class XGBoostFraudModel:
    """Non-linear gradient boosted tree champion with class-imbalance weighting."""

    def __init__(self, n_estimators: int = 100, max_depth: int = 5, learning_rate: float = 0.08):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.model: Optional[xgb.XGBClassifier] = None
        self.is_fitted = False

    def fit(self, X: np.ndarray, y: np.ndarray) -> XGBoostFraudModel:
        # Calculate scale_pos_weight = count(negative) / count(positive)
        n_pos = max(1, int(np.sum(y == 1)))
        n_neg = int(np.sum(y == 0))
        scale_weight = float(n_neg) / float(n_pos)

        self.model = xgb.XGBClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            scale_pos_weight=scale_weight,
            eval_metric="logloss",
            random_state=42,
            n_jobs=2,
        )
        self.model.fit(X, y)
        self.is_fitted = True
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before predict_proba.")
        probs = self.model.predict_proba(X)
        return probs[:, 1]

    def get_feature_importances(self, feature_names: List[str]) -> Dict[str, float]:
        if not self.is_fitted:
            return {}
        importances = self.model.feature_importances_
        return {name: round(float(imp), 4) for name, imp in zip(feature_names, importances)}
