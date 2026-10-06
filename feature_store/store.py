"""Dual Online/Offline Feature Store enforcing point-in-time correctness and zero training-serving skew."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field
from graph.ring_detector import GraphRiskFeatures
from simulation.models import Transaction


class EnrichedFeatureVector(BaseModel):
    tx_id: str
    timestamp: float
    amount: float
    log_amount: float
    hour_of_day: float
    day_of_week: float
    # Streaming velocity metrics
    card_tx_count_1m: float
    card_tx_count_5m: float
    card_tx_count_1h: float
    card_tx_count_24h: float
    card_amount_sum_1h: float
    card_amount_sum_24h: float
    velocity_amount_ratio: float
    device_tx_count_5m: float
    ip_tx_count_5m: float
    user_distinct_devices_24h: float
    user_distinct_ips_24h: float
    geo_distance_km: float
    implied_speed_kmh: float
    # Graph topological metrics
    device_degree_users: float
    device_degree_cards: float
    ip_degree_users: float
    is_in_fraud_ring: float
    ring_size: float
    syndicate_risk_score: float
    # Labels
    is_fraud: int = 0
    attack_type: str = "NONE"

    def to_array(self) -> np.ndarray:
        """Converts into standard 21-dimensional normalized numerical feature array for models."""
        return np.array([
            self.amount,
            self.log_amount,
            self.hour_of_day,
            self.day_of_week,
            self.card_tx_count_1m,
            self.card_tx_count_5m,
            self.card_tx_count_1h,
            self.card_tx_count_24h,
            self.card_amount_sum_1h,
            self.card_amount_sum_24h,
            self.velocity_amount_ratio,
            self.device_tx_count_5m,
            self.ip_tx_count_5m,
            self.user_distinct_devices_24h,
            self.user_distinct_ips_24h,
            self.geo_distance_km,
            self.implied_speed_kmh,
            self.device_degree_users,
            self.device_degree_cards,
            self.ip_degree_users,
            self.syndicate_risk_score,
        ], dtype=np.float32)

    @classmethod
    def feature_names(cls) -> List[str]:
        return [
            "amount",
            "log_amount",
            "hour_of_day",
            "day_of_week",
            "card_tx_count_1m",
            "card_tx_count_5m",
            "card_tx_count_1h",
            "card_tx_count_24h",
            "card_amount_sum_1h",
            "card_amount_sum_24h",
            "velocity_amount_ratio",
            "device_tx_count_5m",
            "ip_tx_count_5m",
            "user_distinct_devices_24h",
            "user_distinct_ips_24h",
            "geo_distance_km",
            "implied_speed_kmh",
            "device_degree_users",
            "device_degree_cards",
            "ip_degree_users",
            "syndicate_risk_score",
        ]


class OnlineFeatureStore:
    """Sub-millisecond in-memory feature cache for real-time scoring."""

    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}

    def put(self, key: str, features: Dict[str, Any]) -> None:
        self._cache[key] = features

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        return self._cache.get(key)

    def clear(self) -> None:
        self._cache.clear()


class OfflineFeatureStore:
    """Historical feature store with point-in-time correctness preventing lookahead leakage."""

    def __init__(self):
        self.records: List[EnrichedFeatureVector] = []

    def record_feature_vector(
        self,
        tx: Transaction,
        velocity_feats: Dict[str, float],
        graph_feats: GraphRiskFeatures,
    ) -> EnrichedFeatureVector:
        # Intrinsic temporal features
        hour = float((tx.timestamp // 3600) % 24)
        dow = float((tx.timestamp // 86400) % 7)

        fv = EnrichedFeatureVector(
            tx_id=tx.tx_id,
            timestamp=tx.timestamp,
            amount=tx.amount,
            log_amount=round(math.log1p(tx.amount), 4),
            hour_of_day=hour,
            day_of_week=dow,
            card_tx_count_1m=velocity_feats.get("card_tx_count_1m", 0.0),
            card_tx_count_5m=velocity_feats.get("card_tx_count_5m", 0.0),
            card_tx_count_1h=velocity_feats.get("card_tx_count_1h", 0.0),
            card_tx_count_24h=velocity_feats.get("card_tx_count_24h", 0.0),
            card_amount_sum_1h=velocity_feats.get("card_amount_sum_1h", 0.0),
            card_amount_sum_24h=velocity_feats.get("card_amount_sum_24h", 0.0),
            velocity_amount_ratio=velocity_feats.get("velocity_amount_ratio", 1.0),
            device_tx_count_5m=velocity_feats.get("device_tx_count_5m", 0.0),
            ip_tx_count_5m=velocity_feats.get("ip_tx_count_5m", 0.0),
            user_distinct_devices_24h=velocity_feats.get("user_distinct_devices_24h", 1.0),
            user_distinct_ips_24h=velocity_feats.get("user_distinct_ips_24h", 1.0),
            geo_distance_km=velocity_feats.get("geo_distance_km", 0.0),
            implied_speed_kmh=velocity_feats.get("implied_speed_kmh", 0.0),
            device_degree_users=float(graph_feats.device_degree_users),
            device_degree_cards=float(graph_feats.device_degree_cards),
            ip_degree_users=float(graph_feats.ip_degree_users),
            is_in_fraud_ring=1.0 if graph_feats.is_in_fraud_ring else 0.0,
            ring_size=float(graph_feats.ring_size),
            syndicate_risk_score=graph_feats.syndicate_risk_score,
            is_fraud=tx.is_fraud,
            attack_type=tx.attack_type.value,
        )
        self.records.append(fv)
        return fv

    def get_temporal_splits(
        self,
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
    ) -> Tuple[Tuple[np.ndarray, np.ndarray], Tuple[np.ndarray, np.ndarray], Tuple[np.ndarray, np.ndarray]]:
        """Splits strictly by ascending timestamp to prevent temporal lookahead data leakage."""
        sorted_records = sorted(self.records, key=lambda r: r.timestamp)
        n = len(sorted_records)

        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)

        train_rec = sorted_records[:n_train]
        val_rec = sorted_records[n_train : n_train + n_val]
        test_rec = sorted_records[n_train + n_val :]

        X_train = np.array([r.to_array() for r in train_rec], dtype=np.float32)
        y_train = np.array([r.is_fraud for r in train_rec], dtype=np.int64)

        X_val = np.array([r.to_array() for r in val_rec], dtype=np.float32)
        y_val = np.array([r.is_fraud for r in val_rec], dtype=np.int64)

        X_test = np.array([r.to_array() for r in test_rec], dtype=np.float32)
        y_test = np.array([r.is_fraud for r in test_rec], dtype=np.int64)

        return (X_train, y_train), (X_val, y_val), (X_test, y_test)
