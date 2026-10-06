# Implementation Plan & Closed Engineering Loop

## Bounded Autonomous Loop:
`OBSERVE → PLAN → IMPLEMENT → TEST → STREAM → EVALUATE → CRITIQUE → CORRECT → VERIFY → BENCHMARK → RECORD → REPEAT`

---

### Phase 1: Inception, Specifications & Simulation (Epics 1 & 2)
- [x] Initialize Git repository, Python virtual environment, dependencies (`torch`, `torch_geometric`, `xgboost`, `scikit-learn`, `networkx`, `fastapi`).
- [x] Author core architecture and durable specifications (`PRD.md`, `ARCHITECTURE.md`, `TASK_REGISTRY.json`, `IMPLEMENTATION_PLAN.md`, `DECISION_LOG.md`, `EVALUATION_SPEC.md`, `TEST_MATRIX.md`).
- [ ] **Epic 1**: Implement `simulation/entities.py` (Users, Cards, Devices, IPs, Merchants, Addresses) and `simulation/attacks.py` (velocity bursts, device sharing, impossible travel, IP proxy clusters, merchant collusion, ATO).
- [ ] **Epic 2**: Implement `graph/entity_graph.py` (dynamic heterogeneous graph structure) and `graph/ring_detector.py` (fraud ring connected components, cycle detection).
- [ ] Unit tests: `tests/test_simulation.py`, `tests/test_graph_engine.py`.

### Phase 2: Streaming Ingestion & Online/Offline Feature Store (Epic 3)
- [ ] **Epic 3**: Implement `streaming/pipeline.py` (Kafka-compatible event broker abstraction, windowed feature transformations: 1m, 5m, 1h, 24h, 7d) and `feature_store/store.py` (dual online Redis-style key-value store and point-in-time offline feature store).
- [ ] Unit tests: `tests/test_streaming_and_feature_store.py`.

### Phase 3: Evolutionary Model Progression Hierarchy (Epic 4)
- [ ] **Epic 4 - Tabular**: Implement `models/tabular.py` (Logistic Regression & XGBoost baselines with Platt probability calibration).
- [ ] **Epic 4 - Anomaly**: Implement `models/anomaly.py` (Isolation Forest & Deep PyTorch Autoencoder).
- [ ] **Epic 4 - GNNs**: Implement `models/gnn.py` (GCN, inductive GraphSAGE, Multi-Head GAT in PyTorch Geometric).
- [ ] **Epic 4 - Temporal GNN**: Implement `models/temporal_gnn.py` (T-GNN with exponential time-decay kernel and dynamic node state embeddings).
- [ ] Unit tests: `tests/test_models.py`.

### Phase 4: Scoring Engine, Decision Policy & Drift Monitoring (Epics 5 & 6)
- [ ] **Epic 5**: Implement `scoring/engine.py` (sub-second inference pipeline, cost-sensitive threshold optimization, reason code generation, and 2-hop graph evidence assembly).
- [ ] **Epic 6**: Implement `monitoring/drift.py` (Population Stability Index, KS-test, concept drift detector) and `monitoring/retraining.py` (delayed chargeback labels simulator and automated retraining pipeline).
- [ ] Unit tests: `tests/test_scoring_and_drift.py`.

### Phase 5: Scientific Evaluation Harness & Benchmarking Suite (Epic 7)
- [ ] **Epic 7**: Implement `eval/benchmarks.py` and `eval/harness.py` systematically comparing all 8 models (LR, XGB, IF, AE, GCN, GraphSAGE, GAT, T-GNN) on Precision, Recall, PR-AUC, ROC-AUC, Fraud Capture Rate @ 1% FPR, False Positive Cost, and Inference Latency.
- [ ] Unit tests: `tests/test_evaluation_harness.py`.

### Phase 6: FastAPI Web Service & Fraud Console Frontend (Epics 8 & 9)
- [ ] **Epic 8**: Implement `api/main.py`, `api/routes/scoring.py`, `api/routes/streaming.py`, `api/routes/investigation.py` with SSE streaming.
- [ ] **Epic 9**: Build React + TypeScript Fraud Investigation Console in `frontend/src/App.tsx` (live transaction stream, interactive graph visualizer, fraud ring inspector, model benchmark view). Compile to `frontend/dist`.
- [ ] Integration tests: `tests/test_api_e2e.py`.

### Phase 7: Packaging, Docker, Kubernetes & AWS Infrastructure (Epic 10)
- [ ] **Epic 10**: Authored `Dockerfile`, `docker-compose.yml`, `k8s/deployment.yaml`, `Makefile`, `docs/AWS_DEPLOYMENT.md`, `README.md`.
- [ ] Full test matrix verification across all test suites.
