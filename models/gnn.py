"""Graph Neural Network architectures: GCN, GraphSAGE, and GAT in PyTorch Geometric."""

from __future__ import annotations

from typing import Optional
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch_geometric.data import Data
from torch_geometric.nn import GATConv, GCNConv, SAGEConv


class _GCNNet(nn.Module):
    def __init__(self, in_channels: int = 8, hidden_dim: int = 16, tabular_dim: int = 21):
        super().__init__()
        self.conv1 = GCNConv(in_channels, hidden_dim)
        self.conv2 = GCNConv(hidden_dim, hidden_dim)
        # Tabular + graph embedding fusion classifier
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim + tabular_dim, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
        )

    def forward(self, x_graph: torch.Tensor, edge_index: torch.Tensor, x_tab: torch.Tensor) -> torch.Tensor:
        h = F.relu(self.conv1(x_graph, edge_index))
        h = F.relu(self.conv2(h, edge_index))
        # Global graph context embedding (mean over graph nodes)
        g_embed = torch.mean(h, dim=0, keepdim=True).expand(x_tab.size(0), -1)
        fused = torch.cat([x_tab, g_embed], dim=1)
        logits = self.classifier(fused).squeeze(-1)
        return logits


class _GraphSAGENet(nn.Module):
    def __init__(self, in_channels: int = 8, hidden_dim: int = 16, tabular_dim: int = 21):
        super().__init__()
        self.conv1 = SAGEConv(in_channels, hidden_dim, aggr="mean")
        self.conv2 = SAGEConv(hidden_dim, hidden_dim, aggr="mean")
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim + tabular_dim, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
        )

    def forward(self, x_graph: torch.Tensor, edge_index: torch.Tensor, x_tab: torch.Tensor) -> torch.Tensor:
        h = F.relu(self.conv1(x_graph, edge_index))
        h = F.relu(self.conv2(h, edge_index))
        g_embed = torch.mean(h, dim=0, keepdim=True).expand(x_tab.size(0), -1)
        fused = torch.cat([x_tab, g_embed], dim=1)
        logits = self.classifier(fused).squeeze(-1)
        return logits


class _GATNet(nn.Module):
    def __init__(self, in_channels: int = 8, hidden_dim: int = 8, heads: int = 2, tabular_dim: int = 21):
        super().__init__()
        self.conv1 = GATConv(in_channels, hidden_dim, heads=heads)
        self.conv2 = GATConv(hidden_dim * heads, hidden_dim, heads=1)
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim + tabular_dim, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
        )

    def forward(self, x_graph: torch.Tensor, edge_index: torch.Tensor, x_tab: torch.Tensor) -> torch.Tensor:
        h = F.elu(self.conv1(x_graph, edge_index))
        h = F.elu(self.conv2(h, edge_index))
        g_embed = torch.mean(h, dim=0, keepdim=True).expand(x_tab.size(0), -1)
        fused = torch.cat([x_tab, g_embed], dim=1)
        logits = self.classifier(fused).squeeze(-1)
        return logits


class BaseGNNFraudModel:
    """Base class for Graph Neural Network fraud detectors with focal / pos-weight loss."""

    def __init__(self, model_type: str = "GCN", epochs: int = 15, lr: float = 0.01):
        self.model_type = model_type
        self.epochs = epochs
        self.lr = lr
        self.net: Optional[nn.Module] = None
        self.is_fitted = False

    def fit(self, X: np.ndarray, y: np.ndarray, pyg_data: Data) -> BaseGNNFraudModel:
        if self.model_type == "GCN":
            self.net = _GCNNet(in_channels=pyg_data.x.size(1), tabular_dim=X.shape[1])
        elif self.model_type == "GraphSAGE":
            self.net = _GraphSAGENet(in_channels=pyg_data.x.size(1), tabular_dim=X.shape[1])
        elif self.model_type == "GAT":
            self.net = _GATNet(in_channels=pyg_data.x.size(1), tabular_dim=X.shape[1])
        else:
            raise ValueError(f"Unknown GNN model type: {self.model_type}")

        # Compute positive class weight
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
            logits = self.net(pyg_data.x, pyg_data.edge_index, t_x)
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
            logits = self.net(pyg_data.x, pyg_data.edge_index, t_x)
            probs = torch.sigmoid(logits).cpu().numpy()
        return np.clip(probs, 0.0, 1.0)


class GCNFraudModel(BaseGNNFraudModel):
    def __init__(self, epochs: int = 15, lr: float = 0.01):
        super().__init__(model_type="GCN", epochs=epochs, lr=lr)


class GraphSAGEFraudModel(BaseGNNFraudModel):
    def __init__(self, epochs: int = 15, lr: float = 0.01):
        super().__init__(model_type="GraphSAGE", epochs=epochs, lr=lr)


class GATFraudModel(BaseGNNFraudModel):
    def __init__(self, epochs: int = 15, lr: float = 0.01):
        super().__init__(model_type="GAT", epochs=epochs, lr=lr)
