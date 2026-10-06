"""Cost-Sensitive Threshold Optimization and Decision Policy Engine."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
import numpy as np
from pydantic import BaseModel


class DecisionPolicy(BaseModel):
    challenge_threshold: float = 0.30
    decline_threshold: float = 0.75
    fp_cost: float = 15.0
    optimal_cost: float = 0.0


class CostSensitiveThresholdOptimizer:
    """Optimizes classification cutoffs to minimize total financial business loss (FP cost + FN fraud loss)."""

    def __init__(self, fp_cost: float = 15.0):
        self.fp_cost = fp_cost

    def optimize_threshold(
        self,
        y_val_true: np.ndarray,
        y_val_probs: np.ndarray,
        amounts: Optional[np.ndarray] = None,
    ) -> DecisionPolicy:
        if amounts is None:
            amounts = np.full_like(y_val_probs, 150.0)  # Default $150 average transaction amount

        best_cost = float("inf")
        best_threshold = 0.50

        # Scan candidate thresholds from 0.05 to 0.95
        candidates = np.linspace(0.05, 0.95, 37)
        for th in candidates:
            preds = (y_val_probs >= th).astype(int)
            fps = np.sum((preds == 1) & (y_val_true == 0))
            fns = (preds == 0) & (y_val_true == 1)

            fp_total_cost = float(fps) * self.fp_cost
            fn_total_cost = float(np.sum(amounts[fns]))
            total_cost = fp_total_cost + fn_total_cost

            if total_cost < best_cost:
                best_cost = total_cost
                best_threshold = float(th)

        # Set multi-tier thresholds: challenge at lower cutoff, hard decline at optimal/high cutoff
        challenge_th = round(max(0.15, best_threshold * 0.55), 4)
        decline_th = round(min(0.85, max(best_threshold, 0.65)), 4)

        return DecisionPolicy(
            challenge_threshold=challenge_th,
            decline_threshold=decline_th,
            fp_cost=self.fp_cost,
            optimal_cost=round(best_cost, 2),
        )

    @staticmethod
    def evaluate_decision(prob: float, policy: DecisionPolicy) -> str:
        """Assigns categorical decision: APPROVE, CHALLENGE, or DECLINE."""
        if prob >= policy.decline_threshold:
            return "DECLINE"
        elif prob >= policy.challenge_threshold:
            return "CHALLENGE"
        else:
            return "APPROVE"
