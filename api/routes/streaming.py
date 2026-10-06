"""Streaming API routes delivering Server-Sent Events (SSE) for live transaction monitoring."""

from __future__ import annotations

import asyncio
import json
from typing import Optional
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from api.app_state import platform_state

router = APIRouter(prefix="/api/stream", tags=["Streaming Pipeline"])


class AttackInjectionRequest(BaseModel):
    attack_type: str = Field(
        ...,
        description="One of CARD_TESTING, FRAUD_RING, IMPOSSIBLE_TRAVEL, ACCOUNT_TAKEOVER, IP_ROTATION_BOTNET, MERCHANT_COLLUSION",
    )
    burst_size: int = Field(10, ge=1, le=50)


@router.get("")
async def sse_transaction_stream(
    delay_ms: int = Query(750, ge=100, le=5000, description="Delay between events in ms")
):
    """Server-Sent Events (SSE) stream delivering real-time scored transactions to the analyst console."""
    if not platform_state.is_initialized:
        platform_state.initialize()

    async def event_generator():
        delay_sec = delay_ms / 1000.0
        while True:
            try:
                # Generate next transaction and score synchronously
                score_res, attack_tag = platform_state.generate_and_score_next()
                payload = score_res.model_dump()
                payload["attack_type"] = attack_tag or "BENIGN"

                yield f"data: {json.dumps(payload)}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

            await asyncio.sleep(delay_sec)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/inject")
def inject_adversarial_attack(req: AttackInjectionRequest):
    """Injects simulated attack bursts (fraud ring, impossible travel, card testing) into the live stream."""
    if not platform_state.is_initialized:
        platform_state.initialize()

    injected_count = platform_state.inject_attack_scenario(
        attack_name=req.attack_type, burst_size=req.burst_size
    )

    return {
        "status": "injected",
        "attack_type": req.attack_type,
        "count": injected_count,
        "queue_depth": len(platform_state.pending_attack_stream),
    }


@router.get("/recent")
def get_recent_transactions(limit: int = Query(50, ge=5, le=200)):
    """Returns the most recent scored transactions for instant dashboard population."""
    recent_list = list(platform_state.recent_transactions)[:limit]
    return {
        "count": len(recent_list),
        "transactions": recent_list,
    }
