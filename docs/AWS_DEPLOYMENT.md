# AWS Production Deployment Architecture & Operating Guide

## 1. Cloud-Native Reference Topology

The **Real-Time Graph Fraud Detection Platform** is engineered for high-availability, low-latency deployment on Amazon Web Services (AWS) capable of handling **> 15,000 transactions per second (TPS)** with a strict sub-second SLA (**P99 latency < 50ms**).

```
[ Financial Gateway / Card Switch ]
               │
               ▼  (HTTPS / TLS 1.3)
      [ AWS Application Load Balancer (ALB) ]
               │
      ┌────────┴───────────────────────────┐
      ▼                                    ▼
[ Amazon EKS: Pod Replica 1 ]    [ Amazon EKS: Pod Replica N ]
(FastAPI + Graph Engine + GNN)   (FastAPI + Graph Engine + GNN)
      │               │                    │
      ├───────────────┼────────────────────┤
      ▼               ▼                    ▼
[ Amazon MSK ]  [ ElastiCache ]     [ Amazon Aurora ]
 (Apache Kafka)  (Redis Cluster)     (PostgreSQL 16)
 Live Ingestion  Sub-ms Features    Audit Log & Offline
```

---

## 2. AWS Managed Service Architecture

| Component | AWS Service | Sizing & Configuration | Role |
| :--- | :--- | :--- | :--- |
| **Ingress & TLS** | AWS ALB + Route 53 | HTTP/2 enabled, WAF Shield Advanced | Load balancing with zero-loss connection draining |
| **Container Compute** | Amazon EKS v1.30 | `c7g.2xlarge` (AWS Graviton3) or `g5.xlarge` (NVIDIA A10G) | Runs FastAPI scoring pods and PyTorch Geometric models |
| **Streaming Bus** | Amazon MSK | 3-Broker Kafka Cluster (`kafka.m7g.large`), 3 AZs | Ingests real-time authorization event streams |
| **Online Feature Store**| Amazon ElastiCache Redis | `cache.r7g.xlarge` Multi-AZ with Auto-Failover | Serves real-time sliding window features in < 1.5ms |
| **Audit & Storage** | Amazon Aurora PostgreSQL | `db.r7g.large` Multi-AZ Cluster | Persists transaction features, labels, and audit trail |
| **Model Registry** | Amazon S3 + AWS KMS | Versioned, SSE-KMS encrypted bucket | Stores PyTorch model weights and benchmark reports |
| **Observability** | Amazon Managed Prometheus | Grafana dashboard + CloudWatch Alarms | Real-time P99 latency, PSI drift, and throughput monitoring |

---

## 3. Kubernetes Deployment Steps (EKS)

### 3.1 Namespace & Configuration Setup
```bash
# 1. Create dedicated Kubernetes namespace
kubectl create namespace fraud-detection

# 2. Apply ConfigMap and Secret parameters
kubectl apply -f k8s/configmap.yaml
```

### 3.2 IAM Roles for Service Accounts (IRSA)
Attach least-privilege IAM policies to the Kubernetes service account for S3 model checkpoint access:
```bash
eksctl create iamserviceaccount \
  --name fraud-platform-sa \
  --namespace fraud-detection \
  --cluster fraud-detection-eks-prod \
  --attach-policy-arn arn:aws:iam::123456789012:policy/FraudPlatformS3Policy \
  --approve
```

### 3.3 Deploy Application & Horizontal Pod Autoscaler
```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

---

## 4. Sub-Second Latency Optimization Guidelines

To guarantee < 50ms P99 end-to-end response times under peak load:

1. **PyTorch Intra-Op Thread Tuning**:
   Configure PyTorch CPU thread count to match container CPU cores to prevent lock contention:
   ```python
   import torch
   torch.set_num_threads(4)
   torch.set_num_interop_threads(2)
   ```

2. **Redis Connection Pooling**:
   Use persistent connection pools with TCP keepalive enabled:
   ```python
   redis.ConnectionPool(max_connections=50, socket_timeout=0.010)
   ```

3. **Sub-graph Caching**:
   2-hop ego-network subgraphs are maintained in memory within `HeterogeneousEntityGraph` and updated incrementally via directed node adjacency lists ($O(\text{deg}(v))$).

---

## 5. Drift Monitoring & Automated Retraining on AWS

- **Population Stability Index (PSI)** is computed continuously every 1,000 transactions by `monitoring/drift.py`.
- When `max_psi >= 0.25` or KS test p-value $< 0.01$, a CloudWatch alarm triggers an EventBridge rule that invokes an AWS Step Function to execute `AutomatedRetrainingPipeline`.
- The challenger model is fitted against temporal splits with delayed ground-truth labels and hot-swapped into the running scoring engine with zero downtime.
