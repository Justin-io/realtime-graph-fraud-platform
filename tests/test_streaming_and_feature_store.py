"""Unit tests for streaming window aggregator and dual feature store."""

import pytest
from simulation.generator import MultiEntitySimulator
from simulation.attacks import AdversarialAttackInjector
from simulation.models import AttackType, Transaction
from streaming.pipeline import StreamingWindowAggregator
from graph.entity_graph import HeterogeneousEntityGraph
from graph.ring_detector import FraudRingDetector
from feature_store.store import EnrichedFeatureVector, OfflineFeatureStore, OnlineFeatureStore


def test_streaming_window_aggregator_velocity_and_impossible_travel():
    agg = StreamingWindowAggregator()
    base_t = 1714521600.0

    # 1. First transaction in New York
    tx1 = Transaction(
        tx_id="TX1", user_id="U1", card_id="C1", device_id="D1", ip_address="198.51.100.1",
        merchant_id="M1", address_id="A1", amount=50.0, timestamp=base_t, channel="ONLINE"
    )
    v1 = agg.process_transaction(tx1, ip_lat=40.7128, ip_lon=-74.0060)
    assert v1["card_tx_count_1m"] == 0.0  # Before current tx was recorded
    assert v1["geo_distance_km"] == 0.0

    # 2. Second transaction 10 seconds later on same card
    tx2 = Transaction(
        tx_id="TX2", user_id="U1", card_id="C1", device_id="D1", ip_address="198.51.100.1",
        merchant_id="M1", address_id="A1", amount=45.0, timestamp=base_t + 10.0, channel="ONLINE"
    )
    v2 = agg.process_transaction(tx2, ip_lat=40.7128, ip_lon=-74.0060)
    assert v2["card_tx_count_1m"] == 1.0

    # 3. Third transaction 15 minutes later from London (Impossible travel!)
    tx3 = Transaction(
        tx_id="TX3", user_id="U1", card_id="C1", device_id="D2", ip_address="203.0.113.5",
        merchant_id="M2", address_id="A2", amount=500.0, timestamp=base_t + 910.0, channel="ONLINE"
    )
    v3 = agg.process_transaction(tx3, ip_lat=51.5074, ip_lon=-0.1278)
    assert v3["geo_distance_km"] > 5500.0  # > 5,500 km between NY and London
    assert v3["implied_speed_kmh"] > 10000.0  # Clearly physically impossible speed


def test_online_and_offline_feature_store():
    # Test Online Key-Value Store
    online_fs = OnlineFeatureStore()
    online_fs.put("card:C1", {"card_tx_count_24h": 5, "card_amount_sum_24h": 250.0})
    fetched = online_fs.get("card:C1")
    assert fetched is not None
    assert fetched["card_tx_count_24h"] == 5

    # Test Offline Point-in-Time Store
    sim = MultiEntitySimulator(seed=42)
    sim.generate_entities(n_users=50, n_cards=80, n_devices=60, n_ips=40, n_merchants=10, n_addresses=50)
    txs = sim.generate_benign_transactions(n_transactions=200)

    graph = HeterogeneousEntityGraph()
    detector = FraudRingDetector(graph)
    agg = StreamingWindowAggregator()
    offline_fs = OfflineFeatureStore()

    for tx in txs:
        v_feats = agg.process_transaction(tx)
        g_feats = detector.extract_graph_features(tx)
        graph.add_transaction(tx)
        offline_fs.record_feature_vector(tx, v_feats, g_feats)

    assert len(offline_fs.records) == 200

    # Test Temporal Leakage-Safe Splits
    (X_train, y_train), (X_val, y_val), (X_test, y_test) = offline_fs.get_temporal_splits(
        train_ratio=0.70, val_ratio=0.15
    )
    assert len(X_train) == 140
    assert len(X_val) == 30
    assert len(X_test) == 30
    assert X_train.shape[1] == 21  # 21 standard normalized features
