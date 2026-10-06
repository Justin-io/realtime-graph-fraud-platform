"""Unit tests for the 8-model evolutionary hierarchy."""

import pytest
import numpy as np
from simulation.generator import MultiEntitySimulator
from simulation.attacks import AdversarialAttackInjector
from graph.entity_graph import HeterogeneousEntityGraph
from graph.ring_detector import FraudRingDetector
from streaming.pipeline import StreamingWindowAggregator
from feature_store.store import EnrichedFeatureVector, OfflineFeatureStore
from models.tabular import LogisticRegressionFraudModel, XGBoostFraudModel
from models.anomaly import IsolationForestFraudModel, DeepAutoencoderFraudModel
from models.gnn import GCNFraudModel, GraphSAGEFraudModel, GATFraudModel
from models.temporal_gnn import TemporalGNNFraudModel


@pytest.fixture(scope="module")
def prepared_dataset():
    sim = MultiEntitySimulator(seed=42)
    sim.generate_entities(n_users=50, n_cards=80, n_devices=60, n_ips=40, n_merchants=15, n_addresses=50)
    benign = sim.generate_benign_transactions(n_transactions=300)
    injector = AdversarialAttackInjector(sim, seed=42)
    stream = injector.inject_all_attacks(benign, fraud_ratio=0.15)

    graph = HeterogeneousEntityGraph()
    detector = FraudRingDetector(graph)
    agg = StreamingWindowAggregator()
    offline_fs = OfflineFeatureStore()

    for tx in stream:
        v_feats = agg.process_transaction(tx)
        g_feats = detector.extract_graph_features(tx)
        graph.add_transaction(tx)
        offline_fs.record_feature_vector(tx, v_feats, g_feats)

    (X_train, y_train), (X_val, y_val), (X_test, y_test) = offline_fs.get_temporal_splits()
    pyg_data = graph.to_pyg_data()
    return X_train, y_train, X_test, y_test, pyg_data


def test_tabular_baselines(prepared_dataset):
    X_train, y_train, X_test, y_test, _ = prepared_dataset

    # 1. Logistic Regression
    lr_model = LogisticRegressionFraudModel(c_param=1.0)
    lr_model.fit(X_train, y_train)
    lr_probs = lr_model.predict_proba(X_test)
    assert len(lr_probs) == len(X_test)
    assert np.all(lr_probs >= 0.0) and np.all(lr_probs <= 1.0)
    weights = lr_model.get_feature_weights(EnrichedFeatureVector.feature_names())
    assert len(weights) == 21

    # 2. XGBoost
    xgb_model = XGBoostFraudModel(n_estimators=30, max_depth=3)
    xgb_model.fit(X_train, y_train)
    xgb_probs = xgb_model.predict_proba(X_test)
    assert len(xgb_probs) == len(X_test)
    assert np.all(xgb_probs >= 0.0) and np.all(xgb_probs <= 1.0)
    importances = xgb_model.get_feature_importances(EnrichedFeatureVector.feature_names())
    assert len(importances) == 21


def test_anomaly_detectors(prepared_dataset):
    X_train, y_train, X_test, y_test, _ = prepared_dataset

    # 3. Isolation Forest
    if_model = IsolationForestFraudModel(n_estimators=30)
    if_model.fit(X_train)
    if_probs = if_model.predict_proba(X_test)
    assert len(if_probs) == len(X_test)
    assert np.all(if_probs >= 0.0) and np.all(if_probs <= 1.0)

    # 4. Deep Autoencoder
    ae_model = DeepAutoencoderFraudModel(input_dim=21, bottleneck_dim=6, epochs=5)
    ae_model.fit(X_train, y_train)
    ae_probs = ae_model.predict_proba(X_test)
    assert len(ae_probs) == len(X_test)
    assert np.all(ae_probs >= 0.0) and np.all(ae_probs <= 1.0)


def test_graph_neural_networks(prepared_dataset):
    X_train, y_train, X_test, y_test, pyg_data = prepared_dataset

    # 5. GCN
    gcn = GCNFraudModel(epochs=3)
    gcn.fit(X_train, y_train, pyg_data)
    gcn_probs = gcn.predict_proba(X_test, pyg_data)
    assert len(gcn_probs) == len(X_test)
    assert np.all(gcn_probs >= 0.0) and np.all(gcn_probs <= 1.0)

    # 6. GraphSAGE
    sage = GraphSAGEFraudModel(epochs=3)
    sage.fit(X_train, y_train, pyg_data)
    sage_probs = sage.predict_proba(X_test, pyg_data)
    assert len(sage_probs) == len(X_test)

    # 7. GAT
    gat = GATFraudModel(epochs=3)
    gat.fit(X_train, y_train, pyg_data)
    gat_probs = gat.predict_proba(X_test, pyg_data)
    assert len(gat_probs) == len(X_test)


def test_temporal_gnn(prepared_dataset):
    X_train, y_train, X_test, y_test, pyg_data = prepared_dataset

    # 8. Temporal GNN
    t_gnn = TemporalGNNFraudModel(epochs=3)
    t_gnn.fit(X_train, y_train, pyg_data)
    t_probs = t_gnn.predict_proba(X_test, pyg_data)
    assert len(t_probs) == len(X_test)
    assert np.all(t_probs >= 0.0) and np.all(t_probs <= 1.0)
