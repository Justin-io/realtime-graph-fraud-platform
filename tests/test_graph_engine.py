"""Unit tests for HeterogeneousEntityGraph and FraudRingDetector."""

import pytest
from simulation.generator import MultiEntitySimulator
from simulation.attacks import AdversarialAttackInjector
from simulation.models import AttackType
from graph.entity_graph import HeterogeneousEntityGraph
from graph.ring_detector import FraudRingDetector


def test_entity_graph_construction_and_neighborhoods():
    sim = MultiEntitySimulator(seed=42)
    sim.generate_entities(n_users=50, n_cards=80, n_devices=60, n_ips=40, n_merchants=10, n_addresses=50)
    txs = sim.generate_benign_transactions(n_transactions=100)

    graph = HeterogeneousEntityGraph()
    for tx in txs:
        graph.add_transaction(tx)

    first_tx = txs[0]
    # Verify nodes exist
    assert first_tx.user_id in graph.node_to_idx
    assert first_tx.card_id in graph.node_to_idx
    assert first_tx.device_id in graph.node_to_idx

    # Check 1-hop neighbors of user
    neighbors_1hop = graph.get_1hop_neighbors(first_tx.user_id)
    assert len(neighbors_1hop) > 0
    assert first_tx.card_id in neighbors_1hop or first_tx.device_id in neighbors_1hop

    # Check 2-hop neighborhood extraction
    neighborhood_2hop = graph.get_2hop_neighborhood(first_tx.user_id)
    assert len(neighborhood_2hop["nodes"]) > 0
    assert len(neighborhood_2hop["edges"]) > 0

    # Check PyG export
    pyg_data = graph.to_pyg_data()
    assert pyg_data.x.shape[0] == len(graph.node_to_idx)
    assert pyg_data.x.shape[1] == 8
    assert pyg_data.edge_index.shape[0] == 2
    assert pyg_data.edge_index.shape[1] > 0


def test_fraud_ring_detection_on_adversarial_stream():
    sim = MultiEntitySimulator(seed=42)
    sim.generate_entities(n_users=100, n_cards=150, n_devices=100, n_ips=80, n_merchants=20, n_addresses=100)
    benign_txs = sim.generate_benign_transactions(n_transactions=500)
    injector = AdversarialAttackInjector(sim, seed=42)
    stream = injector.inject_all_attacks(benign_txs, fraud_ratio=0.10)

    graph = HeterogeneousEntityGraph()
    detector = FraudRingDetector(graph)

    for tx in stream:
        graph.add_transaction(tx)

    # Detect all active rings
    rings = detector.detect_active_fraud_rings(min_users_threshold=3)
    assert len(rings) > 0

    # Check feature extraction for a device-sharing fraud transaction
    ring_tx = next(t for t in stream if t.attack_type == AttackType.DEVICE_SHARING_RING)
    features = detector.extract_graph_features(ring_tx)

    assert features.is_in_fraud_ring
    assert features.device_degree_users >= 3
    assert features.syndicate_risk_score > 0.30
    assert any("Device-Sharing" in r for r in features.risk_factors)
