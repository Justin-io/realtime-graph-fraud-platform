"""Global Platform State singleton managing graph, scoring engine, streaming queues, and audit logs."""

from __future__ import annotations

import collections
import random
import time
from typing import Any, Deque, Dict, List, Optional, Tuple

import numpy as np
from pydantic import BaseModel, Field

from eval.benchmarks import generate_benchmark_dataset
from eval.harness import ComprehensiveBenchmarkReport, ScientificBenchmarkHarness
from graph.entity_graph import HeterogeneousEntityGraph
from graph.ring_detector import FraudRing, FraudRingDetector
from models.anomaly import DeepAutoencoderFraudModel, IsolationForestFraudModel
from models.gnn import GATFraudModel, GCNFraudModel, GraphSAGEFraudModel
from models.tabular import LogisticRegressionFraudModel, XGBoostFraudModel
from models.temporal_gnn import TemporalGNNFraudModel
from monitoring.drift import DriftMonitor, OverallDriftAssessment
from monitoring.retraining import AutomatedRetrainingPipeline, RetrainingEvent
from scoring.engine import RealTimeFraudScoringEngine, ScoringResult
from scoring.policy import DecisionPolicy
from simulation.attacks import AdversarialAttackInjector
from simulation.generator import MultiEntitySimulator
from simulation.models import AttackType, Transaction


FEATURE_NAMES = [
    "amount",
    "hour_of_day",
    "day_of_week",
    "user_tx_count_1m",
    "user_tx_count_5m",
    "user_tx_count_1h",
    "user_tx_count_24h",
    "user_tx_count_7d",
    "card_tx_count_1m",
    "card_tx_count_5m",
    "card_tx_count_1h",
    "card_tx_count_24h",
    "card_amount_sum_1h",
    "card_amount_sum_24h",
    "implied_speed_kmh",
    "device_degree_users",
    "device_degree_cards",
    "ip_degree_users",
    "is_in_fraud_ring",
    "ring_size",
    "syndicate_risk_score",
]


class AnalystDecision(BaseModel):
    decision_id: str
    tx_id: str
    user_id: str
    amount: float
    analyst_id: str
    decision: str  # CONFIRM_FRAUD, FALSE_POSITIVE_APPROVE, ESCALATE_DISPUTE
    notes: str
    timestamp: float
    original_risk_score: float
    original_decision: str


class AuditLogEntry(BaseModel):
    entry_id: str
    timestamp: float
    event_type: str  # SCORING, ANALYST_DECISION, RETRAINING, ATTACK_INJECTION, DRIFT_ALERT
    details: Dict[str, Any]


