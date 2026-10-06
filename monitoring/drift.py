"""Concept and Data Drift Detection using Population Stability Index (PSI) and Kolmogorov-Smirnov tests."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple
import numpy as np
from pydantic import BaseModel, Field
from scipy import stats


class DriftReport(BaseModel):
    feature_name: str
    psi_score: float
    ks_statistic: float
    ks_p_value: float
    drift_status: str  # STABLE, MODERATE_DRIFT, CRITICAL_DRIFT
    retraining_recommended: bool


class OverallDriftAssessment(BaseModel):
    overall_status: str
    total_features_evaluated: int
    features_in_drift: List[str]
    max_psi: float
    requires_retraining: bool
    feature_reports: Dict[str, DriftReport] = Field(default_factory=dict)


class DriftMonitor:
    """Monitors feature and prediction distribution stability between training baseline and live inference."""

    @staticmethod
    def calculate_psi(baseline: np.ndarray, current: np.ndarray, num_bins: int = 10) -> float:
        """Calculates Population Stability Index across quantile bins."""
        if len(baseline) < 5 or len(current) < 5:
            return 0.0

        # Create quantile bin edges from baseline
        quantiles = np.linspace(0, 100, num_bins + 1)
        bin_edges = np.percentile(baseline, quantiles)
        bin_edges = np.unique(bin_edges)

        if len(bin_edges) < 2:
            return 0.0

        # Ensure outer boundaries cover all values
        bin_edges[0] = -np.inf
        bin_edges[-1] = np.inf

        # Bin counts
        b_counts, _ = np.histogram(baseline, bins=bin_edges)
        c_counts, _ = np.histogram(current, bins=bin_edges)

        # Proportions with Laplace smoothing
        b_pct = (b_counts + 1e-4) / (len(baseline) + 1e-4 * len(b_counts))
        c_pct = (c_counts + 1e-4) / (len(current) + 1e-4 * len(c_counts))

        psi = np.sum((c_pct - b_pct) * np.log(c_pct / b_pct))
        return round(float(max(0.0, psi)), 4)

    def evaluate_feature_drift(
        self,
        baseline_X: np.ndarray,
        current_X: np.ndarray,
        feature_names: List[str],
    ) -> OverallDriftAssessment:
        reports: Dict[str, DriftReport] = {}
        drifted_features = []
        max_psi = 0.0

        for col_idx, name in enumerate(feature_names):
            b_col = baseline_X[:, col_idx]
            c_col = current_X[:, col_idx]

            psi = self.calculate_psi(b_col, c_col)
            ks_res = stats.ks_2samp(b_col, c_col)
            ks_stat = round(float(ks_res.statistic), 4)
            ks_p = float(ks_res.pvalue)

            if psi >= 0.25 or (ks_p < 0.01 and ks_stat > 0.35):
                status_str = "CRITICAL_DRIFT"
                retrain = True
                drifted_features.append(name)
            elif psi >= 0.10:
                status_str = "MODERATE_DRIFT"
                retrain = False
            else:
                status_str = "STABLE"
                retrain = False

            max_psi = max(max_psi, psi)
            reports[name] = DriftReport(
                feature_name=name,
                psi_score=psi,
                ks_statistic=ks_stat,
                ks_p_value=ks_p,
                drift_status=status_str,
                retraining_recommended=retrain,
            )

        overall = "CRITICAL_DRIFT" if len(drifted_features) > 0 else "STABLE"
        return OverallDriftAssessment(
            overall_status=overall,
            total_features_evaluated=len(feature_names),
            features_in_drift=drifted_features,
            max_psi=max_psi,
            requires_retraining=len(drifted_features) > 0,
            feature_reports=reports,
        )
