"""Unsupervised Anomaly Detectors: Isolation Forest and PyTorch Deep Autoencoder."""

from __future__ import annotations

from typing import Dict, List, Optional
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import torch
import torch.nn as nn
import torch.optim as optim


class IsolationForestFraudModel:
    """Unsupervised tree ensemble detecting zero-day transaction outliers."""

    def __init__(self, contamination: float = 0.05, n_estimators: int = 100):
        self.model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            random_state=42,
            n_jobs=2,
        )
        self.scaler = StandardScaler()
        self.is_fitted = False

    def fit(self, X: np.ndarray, y: Optional[np.ndarray] = None) -> IsolationForestFraudModel:
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled)
        self.is_fitted = True
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before predict_proba.")
        X_scaled = self.scaler.transform(X)
        # score_samples returns negative anomaly score (lower is more anomalous)
        raw_scores = self.model.score_samples(X_scaled)
        # Invert and scale to [0, 1]
        anomaly_scores = -raw_scores
        min_s, max_s = float(np.min(anomaly_scores)), float(np.max(anomaly_scores))
        if max_s > min_s:
            scaled_probs = (anomaly_scores - min_s) / (max_s - min_s)
        else:
            scaled_probs = np.zeros_like(anomaly_scores)
        return np.clip(scaled_probs, 0.0, 1.0)


class _AutoencoderNet(nn.Module):
    def __init__(self, input_dim: int = 21, bottleneck_dim: int = 6):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 14),
            nn.BatchNorm1d(14),
            nn.ReLU(),
            nn.Linear(14, bottleneck_dim),
            nn.ReLU(),
        )
        self.decoder = nn.Sequential(
            nn.Linear(bottleneck_dim, 14),
            nn.BatchNorm1d(14),
            nn.ReLU(),
            nn.Linear(14, input_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded


class DeepAutoencoderFraudModel:
    """Deep PyTorch reconstruction-loss anomaly detector trained on benign behaviors."""

    def __init__(self, input_dim: int = 21, bottleneck_dim: int = 6, epochs: int = 15, lr: float = 0.005):
        self.input_dim = input_dim
        self.bottleneck_dim = bottleneck_dim
        self.epochs = epochs
        self.lr = lr
        self.scaler = StandardScaler()
        self.net: Optional[_AutoencoderNet] = None
        self.max_recon_error: float = 1.0
        self.is_fitted = False

    def fit(self, X: np.ndarray, y: Optional[np.ndarray] = None) -> DeepAutoencoderFraudModel:
        # If labels provided, train exclusively on benign transactions (y == 0)
        if y is not None:
            benign_mask = (y == 0)
            X_train = X[benign_mask] if np.sum(benign_mask) > 10 else X
        else:
            X_train = X

        X_scaled = self.scaler.fit_transform(X_train)
        self.net = _AutoencoderNet(self.input_dim, self.bottleneck_dim)
        optimizer = optim.Adam(self.net.parameters(), lr=self.lr)
        criterion = nn.MSELoss()

        t_x = torch.tensor(X_scaled, dtype=torch.float32)
        dataset = torch.utils.data.TensorDataset(t_x)
        loader = torch.utils.data.DataLoader(dataset, batch_size=64, shuffle=True)

        self.net.train()
        for epoch in range(self.epochs):
            for (batch_x,) in loader:
                optimizer.zero_grad()
                recon = self.net(batch_x)
                loss = criterion(recon, batch_x)
                loss.backward()
                optimizer.step()

        # Compute calibration scale on training data
        self.net.eval()
        with torch.no_grad():
            train_recon = self.net(t_x)
            errors = torch.mean((t_x - train_recon) ** 2, dim=1).numpy()
            self.max_recon_error = max(1e-4, float(np.percentile(errors, 99)))

        self.is_fitted = True
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before predict_proba.")
        self.net.eval()
        X_scaled = self.scaler.transform(X)
        t_x = torch.tensor(X_scaled, dtype=torch.float32)

        with torch.no_grad():
            recon = self.net(t_x)
            mse_errors = torch.mean((t_x - recon) ** 2, dim=1).numpy()

        # Map reconstruction error to calibrated [0, 1] risk score
        scaled_risk = mse_errors / self.max_recon_error
        # Sigmoid squash around threshold
        probs = 1.0 / (1.0 + np.exp(-3.0 * (scaled_risk - 1.0)))
        return np.clip(probs, 0.0, 1.0)
