"""Unit tests for scientific evaluation harness and 8-model benchmark suite."""

import pytest
import numpy as np
from eval.benchmarks import generate_benchmark_dataset
from eval.harness import ScientificBenchmarkHarness


def test_scientific_benchmark_harness_runs_all_8_models():
    # Generate compact benchmark dataset for test execution speed
    offline_fs, graph, X_train, y_train, X_test, y_test, test_amounts, pyg_data = generate_benchmark_dataset(
        n_users=30,
        n_cards=45,
        n_devices=40,
        n_ips=25,
        n_merchants=10,
        n_addresses=30,
        n_benign=150,
        fraud_ratio=0.15,
        seed=42,
    )

    assert len(X_train) > 0
    assert len(X_test) > 0
    assert len(test_amounts) == len(X_test)

    harness = ScientificBenchmarkHarness()
    report = harness.benchmark_all_models(
        X_train=X_train,
        y_train=y_train,
        X_test=X_test,
        y_test=y_test,
        amounts_test=test_amounts,
        pyg_data=pyg_data,
    )

    # 1. Ensure all 8 models are evaluated
    assert len(report.scorecards) == 8
    model_names = [s.model_name for s in report.scorecards]
    assert "Logistic Regression" in model_names
    assert "XGBoost" in model_names
    assert "Isolation Forest" in model_names
    assert "Deep Autoencoder" in model_names
    assert "GCN" in model_names
    assert "GraphSAGE" in model_names
    assert "GAT" in model_names
    assert "Temporal-GNN" in model_names

    # 2. Check metrics sanity across all scorecards
    for sc in report.scorecards:
        assert 0.0 <= sc.pr_auc <= 1.0
        assert 0.0 <= sc.roc_auc <= 1.0
        assert 0.0 <= sc.fcr_at_1pct_fpr <= 1.0
        assert sc.p99_latency_ms > 0.0
        assert sc.throughput_tps > 0.0
        assert 1 <= sc.rank <= 8

    # 3. Check report metadata
    assert report.champion_model in model_names
    assert report.total_test_samples == len(X_test)
    assert report.fraud_test_samples > 0
