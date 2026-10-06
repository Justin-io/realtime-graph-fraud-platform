"""Scientific Evaluation Harness benchmarking all 8 models on PR-AUC, business cost, and inference latency."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Tuple
import numpy as np
from pydantic import BaseModel, Field
from sklearn import metrics
from models.anomaly import DeepAutoencoderFraudModel, IsolationForestFraudModel
from models.gnn import GATFraudModel, GCNFraudModel, GraphSAGEFraudModel
from models.tabular import LogisticRegressionFraudModel, XGBoostFraudModel
from models.temporal_gnn import TemporalGNNFraudModel


class ModelEvaluationScorecard(BaseModel):
    model_name: str
    architecture_family: str  # Tabular, Anomaly, Graph, TemporalGraph
    precision: float
    recall: float
    pr_auc: float
    roc_auc: float
    fcr_at_1pct_fpr: float
    false_positive_cost: float
    fraud_prevented_dollars: float
    net_dollar_savings: float
    p99_latency_ms: float
    throughput_tps: float
    brier_score: float
    rank: int = 1


class ComprehensiveBenchmarkReport(BaseModel):
    total_test_samples: int
    fraud_test_samples: int
    fraud_prevalence_pct: float
    champion_model: str
    champion_pr_auc: float
    champion_net_savings: float
    graph_improvement_demonstrated: bool
    scorecards: List[ModelEvaluationScorecard]


class ScientificBenchmarkHarness:
    """Executes time-aware evaluation across the 8-model hierarchy under identical conditions."""

    @staticmethod
    def evaluate_predictions(
        model_name: str,
        family: str,
        y_true: np.ndarray,
        y_probs: np.ndarray,
        amounts: np.ndarray,
        latencies_ms: List[float],
        fp_cost: float = 15.0,
        threshold: float = 0.50,
    ) -> ModelEvaluationScorecard:
        # Standard classification metrics
        y_pred = (y_probs >= threshold).astype(int)
        prec = float(metrics.precision_score(y_true, y_pred, zero_division=0))
        rec = float(metrics.recall_score(y_true, y_pred, zero_division=0))

        # PR-AUC & ROC-AUC
        precision_curve, recall_curve, _ = metrics.precision_recall_curve(y_true, y_probs)
        pr_auc = float(metrics.auc(recall_curve, precision_curve))
        try:
            roc_auc = float(metrics.roc_auc_score(y_true, y_probs))
        except Exception:
            roc_auc = 0.50

        # Fraud Capture Rate at 1.0% False Positive Rate
        fpr_curve, tpr_curve, thresholds_roc = metrics.roc_curve(y_true, y_probs)
        # Find index closest to 0.01 FPR
        idx_1pct = int(np.argmin(np.abs(fpr_curve - 0.01)))
        fcr_at_1pct = float(tpr_curve[idx_1pct])

        # Cost-sensitive business impact
        fps = int(np.sum((y_pred == 1) & (y_true == 0)))
        tps = (y_pred == 1) & (y_true == 1)

        fp_dollar_cost = round(float(fps * fp_cost), 2)
        prevented_dollars = round(float(np.sum(amounts[tps])), 2)
        net_savings = round(prevented_dollars - fp_dollar_cost, 2)

        # Latency & throughput
        p99_lat = round(float(np.percentile(latencies_ms, 99)), 2) if latencies_ms else 1.0
        p50_lat = round(float(np.median(latencies_ms)), 2) if latencies_ms else 0.5
        tps_rate = round(1000.0 / max(0.1, p50_lat), 1)

        brier = round(float(metrics.brier_score_loss(y_true, y_probs)), 4)

        return ModelEvaluationScorecard(
            model_name=model_name,
            architecture_family=family,
            precision=round(prec, 4),
            recall=round(rec, 4),
            pr_auc=round(pr_auc, 4),
            roc_auc=round(roc_auc, 4),
            fcr_at_1pct_fpr=round(fcr_at_1pct, 4),
            false_positive_cost=fp_dollar_cost,
            fraud_prevented_dollars=prevented_dollars,
            net_dollar_savings=net_savings,
            p99_latency_ms=p99_lat,
            throughput_tps=tps_rate,
            brier_score=brier,
        )

    def benchmark_all_models(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_test: np.ndarray,
        y_test: np.ndarray,
        amounts_test: np.ndarray,
        pyg_data: Any,
    ) -> ComprehensiveBenchmarkReport:
        scorecards: List[ModelEvaluationScorecard] = []

        models_to_run = [
            ("Logistic Regression", "Tabular", LogisticRegressionFraudModel(c_param=1.0)),
            ("XGBoost", "Tabular", XGBoostFraudModel(n_estimators=35, max_depth=4)),
            ("Isolation Forest", "Anomaly", IsolationForestFraudModel(n_estimators=35)),
            ("Deep Autoencoder", "Anomaly", DeepAutoencoderFraudModel(input_dim=21, bottleneck_dim=6, epochs=6)),
            ("GCN", "Graph", GCNFraudModel(epochs=4)),
            ("GraphSAGE", "Graph", GraphSAGEFraudModel(epochs=4)),
            ("GAT", "Graph", GATFraudModel(epochs=4)),
            ("Temporal-GNN", "TemporalGraph", TemporalGNNFraudModel(epochs=4)),
        ]

        for name, family, model in models_to_run:
            # 1. Fit
            if family in ["Graph", "TemporalGraph"]:
                model.fit(X_train, y_train, pyg_data)
            else:
                model.fit(X_train, y_train)

            # 2. Predict with latency tracking
            latencies = []
            probs_list = []
            for i in range(len(X_test)):
                x_single = X_test[i : i + 1]
                t0 = time.time()
                if family in ["Graph", "TemporalGraph"]:
                    p = float(model.predict_proba(x_single, pyg_data)[0])
                else:
                    p = float(model.predict_proba(x_single)[0])
                lat = (time.time() - t0) * 1000.0
                latencies.append(lat)
                probs_list.append(p)

            y_probs = np.array(probs_list, dtype=np.float32)
            card = self.evaluate_predictions(name, family, y_test, y_probs, amounts_test, latencies)
            scorecards.append(card)

        # Sort scorecards by PR-AUC descending
        scorecards.sort(key=lambda s: s.pr_auc, reverse=True)
        for rank, sc in enumerate(scorecards, 1):
            sc.rank = rank

        champion = scorecards[0]
        # Check if graph models outperformed baseline tabular LR
        lr_card = next(s for s in scorecards if s.model_name == "Logistic Regression")
        graph_beat_lr = any(s.pr_auc > lr_card.pr_auc for s in scorecards if s.architecture_family in ["Graph", "TemporalGraph"])

        n_test = len(y_test)
        n_fraud = int(np.sum(y_test == 1))

        return ComprehensiveBenchmarkReport(
            total_test_samples=n_test,
            fraud_test_samples=n_fraud,
            fraud_prevalence_pct=round((n_fraud / max(1, n_test)) * 100.0, 2),
            champion_model=champion.model_name,
            champion_pr_auc=champion.pr_auc,
            champion_net_savings=champion.net_dollar_savings,
            graph_improvement_demonstrated=graph_beat_lr,
            scorecards=scorecards,
        )
