"""End-to-end integration tests for FastAPI REST and streaming endpoints."""

import pytest
from fastapi.testclient import TestClient
from api.main import app
from api.app_state import platform_state


@pytest.fixture(scope="module")
def client():
    # Force initialization for test suite
    platform_state.initialize(quick_warmup=True)
    with TestClient(app) as test_client:
        yield test_client


def test_healthcheck(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["is_initialized"] is True
    assert data["champion_model"] is not None
    assert data["graph_nodes"] > 0
    assert data["graph_edges"] > 0


def test_spa_index_served(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "FraudShield AI" in res.text


def test_score_transaction_endpoint(client):
    # Retrieve an existing user from the state graph
    user_nodes = [n for n, d in platform_state.graph.nx_graph.nodes(data=True) if d.get("type") == "User"]
    assert len(user_nodes) > 0
    user_id = user_nodes[0]

    payload = {
        "user_id": user_id,
        "card_id": "CARD_TEST_001",
        "device_id": "DEV_TEST_001",
        "ip_address": "198.51.100.42",
        "merchant_id": "MERCH_ELECTRONICS",
        "billing_address_id": "ADDR_NYC_01",
        "amount": 450.75,
        "ip_lat": 40.7128,
        "ip_lon": -74.0060,
    }

    res = client.post("/api/score", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "risk_score" in data
    assert 0.0 <= data["risk_score"] <= 100.0
    assert data["decision"] in ["APPROVE", "CHALLENGE", "DECLINE"]
    assert data["latency_ms"] < 200.0  # sub-second target
    assert "graph_evidence" in data
    assert "model_breakdown" in data
    assert len(data["model_breakdown"]) > 0


def test_policy_get_and_update(client):
    # GET policy
    res = client.get("/api/score/policy")
    assert res.status_code == 200
    policy_data = res.json()
    assert "approve_threshold" in policy_data
    assert "decline_threshold" in policy_data

    # UPDATE policy
    update_payload = {
        "approve_threshold": 0.30,
        "decline_threshold": 0.80,
        "cost_false_positive": 20.0,
    }
    put_res = client.put("/api/score/policy", json=update_payload)
    assert put_res.status_code == 200
    assert put_res.json()["policy"]["approve_threshold"] == 0.30


def test_stream_recent_and_attack_injection(client):
    # Inject attack
    inject_payload = {
        "attack_type": "FRAUD_RING",
        "burst_size": 5,
    }
    inj_res = client.post("/api/stream/inject", json=inject_payload)
    assert inj_res.status_code == 200
    inj_data = inj_res.json()
    assert inj_data["status"] == "injected"
    assert inj_data["count"] > 0

    # Retrieve recent transactions
    rec_res = client.get("/api/stream/recent?limit=20")
    assert rec_res.status_code == 200
    rec_data = rec_res.json()
    assert "transactions" in rec_data
    assert len(rec_data["transactions"]) > 0


def test_graph_endpoints(client):
    # 1. Graph stats
    stats_res = client.get("/api/graph/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["total_nodes"] > 0
    assert stats["total_edges"] > 0
    assert "User" in stats["node_types"]

    # 2. Get entity neighborhood
    user_nodes = [n for n, d in platform_state.graph.nx_graph.nodes(data=True) if d.get("type") == "User"]
    test_node = user_nodes[0]
    nbr_res = client.get(f"/api/graph/entity/{test_node}")
    assert nbr_res.status_code == 200
    nbr = nbr_res.json()
    assert nbr["center_node"] == test_node
    assert len(nbr["nodes"]) > 0
    assert len(nbr["edges"]) > 0

    # 3. Detect fraud rings
    rings_res = client.get("/api/graph/rings?min_users=2")
    assert rings_res.status_code == 200
    assert "rings" in rings_res.json()


def test_benchmark_report(client):
    res = client.get("/api/benchmark")
    assert res.status_code == 200
    report = res.json()
    assert report is not None
    assert "scorecards" in report
    assert len(report["scorecards"]) == 8
    assert report["champion_model"] is not None


def test_monitoring_drift_and_retraining(client):
    # Drift check
    drift_res = client.get("/api/monitoring/drift")
    assert drift_res.status_code == 200
    drift_data = drift_res.json()
    assert "max_psi" in drift_data
    assert "feature_reports" in drift_data

    # Simulate drift
    sim_res = client.post("/api/monitoring/simulate_drift", json={"shift_feature": "amount", "multiplier": 5.0})
    assert sim_res.status_code == 200
    sim_data = sim_res.json()
    assert sim_data["status"] == "drift_simulated"
    assert sim_data["report"]["max_psi"] > 0.0

    # Retrain trigger
    retrain_res = client.post("/api/monitoring/retrain")
    assert retrain_res.status_code == 200
    assert "event" in retrain_res.json()


def test_investigation_and_analyst_decision(client):
    # Check pending alerts
    alerts_res = client.get("/api/investigation/alerts")
    assert alerts_res.status_code == 200
    alerts_data = alerts_res.json()
    assert "alerts" in alerts_data

    # Submit an analyst decision
    decision_payload = {
        "tx_id": "TX_TEST_ALERT_999",
        "user_id": "USER_TEST_001",
        "amount": 890.00,
        "analyst_id": "analyst_sarah_chen",
        "decision": "CONFIRM_FRAUD",
        "notes": "Verified syndicated card testing attack on shared hardware hub",
        "original_risk_score": 92.5,
        "original_decision": "DECLINE",
    }
    dec_res = client.post("/api/investigation/decision", json=decision_payload)
    assert dec_res.status_code == 200
    dec_data = dec_res.json()
    assert dec_data["decision"] == "CONFIRM_FRAUD"
    assert dec_data["tx_id"] == "TX_TEST_ALERT_999"

    # Check decisions history
    hist_res = client.get("/api/investigation/decisions")
    assert hist_res.status_code == 200
    assert any(d["tx_id"] == "TX_TEST_ALERT_999" for d in hist_res.json()["decisions"])

    # Check audit log
    audit_res = client.get("/api/investigation/audit_log")
    assert audit_res.status_code == 200
    assert len(audit_res.json()["audit_logs"]) > 0
