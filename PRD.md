# Product Requirements Document (PRD)

## Project: Production-Grade Real-Time Graph Fraud Detection Platform

### 1. Executive Summary
Financial fraud is inherently adversarial, distributed, and fast-moving. Sophisticated syndicates operate across shared infrastructure—rotating burner devices, cycling through residential proxies, synthesizing artificial identities, and testing compromised cards across dispersed merchant accounts. Static rule engines and isolated tabular classifiers fail because they evaluate transactions in isolation, blind to the underlying graph topology and temporal velocity connecting disparate accounts.

This platform delivers an enterprise, production-grade **Real-Time Temporal Graph Fraud Detection Platform** that simulates millions of multi-entity financial interactions, maintains a live heterogeneous entity graph ($User \leftrightarrow Card \leftrightarrow Device \leftrightarrow IP \leftrightarrow Merchant \leftrightarrow Address$), and executes sub-second risk decisions. It systematically benchmarks and proves whether graph neural complexity (GraphSAGE, GAT, Temporal GNNs) outperforms battle-tested tabular and anomaly baselines (Logistic Regression, XGBoost, Isolation Forest, Autoencoders).

---

### 2. Core Personas & User Scenarios

1. **Fraud Operations Analyst**:
   - Needs an interactive investigation console to trace live high-risk transactions.
   - Demands sub-second explainability: why was a transaction flagged, which risk rules were tripped, and what does the 2-hop graph neighborhood reveal?
   - Takes human-in-the-loop decisions (Confirm Fraud, Whitelist, Challenge via Step-up MFA).
2. **Machine Learning / Risk Engineer**:
   - Needs leak-free temporal evaluation and online/offline feature parity.
   - Requires rigorous benchmarking comparing tabular vs deep graph architectures under identical time splits.
   - Monitors model drift (PSI, KS-test) and initiates automated retraining on delayed chargeback signals.
3. **Head of Risk & Payments Executive**:
   - Monitors business impact: Fraud Capture Rate @ 1% False Positive Rate (FPR), False Positive Cost vs Fraud Losses prevented, and API P99 latency (< 50ms).

---

### 3. Critical Requirements & Acceptance Criteria

#### A. Multi-Entity Simulator & Fraud Attack Generation
- **Entities**: Millions of Users, Credit/Debit Cards, Mobile/Desktop Devices, IPv4/IPv6 Addresses, Merchants, Physical Shipping/Billing Addresses.
- **Attack Types**:
  1. *Carding & Velocity Bursts*: Rapid transactions across multiple cards using a single automated device.
  2. *Device-Sharing Fraud Rings*: Multiple disparate user accounts bound to identical hardware fingerprints.
  3. *Impossible Travel*: Geographically incompatible transactions (e.g. London to Singapore in 20 minutes).
  4. *IP Cluster / Residential Proxy Farms*: Suspicious ASN/IP syndicates driving multi-card probing.
  5. *Merchant Collusion / Bust-Out*: Collusive merchants processing fake or split transactions.
  6. *Account Takeover (ATO)*: Sudden shift in device fingerprint, geo-location, and withdrawal velocity.

#### B. Dynamic Heterogeneous Entity Graph
- Entities represented as typed nodes: `User`, `Card`, `Device`, `IP`, `Merchant`, `Address`.
- Relationships maintained as directed temporal edges:
  - `(User)-[OWNS]->(Card)`
  - `(User)-[USES]->(Device)`
  - `(Device)-[CONNECTS_FROM]->(IP)`
  - `(Card)-[TRANSACTS_WITH]->(Merchant)`
  - `(User)-[SHIPS_TO]->(Address)`
- Dynamic sub-second graph updates upon transaction ingestion with temporal decay kernels.

#### C. Model Hierarchy & Progressive Benchmarking
Must implement and evaluate all 8 model families under identical temporal splits:
1. **Logistic Regression** (Interpretable baseline, L1/L2 penalized, probability calibration)
2. **XGBoost / Gradient Boosted Trees** (Non-linear tabular champion with feature importance)
3. **Isolation Forest** (Unsupervised anomaly detection baseline)
4. **Deep Autoencoder** (Reconstruction loss anomaly detector in PyTorch)
5. **Graph Convolutional Network (GCN)** (2-layer spectral graph convolution)
6. **GraphSAGE** (Inductive neighborhood aggregation: Mean/Pooling for unseen entities)
7. **Graph Attention Network (GAT)** (Multi-head attention scoring neighboring edge relevance)
8. **Temporal Graph Neural Network (T-GNN)** (Incorporates edge timestamps and historical node states)

#### D. Real-Time Streaming & Feature Store Parity
- **Streaming Pipeline**: Kafka-compatible transaction ingestion with tumbling and sliding window aggregations (1m, 5m, 1h, 24h, 7d).
- **Online Feature Store**: Low-latency key-value feature retrieval (< 5ms) for live scoring.
- **Offline Feature Store**: Point-in-time correct historical feature table preventing lookahead data leakage.
- **Sub-Second Scoring API**: REST & SSE endpoints returning risk score, decision (`APPROVE`, `CHALLENGE`, `DECLINE`), reason codes, and supporting graph evidence in < 50ms.

#### E. MLOps, Drift Detection & Explainability
- **Class Imbalance**: Cost-sensitive weighted cross-entropy and focal loss.
- **Probability Calibration**: Platt scaling / Isotonic regression.
- **Threshold Optimization**: Decision threshold optimized for business payoff ($Cost = C_{FP} \cdot FP + C_{FN} \cdot FN$).
- **Drift Monitoring**: Population Stability Index (PSI) and Kolmogorov-Smirnov test for online feature drift and concept drift.
- **Explainability**: Top risk drivers, graph ring identifiers, rule triggers, and neighborhood visualizations.
