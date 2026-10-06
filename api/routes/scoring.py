"""Scoring API routes for sub-second real-time transaction risk evaluation."""

from __future__ import annotations

import time
import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.app_state import platform_state
from scoring.engine import ScoringResult
from simulation.models import Transaction

router = APIRouter(prefix="/api/score", tags=["Scoring Engine"])


class ScoreTransactionRequest(BaseModel):
    user_id: str
    card_id: str
    device_id: str
    ip_address: str
    merchant_id: str
    address_id: Optional[str] = None
    billing_address_id: Optional[str] = None
    amount: float = Field(..., gt=0.0)
    ip_lat: float = 40.7128
    ip_lon: float = -74.0060
    timestamp: Optional[float] = None
    tx_id: Optional[str] = None


class PolicyUpdateRequest(BaseModel):
    challenge_threshold: Optional[float] = None
    approve_threshold: Optional[float] = None
    decline_threshold: float = Field(..., ge=0.0, le=1.0)
    fp_cost: Optional[float] = None
    cost_false_positive: Optional[float] = None


@router.post("", response_model=ScoringResult)
def score_transaction(req: ScoreTransactionRequest) -> ScoringResult:
    """Scores an incoming transaction in sub-second latency with graph topology analysis and 8-model reasoning."""
    if not platform_state.is_initialized:
        platform_state.initialize()

    tx = Transaction(
        tx_id=req.tx_id or f"TX_{uuid.uuid4().hex[:10].upper()}",
        user_id=req.user_id,
        card_id=req.card_id,
        device_id=req.device_id,
        ip_address=req.ip_address,
        merchant_id=req.merchant_id,
        address_id=req.address_id or req.billing_address_id or "ADDR_000001",
        amount=req.amount,
        timestamp=req.timestamp or time.time(),
        is_fraud=0,
    )

    result = platform_state.scoring_engine.score_transaction(
        tx=tx, ip_lat=req.ip_lat, ip_lon=req.ip_lon
    )

    # Store in recent transactions and alerts buffer
    tx_dict = result.model_dump()
    tx_dict["attack_type"] = "API_SUBMITTED"
    tx_dict["card_id"] = req.card_id
    tx_dict["device_id"] = req.device_id
    tx_dict["ip_address"] = req.ip_address
    tx_dict["merchant_id"] = req.merchant_id

    platform_state.recent_transactions.appendleft(tx_dict)
    if result.decision in ["CHALLENGE", "DECLINE"]:
        platform_state.alerts.appendleft(tx_dict)

    return result


@router.get("/policy")
def get_scoring_policy():
    """Returns active decision policy thresholds and cost parameters."""
    policy = platform_state.scoring_engine.policy
    return {
        "challenge_threshold": policy.challenge_threshold,
        "approve_threshold": policy.challenge_threshold,
        "decline_threshold": policy.decline_threshold,
        "fp_cost": policy.fp_cost,
        "cost_false_positive": policy.fp_cost,
        "champion_model": platform_state.scoring_engine.champion_model_name,
        "registered_models": list(platform_state.scoring_engine.models.keys()),
    }


@router.put("/policy")
def update_scoring_policy(req: PolicyUpdateRequest):
    """Dynamically updates decision policy thresholds and cost weights."""
    chal_th = req.challenge_threshold if req.challenge_threshold is not None else req.approve_threshold
    if chal_th is None:
        chal_th = platform_state.scoring_engine.policy.challenge_threshold
    fp_c = req.fp_cost if req.fp_cost is not None else req.cost_false_positive
    if fp_c is None:
        fp_c = platform_state.scoring_engine.policy.fp_cost

    if chal_th >= req.decline_threshold:
        raise HTTPException(
            status_code=400,
            detail="challenge_threshold must be strictly less than decline_threshold",
        )

    platform_state.scoring_engine.policy.challenge_threshold = chal_th
    platform_state.scoring_engine.policy.decline_threshold = req.decline_threshold
    platform_state.scoring_engine.policy.fp_cost = fp_c

    platform_state._record_audit(
        event_type="POLICY_UPDATE",
        details={
            "challenge_threshold": chal_th,
            "decline_threshold": req.decline_threshold,
            "fp_cost": fp_c,
        },
    )

    return {
        "status": "updated",
        "policy": {
            "challenge_threshold": chal_th,
            "approve_threshold": chal_th,
            "decline_threshold": req.decline_threshold,
            "fp_cost": fp_c,
            "cost_false_positive": fp_c,
        },
    }
