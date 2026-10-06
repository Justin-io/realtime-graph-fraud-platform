# Architectural Decision Log (ADR)

## ADR-001: Heterogeneous Typed Entity Graph over Homogeneous Transaction Projections
- **Status**: ACCEPTED
- **Context**: Transactions can be modeled as bipartite graphs (User $\to$ Merchant) or projected onto transaction-to-transaction similarity graphs. However, modern financial fraud involves syndicated attacks where fraud rings share devices, residential IPs, and delivery addresses without transacting at the same merchants.
- **Decision**: Represent fraud as a multi-relational heterogeneous graph with 6 distinct typed entities ($User, Card, Device, IP, Merchant, Address$) and explicit typed temporal edges.
- **Consequences**: Enables GraphSAGE and GAT to aggregate signals across shared hardware and IP proxies, detecting fraud rings that homogeneous transaction graphs cannot capture.

---

## ADR-002: Point-in-Time Dual Feature Store Architecture
- **Status**: ACCEPTED
- **Context**: Online fraud models suffer from "time-travel" data leakage when features (such as 24-hour spend velocity) are trained on aggregated database columns that include transactions that occurred after the training example's timestamp.
- **Decision**: Enforce strict point-in-time correctness. Offline feature store records features using only historical state $\le t_{\text{transaction}}$. Online feature store maintains live rolling windows in key-value memory updated incrementally per event.
- **Consequences**: Zero training-serving skew and leak-free temporal model evaluation.

---

## ADR-003: Progressive 8-Model Evolutionary Hierarchy
- **Status**: ACCEPTED
- **Context**: A common industry failure mode is deploying complex Graph Neural Networks without verifying whether simpler, faster models (Logistic Regression or XGBoost) achieve equivalent accuracy at lower latency.
- **Decision**: Retain and evaluate 8 distinct model families under identical time-aware splits:
  1. Logistic Regression (interpretable linear baseline)
  2. XGBoost (tabular non-linear champion)
  3. Isolation Forest (unsupervised tree anomaly)
  4. Deep PyTorch Autoencoder (reconstruction loss anomaly)
  5. GCN (spectral graph convolution)
  6. GraphSAGE (inductive neighborhood aggregation)
  7. GAT (multi-head edge attention)
  8. Temporal-GNN (time-decay kernels and dynamic node histories)
- **Consequences**: Scientifically proves whether and where graph neural networks outperform tabular baselines.

---

## ADR-004: Cost-Sensitive Decision Theory over Arbitrary 0.5 Thresholds
- **Status**: ACCEPTED
- **Context**: Standard binary classifiers use a default threshold of $p = 0.5$. In fraud detection, class imbalance is extreme (0.1% to 1%), and the cost of a False Positive (customer friction, $\$15$) is drastically different from a False Negative (unrecovered fraud loss, e.g. $\$1,200$).
- **Decision**: Dynamically compute optimal threshold $p^*$ minimizing total expected financial loss:
  $$\text{Cost} = C_{FP} \cdot FP + C_{FN} \cdot FN$$
- **Consequences**: Maximizes dollar-denominated business savings and aligns ML scoring with risk operations.

---

## ADR-005: Exponential Temporal Decay Kernels for Dynamic Edges
- **Status**: ACCEPTED
- **Context**: Fraud rings frequently abandon devices and IP addresses after executing attacks ("burner devices"). Static graphs treat 6-month-old connections as equally relevant to interactions that occurred 5 minutes ago.
- **Decision**: Implement exponential time-decay kernels on graph edges:
  $$\kappa(\Delta t) = \exp(-\lambda \cdot \Delta t)$$
- **Consequences**: Graph representations adapt dynamically to active fraud rings while deprecating stale topological edges.
