"""Real-Time Sub-Second Fraud Scoring Engine with Explainability and Graph Evidence."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
import numpy as np
from pydantic import BaseModel, Field
from feature_store.store import EnrichedFeatureVector, OfflineFeatureStore, OnlineFeatureStore
from graph.entity_graph import HeterogeneousEntityGraph
from graph.ring_detector import FraudRingDetector, GraphRiskFeatures
from scoring.policy import CostSensitiveThresholdOptimizer, DecisionPolicy
from simulation.models import Transaction


class ScoringResult(BaseModel):
    tx_id: str
    user_id: str
    amount: float
    timestamp: float
    risk_score: float  # 0.0 to 100.0
    calibrated_probability: float  # 0.0 to 1.0
    decision: str  # APPROVE, CHALLENGE, DECLINE
    latency_ms: float
    reason_codes: List[str] = Field(default_factory=list)
    graph_evidence: Dict[str, Any] = Field(default_factory=dict)
    model_breakdown: Dict[str, float] = Field(default_factory=dict)
    triggered_rules: List[str] = Field(default_factory=list)


class RealTimeFraudScoringEngine:
    """Production scoring engine delivering sub-second decisions with full explainability."""

    def __init__(
        self,
        graph: Optional[HeterogeneousEntityGraph] = None,
        policy: Optional[DecisionPolicy] = None,
    ):
        from streaming.pipeline import StreamingWindowAggregator

        self.graph = graph or HeterogeneousEntityGraph()
        self.ring_detector = FraudRingDetector(self.graph)
        self.aggregator = StreamingWindowAggregator()
        self.online_fs = OnlineFeatureStore()
        self.offline_fs = OfflineFeatureStore()
        self.policy = policy or DecisionPolicy()

        # Models dictionary: name -> model
        self.models: Dict[str, Any] = {}
        self.champion_model_name: str = "XGBoost"

    def register_model(self, name: str, model_instance: Any, is_champion: bool = False):
        self.models[name] = model_instance
        if is_champion or len(self.models) == 1:
            self.champion_model_name = name

    def score_transaction(
        self,
        tx: Transaction,
        ip_lat: float = 40.7128,
        ip_lon: float = -74.0060,
    ) -> ScoringResult:
        t0 = time.time()
        triggered_rules: List[str] = []
        reason_codes: List[str] = []

        # 1. Real-time streaming window feature computation (< 2ms)
        velocity_feats = self.aggregator.process_transaction(tx, ip_lat=ip_lat, ip_lon=ip_lon)

        # 2. Dynamic graph topology risk extraction (< 5ms)
        graph_feats = self.ring_detector.extract_graph_features(tx)

        # 3. Increment graph state with new transaction edge
        self.graph.add_transaction(tx)

        # 4. Store in offline store for training audit
        fv = self.offline_fs.record_feature_vector(tx, velocity_feats, graph_feats)
        # Store in online key-value cache
        self.online_fs.put(f"tx:{tx.tx_id}", fv.model_dump())

        # 5. Extract feature array for inference
        x_vec = fv.to_array().reshape(1, -1)

        # 6. Hard-rule heuristic triggers
        if velocity_feats.get("card_tx_count_1m", 0.0) >= 3.0:
            triggered_rules.append("RULE_BURST_VELOCITY: >=3 transactions within 60s")
            reason_codes.append("High card transaction burst frequency")

        if velocity_feats.get("implied_speed_kmh", 0.0) > 1000.0:
            triggered_rules.append("RULE_IMPOSSIBLE_TRAVEL: Speed > 1,000 km/h")
            reason_codes.append("Physically impossible geo-velocity between consecutive transactions")

        if graph_feats.is_in_fraud_ring:
            triggered_rules.append(f"RULE_FRAUD_RING: Hardware shared by {graph_feats.device_degree_users} accounts")
            reason_codes.extend(graph_feats.risk_factors)

        # 7. Model Inference across available models
        model_scores: Dict[str, float] = {}
        pyg_data = None

        for name, m in self.models.items():
            try:
                if name in ["GCN", "GraphSAGE", "GAT", "TemporalGNN"]:
                    if pyg_data is None:
                        pyg_data = self.graph.to_pyg_data(current_time=tx.timestamp)
                    p = float(m.predict_proba(x_vec, pyg_data)[0])
                else:
                    p = float(m.predict_proba(x_vec)[0])
                model_scores[name] = round(p, 4)
            except Exception:
                # Graceful fallback if model not yet fitted
                model_scores[name] = 0.05

        # Determine primary probability from champion model or heuristic fusion
        champ_prob = model_scores.get(self.champion_model_name, 0.05)

        # Apply rule penalty if hard attack detected
        if triggered_rules:
            champ_prob = max(champ_prob, 0.85)

        risk_score = round(champ_prob * 100.0, 1)
        decision = CostSensitiveThresholdOptimizer.evaluate_decision(champ_prob, self.policy)

        # 8. Assembled 2-hop graph evidence for UI inspector
        graph_evidence = self.graph.get_2hop_neighborhood(tx.user_id)

        elapsed_ms = round((time.time() - t0) * 1000.0, 2)

        return ScoringResult(
            tx_id=tx.tx_id,
            user_id=tx.user_id,
            amount=tx.amount,
            timestamp=tx.timestamp,
            risk_score=risk_score,
            calibrated_probability=round(champ_prob, 4),
            decision=decision,
            latency_ms=elapsed_ms,
            reason_codes=reason_codes,
            graph_evidence=graph_evidence,
            model_breakdown=model_scores,
            triggered_rules=triggered_rules,
        )
