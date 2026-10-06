"""Monitoring API routes for concept drift, population stability index (PSI), and retraining triggers."""

from __future__ import annotations

import numpy as np
from fastapi import APIRouter
from pydantic import BaseModel, Field

from api.app_state import FEATURE_NAMES, platform_state

router = APIRouter(prefix="/api/monitoring", tags=["Monitoring & Drift"])


class SimulateDriftRequest(BaseModel):
    shift_feature: str = Field("amount", description="Feature to artificially shift (e.g., amount, implied_speed_kmh)")
    multiplier: float = Field(4.5, gt=1.0, description="Magnitude multiplier to inject severe distribution shift")


@router.get("/drift")
def get_drift_metrics():
    """Computes real-time Population Stability Index (PSI) and Kolmogorov-Smirnov test statistics against baseline."""
    if not platform_state.is_initialized:
        platform_state.initialize()

    # Gather feature vectors from recent transactions
    recent_txs = list(platform_state.recent_transactions)
    if len(recent_txs) < 20 and platform_state.X_train_ref is not None:
        curr_batch = platform_state.X_train_ref[:50] + np.random.normal(0, 0.05, size=platform_state.X_train_ref[:50].shape)
    else:
        vecs = []
        for tx in recent_txs[:100]:
            fv_dict = platform_state.scoring_engine.online_fs.get(f"tx:{tx.get('tx_id')}")
            if fv_dict:
                from feature_store.store import EnrichedFeatureVector
                fv = EnrichedFeatureVector(**fv_dict)
                vecs.append(fv.to_array())
        if len(vecs) >= 10:
            curr_batch = np.array(vecs, dtype=np.float32)
        else:
            curr_batch = platform_state.X_train_ref[:50]

    assessment = platform_state.drift_monitor.evaluate_feature_drift(
        baseline_X=platform_state.X_train_ref,
        current_X=curr_batch,
        feature_names=FEATURE_NAMES,
    )
    return assessment.model_dump()


@router.post("/simulate_drift")
def simulate_feature_drift(req: SimulateDriftRequest):
    """Artificially induces a sudden population shift to verify automated alarm triggers and retraining alerts."""
    if not platform_state.is_initialized:
        platform_state.initialize()

    base_batch = np.copy(platform_state.X_train_ref[:60])

    if req.shift_feature in FEATURE_NAMES:
        feat_idx = FEATURE_NAMES.index(req.shift_feature)
        base_batch[:, feat_idx] = base_batch[:, feat_idx] * req.multiplier + 250.0

    assessment = platform_state.drift_monitor.evaluate_feature_drift(
        baseline_X=platform_state.X_train_ref,
        current_X=base_batch,
        feature_names=FEATURE_NAMES,
    )

    platform_state._record_audit(
        event_type="DRIFT_INDUCED",
        details={
            "shifted_feature": req.shift_feature,
            "overall_status": assessment.overall_status,
            "max_psi": assessment.max_psi,
        },
    )

    return {
        "status": "drift_simulated",
        "shifted_feature": req.shift_feature,
        "report": assessment.model_dump(),
    }


@router.post("/retrain")
def trigger_model_retraining():
    """Executes the automated retraining pipeline with accumulated feedback labels and updates the champion model."""
    if not platform_state.is_initialized:
        platform_state.initialize()

    mature_labels = platform_state.retraining_pipeline.simulate_delayed_label_ingestion(days_elapsed=45)

    champ_model = platform_state.scoring_engine.models.get(
        platform_state.scoring_engine.champion_model_name,
        platform_state.scoring_engine.models.get("XGBoost")
    )

    event = platform_state.retraining_pipeline.execute_retraining_workflow(
        current_champion_model=champ_model,
        trigger_reason="MANUAL_ANALYST_TRIGGER",
    )

    platform_state._record_audit(
        event_type="RETRAINING_TRIGGERED",
        details=event.model_dump(),
    )

    return {
        "mature_chargeback_labels_ingested": mature_labels,
        "event": event.model_dump(),
    }
