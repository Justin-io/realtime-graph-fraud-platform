"""Benchmark API routes serving scientific evaluation reports comparing all 8 model families."""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Query
from pydantic import BaseModel, Field

from api.app_state import platform_state
from eval.benchmarks import generate_benchmark_dataset
from eval.harness import ComprehensiveBenchmarkReport, ScientificBenchmarkHarness

router = APIRouter(prefix="/api/benchmark", tags=["Scientific Evaluation"])


class RunBenchmarkRequest(BaseModel):
    n_benign: int = Field(150, ge=50, le=500)
    fraud_ratio: float = Field(0.15, ge=0.05, le=0.40)


@router.get("", response_model=Optional[ComprehensiveBenchmarkReport])
def get_latest_benchmark_report():
    """Returns the latest scientific benchmark scorecard comparing Logistic Regression, XGBoost, Isolation Forest, Autoencoder, GCN, GraphSAGE, GAT, and Temporal-GNN."""
    if not platform_state.is_initialized:
        platform_state.initialize()

    return platform_state.benchmark_report


@router.post("/run", response_model=ComprehensiveBenchmarkReport)
def execute_benchmark_run(req: RunBenchmarkRequest):
    """Triggers a fresh scientific evaluation cycle across all 8 models on a time-split benchmark dataset."""
    if not platform_state.is_initialized:
        platform_state.initialize()

    (
        offline_fs,
        graph,
        X_train,
        y_train,
        X_test,
        y_test,
        test_amounts,
        pyg_data,
    ) = generate_benchmark_dataset(
        n_users=35,
        n_cards=50,
        n_devices=45,
        n_ips=30,
        n_merchants=12,
        n_addresses=35,
        n_benign=req.n_benign,
        fraud_ratio=req.fraud_ratio,
        seed=42,
    )

    harness = ScientificBenchmarkHarness()
    report = harness.benchmark_all_models(
        X_train=X_train,
        y_train=y_train,
        X_test=X_test,
        y_test=y_test,
        amounts_test=test_amounts,
        pyg_data=pyg_data,
    )

    platform_state.benchmark_report = report

    platform_state._record_audit(
        event_type="BENCHMARK_RUN",
        details={
            "champion_model": report.champion_model,
            "champion_pr_auc": report.champion_pr_auc,
            "net_dollar_savings": report.champion_net_savings,
            "test_samples": report.total_test_samples,
        },
    )

    return report
