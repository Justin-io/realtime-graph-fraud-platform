"""Temporal Graph Neural Network (T-GNN) incorporating edge decay kernels and evolving node histories."""

from __future__ import annotations

import math
from typing import Optional
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch_geometric.data import Data


class _TemporalGraphConv(nn.Module):
    """Custom message passing layer incorporating edge decay weights and transaction amounts."""

    def __init__(self, in_channels: int, out_channels: int, edge_attr_dim: int = 3):
        super().__init__()
        self.node_proj = nn.Linear(in_channels, out_channels)
        self.edge_proj = nn.Linear(edge_attr_dim, out_channels)
        self.out_proj = nn.Linear(out_channels * 2, out_channels)

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor, edge_attr: torch.Tensor) -> torch.Tensor:
        num_nodes = x.size(0)
        out = torch.zeros((num_nodes, self.out_proj.out_features), device=x.device)

        if edge_index.size(1) == 0:
            # Fallback for empty edges
            h_v = self.node_proj(x)
            return F.relu(self.out_proj(torch.cat([h_v, torch.zeros_like(h_v)], dim=1)))

        src, dst = edge_index[0], edge_index[1]
        # Neighbor messages transformed by node projection + edge decay embedding
        msg = F.relu(self.node_proj(x[src]) + self.edge_proj(edge_attr))

        # Scatter mean aggregate
        agg = torch.zeros((num_nodes, msg.size(1)), device=x.device)
        agg.scatter_add_(0, dst.unsqueeze(1).expand(-1, msg.size(1)), msg)
        deg = torch.zeros((num_nodes, 1), device=x.device)
        deg.scatter_add_(0, dst.unsqueeze(1), torch.ones_like(dst.unsqueeze(1), dtype=torch.float32))
        deg = torch.clamp(deg, min=1.0)
        agg_mean = agg / deg

        h_self = self.node_proj(x)
        fused = torch.cat([h_self, agg_mean], dim=1)
        return F.relu(self.out_proj(fused))


class _TemporalGNNNet(nn.Module):
    def __init__(self, in_channels: int = 8, hidden_dim: int = 16, tabular_dim: int = 21):
        super().__init__()
        self.t_conv1 = _TemporalGraphConv(in_channels, hidden_dim)
        self.t_conv2 = _TemporalGraphConv(hidden_dim, hidden_dim)
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim + tabular_dim, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
        )

    def forward(
        self,
        x_graph: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: torch.Tensor,
        x_tab: torch.Tensor,
    ) -> torch.Tensor:
        h1 = self.t_conv1(x_graph, edge_index, edge_attr)
        h2 = self.t_conv2(h1, edge_index, edge_attr)
        g_embed = torch.mean(h2, dim=0, keepdim=True).expand(x_tab.size(0), -1)
        fused = torch.cat([x_tab, g_embed], dim=1)
        logits = self.classifier(fused).squeeze(-1)
        return logits


class TemporalGNNFraudModel:
    """Temporal Graph Neural Network modeling time-decayed transactions and evolving graph topologies."""

    def __init__(self, epochs: int = 15, lr: float = 0.01):
        self.epochs = epochs
        self.lr = lr
        self.net: Optional[_TemporalGNNNet] = None
        self.is_fitted = False

    def fit(self, X: np.ndarray, y: np.ndarray, pyg_data: Data) -> TemporalGNNFraudModel:
        self.net = _TemporalGNNNet(in_channels=pyg_data.x.size(1), tabular_dim=X.shape[1])

        n_pos = max(1, int(np.sum(y == 1)))
        n_neg = int(np.sum(y == 0))
        pos_weight = torch.tensor([float(n_neg) / float(n_pos)], dtype=torch.float32)

        criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
        optimizer = optim.Adam(self.net.parameters(), lr=self.lr, weight_decay=1e-4)

        t_x = torch.tensor(X, dtype=torch.float32)
        t_y = torch.tensor(y, dtype=torch.float32)

        self.net.train()
        for epoch in range(self.epochs):
            optimizer.zero_grad()
            logits = self.net(pyg_data.x, pyg_data.edge_index, pyg_data.edge_attr, t_x)
            loss = criterion(logits, t_y)
            loss.backward()
            optimizer.step()

        self.is_fitted = True
        return self

    def predict_proba(self, X: np.ndarray, pyg_data: Data) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before predict_proba.")
        self.net.eval()
        t_x = torch.tensor(X, dtype=torch.float32)
        with torch.no_grad():
            logits = self.net(pyg_data.x, pyg_data.edge_index, pyg_data.edge_attr, t_x)
            probs = torch.sigmoid(logits).cpu().numpy()
        return np.clip(probs, 0.0, 1.0)
