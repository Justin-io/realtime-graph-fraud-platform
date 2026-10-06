"""Graph-based Fraud Ring and Topology Analysis Engine."""

from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple
import networkx as nx
from pydantic import BaseModel, Field
from graph.entity_graph import HeterogeneousEntityGraph
from simulation.models import Transaction


class GraphRiskFeatures(BaseModel):
    device_degree_users: int
    device_degree_cards: int
    ip_degree_users: int
    is_in_fraud_ring: bool
    ring_size: int
    syndicate_risk_score: float
    risk_factors: List[str] = Field(default_factory=list)


class FraudRing(BaseModel):
    ring_id: str
    member_count: int
    hub_entity_id: str
    hub_entity_type: str
    member_user_ids: List[str]
    member_card_ids: List[str]
    risk_level: str  # HIGH, CRITICAL


class FraudRingDetector:
    """Detects syndicated carding rings, shared hardware hubs, and circular transaction graphs."""

    def __init__(self, graph: HeterogeneousEntityGraph):
        self.graph = graph

    def extract_graph_features(self, tx: Transaction) -> GraphRiskFeatures:
        """Computes topological risk features for a candidate transaction in sub-second time."""
        nx_g = self.graph.nx_graph
        risk_factors: List[str] = []

        # 1. Device degree (distinct users & cards linked to device)
        device_users = set()
        device_cards = set()
        if tx.device_id in nx_g:
            # Users using device
            device_users = set(nx_g.predecessors(tx.device_id))
            # Cards linked to those users
            for u in device_users:
                if u in nx_g:
                    device_cards.update(set(nx_g.successors(u)))

        dev_user_deg = len(device_users)
        dev_card_deg = len(device_cards)

        # 2. IP degree (distinct users connecting through IP)
        ip_users = set()
        if tx.ip_address in nx_g:
            devices_on_ip = set(nx_g.predecessors(tx.ip_address))
            for d in devices_on_ip:
                if d in nx_g:
                    ip_users.update(set(nx_g.predecessors(d)))
        ip_user_deg = len(ip_users)

        # 3. Ring detection logic
        is_ring = False
        ring_size = 1
        syndicate_score = 0.05

        if dev_user_deg >= 3:
            is_ring = True
            ring_size = max(ring_size, dev_user_deg + dev_card_deg)
            syndicate_score += min(0.50, dev_user_deg * 0.12)
            risk_factors.append(f"Device-Sharing Hub: Hardware fingerprint shared by {dev_user_deg} distinct user accounts")

        if dev_card_deg >= 4:
            is_ring = True
            syndicate_score += 0.25
            risk_factors.append(f"Card Testing Syndicate: Single device linked to {dev_card_deg} distinct payment cards")

        if ip_user_deg >= 5:
            is_ring = True
            ring_size = max(ring_size, ip_user_deg)
            syndicate_score += min(0.30, ip_user_deg * 0.05)
            risk_factors.append(f"IP Proxy Farm: Shared network node connecting {ip_user_deg} distinct accounts")

        syndicate_score = round(min(1.0, syndicate_score), 4)

        return GraphRiskFeatures(
            device_degree_users=dev_user_deg,
            device_degree_cards=dev_card_deg,
            ip_degree_users=ip_user_deg,
            is_in_fraud_ring=is_ring,
            ring_size=ring_size,
            syndicate_risk_score=syndicate_score,
            risk_factors=risk_factors,
        )

    def detect_active_fraud_rings(self, min_users_threshold: int = 3) -> List[FraudRing]:
        """Discovers all active syndicated fraud rings across the full graph topology."""
        nx_g = self.graph.nx_graph
        rings: List[FraudRing] = []
        ring_counter = 1

        # Find high-degree device hubs
        for node, data in nx_g.nodes(data=True):
            if data.get("type") == "Device":
                users_on_dev = list(set(nx_g.predecessors(node)))
                if len(users_on_dev) >= min_users_threshold:
                    cards_on_dev = set()
                    for u in users_on_dev:
                        cards_on_dev.update(set(nx_g.successors(u)))

                    rings.append(
                        FraudRing(
                            ring_id=f"RING_{ring_counter:04d}",
                            member_count=len(users_on_dev) + len(cards_on_dev),
                            hub_entity_id=node,
                            hub_entity_type="Device",
                            member_user_ids=users_on_dev,
                            member_card_ids=list(cards_on_dev),
                            risk_level="CRITICAL" if len(users_on_dev) >= 5 else "HIGH",
                        )
                    )
                    ring_counter += 1

        return rings
