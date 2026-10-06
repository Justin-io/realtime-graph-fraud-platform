"""Evaluation Dataset and Benchmark Generation for Scientific Model Comparison."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
import numpy as np
from feature_store.store import OfflineFeatureStore
from graph.entity_graph import HeterogeneousEntityGraph
from graph.ring_detector import FraudRingDetector
from simulation.attacks import AdversarialAttackInjector
from simulation.generator import MultiEntitySimulator
from streaming.pipeline import StreamingWindowAggregator


def generate_benchmark_dataset(
    n_users: int = 150,
    n_cards: int = 220,
    n_devices: int = 180,
    n_ips: int = 120,
    n_merchants: int = 25,
    n_addresses: int = 150,
    n_benign: int = 1200,
    fraud_ratio: float = 0.12,
    seed: int = 42,
) -> Tuple[OfflineFeatureStore, HeterogeneousEntityGraph, np.ndarray, np.ndarray, np.ndarray, np.ndarray, Any]:
    """Generates an end-to-end benchmark dataset with all 6 fraud attacks and returns temporal splits."""
    sim = MultiEntitySimulator(seed=seed)
    sim.generate_entities(
        n_users=n_users,
        n_cards=n_cards,
        n_devices=n_devices,
        n_ips=n_ips,
        n_merchants=n_merchants,
        n_addresses=n_addresses,
    )
    benign_txs = sim.generate_benign_transactions(n_transactions=n_benign)
    injector = AdversarialAttackInjector(sim, seed=seed)
    stream = injector.inject_all_attacks(benign_txs, fraud_ratio=fraud_ratio)

    graph = HeterogeneousEntityGraph()
    detector = FraudRingDetector(graph)
    agg = StreamingWindowAggregator()
    offline_fs = OfflineFeatureStore()

    for tx in stream:
        v_feats = agg.process_transaction(tx)
        g_feats = detector.extract_graph_features(tx)
        graph.add_transaction(tx)
        offline_fs.record_feature_vector(tx, v_feats, g_feats)

    (X_train, y_train), (X_val, y_val), (X_test, y_test) = offline_fs.get_temporal_splits(
        train_ratio=0.70, val_ratio=0.15
    )
    pyg_data = graph.to_pyg_data()

    # Extract test transaction amounts for cost-sensitive evaluation
    test_records = offline_fs.records[len(X_train) + len(X_val) :]
    test_amounts = np.array([r.amount for r in test_records], dtype=np.float32)

    return offline_fs, graph, X_train, y_train, X_test, y_test, test_amounts, pyg_data
