# Comprehensive Test Matrix

| Test Suite File | Epic / Component Tested | Key Assertions & Scenarios |
| :--- | :--- | :--- |
| `tests/test_simulation.py` | Epic 1: Multi-Entity Simulator & Attacks | Entity generation, background legitimate behavior, 6 fraud attack patterns (velocity, device sharing, impossible travel, IP clusters, merchant collusion, ATO). |
| `tests/test_graph_engine.py` | Epic 2: Entity Graph & Ring Detector | Heterogeneous node/edge insertion, temporal edge decay, 1-hop/2-hop neighborhood extraction, cycle detection, fraud-ring clustering. |
| `tests/test_streaming_and_feature_store.py` | Epic 3: Streaming & Feature Store | Tumbling/sliding windows (1m, 5m, 1h, 24h, 7d), online key-value retrieval, offline point-in-time correctness without lookahead leakage. |
| `tests/test_models.py` | Epic 4: 8-Model Evolutionary Progression | Tabular baselines (LR, XGB), Anomaly detectors (Isolation Forest, Autoencoder), Graph Neural Networks (GCN, GraphSAGE, GAT, Temporal-GNN). |
| `tests/test_scoring_and_drift.py` | Epics 5 & 6: Scoring, Decision Policy & Drift | Sub-second scoring latency, cost-sensitive threshold optimization, reason codes, PSI & KS drift detection, automated retraining trigger. |
| `tests/test_evaluation_harness.py` | Epic 7: Scientific Evaluation Suite | Benchmark comparing all 8 models on PR-AUC, ROC-AUC, FCR@1%FPR, false positive cost, and inference throughput. |
| `tests/test_api_e2e.py` | Epic 8: FastAPI & SSE Streaming | Endpoints `/health`, `/api/score`, `/api/stream`, `/api/graph/entity/{id}`, `/api/investigation/decision`, `/api/benchmark`. |
