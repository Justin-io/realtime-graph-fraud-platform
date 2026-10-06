"""Streaming Ingestion Pipeline and Windowed Feature Aggregator with Kafka-compatible semantics."""

from __future__ import annotations

import collections
import math
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple
from simulation.models import Transaction


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance in kilometers between two geo coordinates."""
    r = 6371.0  # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


class StreamingWindowAggregator:
    """Computes tumbling and sliding window velocity features with strict point-in-time correctness."""

    def __init__(self):
        # Sliding event deques: key -> Deque[(timestamp, amount, extra)]
        self.card_history: Dict[str, Deque[Tuple[float, float]]] = collections.defaultdict(collections.deque)
        self.user_history: Dict[str, Deque[Tuple[float, float, str, str, float, float]]] = collections.defaultdict(collections.deque)
        self.device_history: Dict[str, Deque[Tuple[float, float]]] = collections.defaultdict(collections.deque)
        self.ip_history: Dict[str, Deque[Tuple[float, float]]] = collections.defaultdict(collections.deque)

    def _prune(self, dq: Deque, current_ts: float, max_window_sec: float = 86400.0 * 7):
        cutoff = current_ts - max_window_sec
        while dq and dq[0][0] < cutoff:
            dq.popleft()

    def process_transaction(
        self,
        tx: Transaction,
        ip_lat: float = 40.7128,
        ip_lon: float = -74.0060,
    ) -> Dict[str, float]:
        """Computes streaming velocity metrics for the current transaction prior to state ingestion."""
        t = tx.timestamp
        amt = tx.amount

        # Prune older than 7 days
        self._prune(self.card_history[tx.card_id], t, 86400.0 * 7)
        self._prune(self.user_history[tx.user_id], t, 86400.0 * 7)
        self._prune(self.device_history[tx.device_id], t, 3600.0)
        self._prune(self.ip_history[tx.ip_address], t, 3600.0)

        # 1. Card Velocity Windows
        c_dq = self.card_history[tx.card_id]
        card_cnt_1m = sum(1 for (ts, _) in c_dq if t - ts <= 60.0)
        card_cnt_5m = sum(1 for (ts, _) in c_dq if t - ts <= 300.0)
        card_cnt_1h = sum(1 for (ts, _) in c_dq if t - ts <= 3600.0)
        card_cnt_24h = sum(1 for (ts, _) in c_dq if t - ts <= 86400.0)

        card_amt_1h = sum(a for (ts, a) in c_dq if t - ts <= 3600.0)
        card_amt_24h = sum(a for (ts, a) in c_dq if t - ts <= 86400.0)
        avg_amt_24h = (card_amt_24h / max(1, card_cnt_24h)) if card_cnt_24h > 0 else amt
        velocity_amt_ratio = round(amt / max(1.0, avg_amt_24h), 4)

        # 2. Device & IP Velocity
        dev_cnt_5m = sum(1 for (ts, _) in self.device_history[tx.device_id] if t - ts <= 300.0)
        ip_cnt_5m = sum(1 for (ts, _) in self.ip_history[tx.ip_address] if t - ts <= 300.0)

        # 3. User Multi-Entity Diversity & Geo-Velocity (Impossible Travel)
        u_dq = self.user_history[tx.user_id]
        devices_24h = len({d for (ts, _, d, _, _, _) in u_dq if t - ts <= 86400.0} | {tx.device_id})
        ips_24h = len({ip for (ts, _, _, ip, _, _) in u_dq if t - ts <= 86400.0} | {tx.ip_address})

        geo_dist_km = 0.0
        speed_kmh = 0.0
        if u_dq:
            last_ts, _, _, _, last_lat, last_lon = u_dq[-1]
            time_diff_hours = max(0.001, (t - last_ts) / 3600.0)
            geo_dist_km = haversine_distance(last_lat, last_lon, ip_lat, ip_lon)
            speed_kmh = round(geo_dist_km / time_diff_hours, 2)

        # Update in-memory state with current transaction
        self.card_history[tx.card_id].append((t, amt))
        self.user_history[tx.user_id].append((t, amt, tx.device_id, tx.ip_address, ip_lat, ip_lon))
        self.device_history[tx.device_id].append((t, amt))
        self.ip_history[tx.ip_address].append((t, amt))

        return {
            "card_tx_count_1m": float(card_cnt_1m),
            "card_tx_count_5m": float(card_cnt_5m),
            "card_tx_count_1h": float(card_cnt_1h),
            "card_tx_count_24h": float(card_cnt_24h),
            "card_amount_sum_1h": round(card_amt_1h, 2),
            "card_amount_sum_24h": round(card_amt_24h, 2),
            "velocity_amount_ratio": velocity_amt_ratio,
            "device_tx_count_5m": float(dev_cnt_5m),
            "ip_tx_count_5m": float(ip_cnt_5m),
            "user_distinct_devices_24h": float(devices_24h),
            "user_distinct_ips_24h": float(ips_24h),
            "geo_distance_km": round(geo_dist_km, 2),
            "implied_speed_kmh": round(speed_kmh, 2),
        }
