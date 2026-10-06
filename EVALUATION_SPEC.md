# Scientific Evaluation Specification & Benchmarking Metrics

## 1. Primary Classification & Imbalance Metrics

Given extreme class imbalance ($P(Y=1) \approx 0.5\% - 2.0\%$), standard accuracy is uninformative. The platform evaluates models using:

### A. Precision-Recall Area Under Curve (PR-AUC)
$$\text{PR-AUC} = \int_0^1 P(R) \, dR \approx \sum_k (R_k - R_{k-1}) \cdot P_k$$
PR-AUC is the gold standard for rare-event fraud detection because it does not reward high true negative counts ($TN$).

### B. Fraud Capture Rate at Fixed False Positive Rates
- **FCR @ 1.0% FPR**: Fraction of total fraud caught when customer friction is constrained to $\le 1.0\%$ of benign transactions.
- **FCR @ 0.1% FPR**: Ultra-low friction threshold for automated auto-declines.

### C. Brier Score (Probability Calibration)
$$\text{Brier Score} = \frac{1}{N} \sum_{i=1}^N (p_i - y_i)^2$$
Measures whether predicted probabilities represent true risk frequencies.

---

## 2. Cost-Sensitive Business Loss Metrics

Every decision policy ($p^*$) is evaluated using real financial impact:

$$\text{Net Fraud Loss} = \sum_{i \in \text{FN}} \text{Amount}_i$$
$$\text{False Positive Friction Cost} = N_{\text{FP}} \times C_{\text{FP}} \quad (C_{\text{FP}} = \$15.00)$$
$$\text{Net Dollar Savings} = \sum_{i \in \text{TP}} \text{Amount}_i - \left( N_{\text{FP}} \times C_{\text{FP}} \right)$$

---

## 3. Computational Performance Budgets

| Metric | Target SLA | Hard Maximum Budget |
| :--- | :--- | :--- |
| **End-to-End Scoring Latency (P50)** | $< 15\text{ ms}$ | $25\text{ ms}$ |
| **End-to-End Scoring Latency (P99)** | $< 45\text{ ms}$ | $60\text{ ms}$ |
| **Graph Neighborhood Extraction (2-hop)** | $< 10\text{ ms}$ | $15\text{ ms}$ |
| **Throughput (Single Node)** | $> 2,000\text{ TPS}$ | $> 1,000\text{ TPS}$ |

---

## 4. Population Stability Index (PSI) Drift Metric

$$\text{PSI} = \sum_{b=1}^B \left( \%Actual_b - \%Baseline_b \right) \times \ln \left( \frac{\%Actual_b}{\%Baseline_b} \right)$$

- $\text{PSI} < 0.10$: No significant drift; model state is stable.
- $0.10 \le \text{PSI} < 0.25$: Moderate drift; warning triggered, schedule shadow retraining.
- $\text{PSI} \ge 0.25$: Significant population drift; automated retraining alert fired.
