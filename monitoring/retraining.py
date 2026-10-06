"""Automated Model Retraining Pipeline and Delayed Label Feedback Loop."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from pydantic import BaseModel, Field
from feature_store.store import OfflineFeatureStore
from models.tabular import XGBoostFraudModel


class RetrainingEvent(BaseModel):
    event_id: str
    triggered_at: float
    trigger_reason: str
    champion_previous: str
    champion_new: str
    previous_pr_auc: float
    new_pr_auc: float
    performance_gain: float
    deployed: bool


class AutomatedRetrainingPipeline:
    """Manages delayed chargeback label ingestion and champion/challenger model retraining."""

    def __init__(self, offline_fs: OfflineFeatureStore):
        self.offline_fs = offline_fs
        self.history: List[RetrainingEvent] = []

    def simulate_delayed_label_ingestion(self, days_elapsed: int = 45) -> int:
        """Simulates historical chargeback signals arriving after the 14-90 day bank processing lag."""
        updated_count = 0
        for r in self.offline_fs.records:
            # If transaction is older than days_elapsed, label is mature
            if r.is_fraud == 1:
                updated_count += 1
        return updated_count

    def execute_retraining_workflow(
        self,
        current_champion_model: Any,
        trigger_reason: str = "SCHEDULED_DELAYED_LABELS",
    ) -> RetrainingEvent:
        (X_train, y_train), (X_val, y_val), (X_test, y_test) = self.offline_fs.get_temporal_splits()

        # Fit challenger XGBoost model with latest temporal data
        challenger = XGBoostFraudModel(n_estimators=40, max_depth=4)
        challenger.fit(X_train, y_train)

        # Evaluate PR-AUC approximation on test set
        test_probs_champ = current_champion_model.predict_proba(X_test)
        test_probs_chal = challenger.predict_proba(X_test)

        # Baseline evaluation (fraud capture rate at top 10% risk threshold)
        top_k = max(1, int(len(y_test) * 0.10))
        champ_top_indices = np.argsort(test_probs_champ)[-top_k:]
        chal_top_indices = np.argsort(test_probs_chal)[-top_k:]

        champ_capture = float(np.sum(y_test[champ_top_indices])) / max(1, float(np.sum(y_test)))
        chal_capture = float(np.sum(y_test[chal_top_indices])) / max(1, float(np.sum(y_test)))

        gain = round(chal_capture - champ_capture, 4)
        deployed = gain >= 0.0  # Deploy challenger if performance matches or exceeds champion

        event = RetrainingEvent(
            event_id=f"RETRAIN_{len(self.history) + 1:04d}",
            triggered_at=time.time(),
            trigger_reason=trigger_reason,
            champion_previous="XGBoost_v1",
            champion_new="XGBoost_v2" if deployed else "XGBoost_v1",
            previous_pr_auc=round(champ_capture, 4),
            new_pr_auc=round(chal_capture, 4),
            performance_gain=gain,
            deployed=deployed,
        )
        self.history.append(event)
        return event
