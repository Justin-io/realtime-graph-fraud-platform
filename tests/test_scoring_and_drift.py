"""Unit tests for Real-Time Scoring Engine, Cost-Sensitive Policy, and Drift Monitor."""

import pytest
import numpy as np
from simulation.generator import MultiEntitySimulator
from simulation.attacks import AdversarialAttackInjector
from graph.entity_graph import HeterogeneousEntityGraph
from scoring.policy import CostSensitiveThresholdOptimizer, DecisionPolicy
from scoring.engine import RealTimeFraudScoringEngine
from models.tabular import XGBoostFraudModel
from monitoring.drift import DriftMonitor
from monitoring.retraining import AutomatedRetrainingPipeline


@pytest.fixture(scope="module")
def seeded_engine():
    sim = MultiEntitySimulator(seed=42)
    sim.generate_entities(n_users=50, n_cards=80, n_devices=60, n_ips=40, n_merchants=15, n_addresses=50)
    benign = sim.generate_benign_transactions(n_transactions=300)
    injector = AdversarialAttackInjector(sim, seed=42)
    stream = injector.inject_all_attacks(benign, fraud_ratio=0.12)

    graph = HeterogeneousEntityGraph()
    optimizer = CostSensitiveThresholdOptimizer(fp_cost=15.0)
    policy = DecisionPolicy(challenge_threshold=0.30, decline_threshold=0.75)
    engine = RealTimeFraudScoringEngine(graph=graph, policy=policy)

    # Pre-train an XGBoost champion
    for tx in stream[:200]:
        engine.score_transaction(tx)

    (X_tr, y_tr), _, _ = engine.offline_fs.get_temporal_splits()
    xgb_m = XGBoostFraudModel(n_estimators=25, max_depth=3)
    xgb_m.fit(X_tr, y_tr)
    engine.register_model("XGBoost", xgb_m, is_champion=True)

    return engine, stream[200:]


def test_realtime_scoring_engine_latency_and_evidence(seeded_engine):
    engine, test_txs = seeded_engine
    tx = test_txs[0]

    result = engine.score_transaction(tx)
    assert result.tx_id == tx.tx_id
    assert 0.0 <= result.risk_score <= 100.0
    assert result.decision in ["APPROVE", "CHALLENGE", "DECLINE"]
    # Sub-second latency assertion (< 50ms P99 SLA)
    assert result.latency_ms < 50.0
    # Graph evidence verification
    assert "nodes" in result.graph_evidence
    assert "edges" in result.graph_evidence
    assert len(result.graph_evidence["nodes"]) > 0


def test_cost_sensitive_threshold_optimization():
    optimizer = CostSensitiveThresholdOptimizer(fp_cost=15.0)
    y_true = np.array([0] * 900 + [1] * 100)
    # Synthetic predicted probabilities
    y_probs = np.concatenate([np.random.beta(1, 10, 900), np.random.beta(8, 2, 100)])

    policy = optimizer.optimize_threshold(y_true, y_probs)
    assert 0.05 < policy.challenge_threshold < policy.decline_threshold
    assert policy.decline_threshold <= 0.85
    assert policy.optimal_cost >= 0.0


def test_drift_monitor_and_psi():
    monitor = DriftMonitor()
    np.random.seed(42)

    # 1. Stable baseline vs same distribution
    baseline = np.random.normal(50, 10, (500, 2))
    current_stable = np.random.normal(50, 10, (500, 2))
    report_stable = monitor.evaluate_feature_drift(baseline, current_stable, ["feat_1", "feat_2"])
    assert report_stable.overall_status == "STABLE"
    assert not report_stable.requires_retraining

    # 2. Severe drift (mean shifted to 120)
    current_drifted = np.random.normal(120, 15, (500, 2))
    report_drifted = monitor.evaluate_feature_drift(baseline, current_drifted, ["feat_1", "feat_2"])
    assert report_drifted.overall_status == "CRITICAL_DRIFT"
    assert report_drifted.max_psi > 0.25
    assert report_drifted.requires_retraining


def test_automated_retraining_pipeline(seeded_engine):
    engine, _ = seeded_engine
    pipeline = AutomatedRetrainingPipeline(engine.offline_fs)

    mature_labels = pipeline.simulate_delayed_label_ingestion(days_elapsed=45)
    assert mature_labels > 0

    retrain_event = pipeline.execute_retraining_workflow(
        current_champion_model=engine.models["XGBoost"],
        trigger_reason="CRITICAL_PSI_DRIFT_ALERT",
    )
    assert retrain_event.event_id.startswith("RETRAIN_")
    assert retrain_event.trigger_reason == "CRITICAL_PSI_DRIFT_ALERT"
    assert len(pipeline.history) == 1
