"""Investigation API routes for human-in-the-loop analyst decisions, alerts review, and audit trail."""

from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from api.app_state import AnalystDecision, AuditLogEntry, platform_state

router = APIRouter(prefix="/api/investigation", tags=["Analyst Investigation"])


class SubmitDecisionRequest(BaseModel):
    tx_id: str
    user_id: str
    amount: float
    analyst_id: str = "analyst_sarah_chen"
    decision: str = Field(..., description="One of: CONFIRM_FRAUD, FALSE_POSITIVE_APPROVE, ESCALATE_DISPUTE")
    notes: str = Field(..., min_length=3)
    original_risk_score: float = 0.0
    original_decision: str = "DECLINE"


@router.get("/alerts")
def get_pending_alerts(limit: int = Query(50, ge=1, le=150)):
    """Retrieves high-risk or flagged transactions awaiting human-in-the-loop analyst investigation."""
    if not platform_state.is_initialized:
        platform_state.initialize()

    alerts_list = list(platform_state.alerts)[:limit]
    return {
        "pending_count": len(alerts_list),
        "alerts": alerts_list,
    }


@router.get("/alert/{tx_id}")
def get_alert_detail(tx_id: str):
    """Retrieves deep investigation context for a specific alert, including 2-hop graph evidence and feature details."""
    if not platform_state.is_initialized:
        platform_state.initialize()

    # Search in alerts or recent transactions
    match = None
    for item in platform_state.recent_transactions:
        if item.get("tx_id") == tx_id:
            match = item
            break

    if not match:
        raise HTTPException(status_code=404, detail=f"Transaction '{tx_id}' not found in active cache.")

    # Retrieve 2-hop graph neighborhood for the user and device
    user_id = match.get("user_id")
    device_id = match.get("device_id")

    graph_evidence = platform_state.graph.get_2hop_neighborhood(user_id) if user_id else {}
    device_evidence = platform_state.graph.get_2hop_neighborhood(device_id) if device_id else {}

    return {
        "transaction": match,
        "user_neighborhood": graph_evidence,
        "device_neighborhood": device_evidence,
    }


@router.post("/decision", response_model=AnalystDecision)
def submit_analyst_decision(req: SubmitDecisionRequest) -> AnalystDecision:
    """Records a human analyst review decision, creating an indelible audit log entry and closing the alert."""
    if not platform_state.is_initialized:
        platform_state.initialize()

    valid_decisions = ["CONFIRM_FRAUD", "FALSE_POSITIVE_APPROVE", "ESCALATE_DISPUTE"]
    if req.decision not in valid_decisions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid decision '{req.decision}'. Must be one of: {valid_decisions}",
        )

    decision_record = platform_state.record_analyst_decision(
        tx_id=req.tx_id,
        user_id=req.user_id,
        amount=req.amount,
        analyst_id=req.analyst_id,
        decision=req.decision,
        notes=req.notes,
        original_risk_score=req.original_risk_score,
        original_decision=req.original_decision,
    )

    return decision_record


@router.get("/decisions")
def get_analyst_decisions_history(limit: int = Query(50, ge=1, le=200)):
    """Returns chronological log of human analyst investigation decisions."""
    decisions_list = list(platform_state.analyst_decisions)[:limit]
    return {
        "count": len(decisions_list),
        "decisions": [d.model_dump() for d in decisions_list],
    }


@router.get("/audit_log")
def get_system_audit_trail(limit: int = Query(100, ge=1, le=500)):
    """Returns comprehensive chronological audit trail of all platform events, scoring runs, attacks, and decisions."""
    logs_list = list(platform_state.audit_logs)[:limit]
    return {
        "count": len(logs_list),
        "audit_logs": [entry.model_dump() for entry in logs_list],
    }