class PlatformState:
    """Production state container holding initialized models, graph state, and stream buffers."""

    def __init__(self):
        self.simulator: Optional[MultiEntitySimulator] = None
        self.attack_injector: Optional[AdversarialAttackInjector] = None
        self.graph: HeterogeneousEntityGraph = HeterogeneousEntityGraph()
        self.ring_detector: FraudRingDetector = FraudRingDetector(self.graph)
        self.scoring_engine: RealTimeFraudScoringEngine = RealTimeFraudScoringEngine(
            graph=self.graph, policy=DecisionPolicy(challenge_threshold=0.35, decline_threshold=0.75, fp_cost=15.0)
        )
        self.drift_monitor: DriftMonitor = DriftMonitor()
        self.retraining_pipeline: Optional[AutomatedRetrainingPipeline] = None

        self.benchmark_report: Optional[ComprehensiveBenchmarkReport] = None
        self.fitted_models: Dict[str, Any] = {}

        # Buffers
        self.recent_transactions: Deque[Dict[str, Any]] = collections.deque(maxlen=300)
        self.alerts: Deque[Dict[str, Any]] = collections.deque(maxlen=150)
        self.analyst_decisions: Deque[AnalystDecision] = collections.deque(maxlen=200)
        self.audit_logs: Deque[AuditLogEntry] = collections.deque(maxlen=500)
        self.pending_attack_stream: Deque[Tuple[Transaction, str]] = collections.deque()

        # Seed data references
        self.X_train_ref: Optional[np.ndarray] = None
        self.y_train_ref: Optional[np.ndarray] = None
        self.is_initialized: bool = False

    def initialize(self, quick_warmup: bool = True):
        if self.is_initialized:
            return

        # 1. Initialize Simulator
        self.simulator = MultiEntitySimulator(seed=42)
        self.simulator.generate_entities(
            n_users=60,
            n_cards=90,
            n_devices=75,
            n_ips=50,
            n_merchants=20,
            n_addresses=60,
        )
        self.attack_injector = AdversarialAttackInjector(self.simulator, seed=42)

        # 2. Benchmark & warm up 8 models
        n_benign = 120 if quick_warmup else 300
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
            n_benign=n_benign,
            fraud_ratio=0.15,
            seed=42,
        )

        self.X_train_ref = X_train
        self.y_train_ref = y_train

        # Populate state graph with warmup graph
        self.graph = graph
        self.ring_detector = FraudRingDetector(self.graph)
        self.scoring_engine = RealTimeFraudScoringEngine(
            graph=self.graph,
            policy=DecisionPolicy(challenge_threshold=0.35, decline_threshold=0.75, fp_cost=15.0),
        )
        self.scoring_engine.offline_fs = offline_fs

        # Run benchmark harness
        harness = ScientificBenchmarkHarness()
        self.benchmark_report = harness.benchmark_all_models(
            X_train=X_train,
            y_train=y_train,
            X_test=X_test,
            y_test=y_test,
            amounts_test=test_amounts,
            pyg_data=pyg_data,
        )

        # Register top-performing trained models into scoring engine
        lr = LogisticRegressionFraudModel(c_param=1.0)
        lr.fit(X_train, y_train)
        self.scoring_engine.register_model("Logistic Regression", lr)

        xgb = XGBoostFraudModel(n_estimators=40, max_depth=4)
        xgb.fit(X_train, y_train)
        self.scoring_engine.register_model("XGBoost", xgb, is_champion=True)

        iso = IsolationForestFraudModel(n_estimators=35)
        iso.fit(X_train, y_train)
        self.scoring_engine.register_model("Isolation Forest", iso)

        ae = DeepAutoencoderFraudModel(input_dim=21, bottleneck_dim=6, epochs=5)
        ae.fit(X_train, y_train)
        self.scoring_engine.register_model("Deep Autoencoder", ae)

        gcn = GCNFraudModel(epochs=4)
        gcn.fit(X_train, y_train, pyg_data)
        self.scoring_engine.register_model("GCN", gcn)

        sage = GraphSAGEFraudModel(epochs=4)
        sage.fit(X_train, y_train, pyg_data)
        self.scoring_engine.register_model("GraphSAGE", sage)

        gat = GATFraudModel(epochs=4)
        gat.fit(X_train, y_train, pyg_data)
        self.scoring_engine.register_model("GAT", gat)

        tgnn = TemporalGNNFraudModel(epochs=4)
        tgnn.fit(X_train, y_train, pyg_data)
        self.scoring_engine.register_model("Temporal-GNN", tgnn)

        # Champion model
        if self.benchmark_report and self.benchmark_report.champion_model in self.scoring_engine.models:
            self.scoring_engine.champion_model_name = self.benchmark_report.champion_model

        # 3. Retraining Pipeline
        self.retraining_pipeline = AutomatedRetrainingPipeline(offline_fs=self.scoring_engine.offline_fs)

        self._record_audit(
            event_type="INITIALIZATION",
            details={
                "champion_model": self.scoring_engine.champion_model_name,
                "registered_models": list(self.scoring_engine.models.keys()),
                "total_train_samples": len(X_train),
                "benchmark_champion": self.benchmark_report.champion_model if self.benchmark_report else None,
            },
        )

        self.is_initialized = True

    def _record_audit(self, event_type: str, details: Dict[str, Any]):
        entry = AuditLogEntry(
            entry_id=f"AUDIT_{len(self.audit_logs)+1:06d}",
            timestamp=time.time(),
            event_type=event_type,
            details=details,
        )
        self.audit_logs.appendleft(entry)

    def inject_attack_scenario(self, attack_name: str, burst_size: int = 10) -> int:
        """Injects a specific adversarial attack pattern into the live stream queue."""
        if not self.simulator or not self.attack_injector:
            return 0

        attack_type_map = {
            "CARD_TESTING": AttackType.VELOCITY_BURST,
            "VELOCITY_BURST": AttackType.VELOCITY_BURST,
            "FRAUD_RING": AttackType.DEVICE_SHARING_RING,
            "DEVICE_SHARING_RING": AttackType.DEVICE_SHARING_RING,
            "IMPOSSIBLE_TRAVEL": AttackType.IMPOSSIBLE_TRAVEL,
            "ACCOUNT_TAKEOVER": AttackType.ACCOUNT_TAKEOVER,
            "IP_ROTATION_BOTNET": AttackType.IP_PROXY_CLUSTER,
            "IP_PROXY_CLUSTER": AttackType.IP_PROXY_CLUSTER,
            "MERCHANT_COLLUSION": AttackType.MERCHANT_COLLUSION,
        }

        atk = attack_type_map.get(attack_name.upper(), AttackType.DEVICE_SHARING_RING)
        curr_t = time.time()
        counter = random.randint(10000, 99999)

        if atk == AttackType.VELOCITY_BURST:
            _, txs = self.attack_injector._inject_velocity_burst(counter, count=burst_size, t_min=curr_t, t_span=60.0)
        elif atk == AttackType.DEVICE_SHARING_RING:
            _, txs = self.attack_injector._inject_device_sharing_ring(counter, count=burst_size, t_min=curr_t, t_span=60.0)
        elif atk == AttackType.IMPOSSIBLE_TRAVEL:
            _, txs = self.attack_injector._inject_impossible_travel(counter, count=burst_size, t_min=curr_t, t_span=60.0)
        elif atk == AttackType.IP_PROXY_CLUSTER:
            _, txs = self.attack_injector._inject_ip_proxy_cluster(counter, count=burst_size, t_min=curr_t, t_span=60.0)
        elif atk == AttackType.MERCHANT_COLLUSION:
            _, txs = self.attack_injector._inject_merchant_collusion(counter, count=burst_size, t_min=curr_t, t_span=60.0)
        elif atk == AttackType.ACCOUNT_TAKEOVER:
            _, txs = self.attack_injector._inject_account_takeover(counter, count=burst_size, t_min=curr_t, t_span=60.0)
        else:
            _, txs = self.attack_injector._inject_device_sharing_ring(counter, count=burst_size, t_min=curr_t, t_span=60.0)

        for a in txs:
            self.pending_attack_stream.append((a, a.attack_type.value if a.attack_type else "ATTACK"))

        self._record_audit(
            event_type="ATTACK_INJECTION",
            details={"attack_name": attack_name, "count": len(txs)},
        )
        return len(txs)

    def generate_and_score_next(self) -> Tuple[ScoringResult, Optional[str]]:
        """Generates the next streaming transaction (adversarial or benign) and executes real-time scoring."""
        if not self.is_initialized:
            self.initialize()

        attack_label: Optional[str] = None
        curr_time = time.time()

        if self.pending_attack_stream:
            tx, attack_label = self.pending_attack_stream.popleft()
            tx.timestamp = curr_time
        else:
            # Generate benign diurnal transaction
            user = random.choice(self.simulator.users)
            user_cards = [c for c in self.simulator.cards if c.user_id == user.user_id]
            card = random.choice(user_cards) if user_cards else random.choice(self.simulator.cards)
            device = self.simulator.devices[hash(user.user_id) % len(self.simulator.devices)]
            ip = self.simulator.ips[hash(user.user_id) % len(self.simulator.ips)]
            merchant = random.choice(self.simulator.merchants)
            address = self.simulator.addresses[hash(user.user_id) % len(self.simulator.addresses)]

            # Amount from merchant log-normal
            raw_amount = random.lognormvariate(2.8, 0.7)
            amt = round(max(2.50, min(raw_amount, 9999.0)), 2)

            tx = Transaction(
                tx_id=f"TX_LIVE_{random.randint(1000000, 9999999)}",
                user_id=user.user_id,
                card_id=card.card_id,
                device_id=device.device_id,
                ip_address=ip.ip_address,
                merchant_id=merchant.merchant_id,
                address_id=address.address_id,
                amount=amt,
                timestamp=curr_time,
                is_fraud=0,
            )

        # Real-time scoring
        score_res = self.scoring_engine.score_transaction(tx)

        # Store in rolling streams
        tx_dict = score_res.model_dump()
        tx_dict["attack_type"] = attack_label or "BENIGN"
        tx_dict["card_id"] = tx.card_id
        tx_dict["device_id"] = tx.device_id
        tx_dict["ip_address"] = tx.ip_address
        tx_dict["merchant_id"] = tx.merchant_id

        self.recent_transactions.appendleft(tx_dict)

        # If flagged as review or decline, push to analyst alert queue
        if score_res.decision in ["CHALLENGE", "DECLINE"]:
            self.alerts.appendleft(tx_dict)

        return score_res, attack_label

    def record_analyst_decision(
        self,
        tx_id: str,
        user_id: str,
        amount: float,
        analyst_id: str,
        decision: str,
        notes: str,
        original_risk_score: float,
        original_decision: str,
    ) -> AnalystDecision:
        dec = AnalystDecision(
            decision_id=f"DEC_{len(self.analyst_decisions)+1:05d}",
            tx_id=tx_id,
            user_id=user_id,
            amount=amount,
            analyst_id=analyst_id,
            decision=decision,
            notes=notes,
            timestamp=time.time(),
            original_risk_score=original_risk_score,
            original_decision=original_decision,
        )
        self.analyst_decisions.appendleft(dec)

        # Remove from pending alerts if reviewed
        self.alerts = collections.deque(
            [a for a in self.alerts if a.get("tx_id") != tx_id], maxlen=150
        )

        self._record_audit(
            event_type="ANALYST_DECISION",
            details={
                "tx_id": tx_id,
                "analyst_id": analyst_id,
                "decision": decision,
                "notes": notes,
            },
        )
        return dec


# Global singleton instance
platform_state = PlatformState()
