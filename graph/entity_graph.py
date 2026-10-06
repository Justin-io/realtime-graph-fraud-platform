"""Dynamic Heterogeneous Entity Graph with incremental temporal edge updates and PyG data export."""

from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Optional, Set, Tuple
import networkx as nx
import numpy as np
import torch
from torch_geometric.data import Data
from simulation.models import Transaction


class HeterogeneousEntityGraph:
    """Maintains a dynamic multi-relational graph connecting Users, Cards, Devices, IPs, Merchants, and Addresses."""

    def __init__(self, time_decay_lambda: float = 1e-5):
        self.time_decay_lambda = time_decay_lambda
        # NetworkX multi-directed graph for topological operations
        self.nx_graph: nx.MultiDiGraph = nx.MultiDiGraph()
        # Node attribute store: node_id -> {"type": ..., "features": np.ndarray}
        self.node_attributes: Dict[str, Dict[str, Any]] = {}
        # Entity-to-index mapping for PyTorch tensor tensors
        self.node_to_idx: Dict[str, int] = {}
        self.idx_to_node: Dict[int, str] = {}
        self._next_idx = 0

    def _get_or_create_node(self, node_id: str, node_type: str, raw_features: Optional[List[float]] = None) -> int:
        if node_id not in self.node_to_idx:
            idx = self._next_idx
            self.node_to_idx[node_id] = idx
            self.idx_to_node[idx] = node_id
            self._next_idx += 1

            # Default 8-dim feature representation per node
            feat = np.array(raw_features if raw_features else [0.0] * 8, dtype=np.float32)
            # Encode node type in one-hot (first 6 dims)
            type_map = {"User": 0, "Card": 1, "Device": 2, "IP": 3, "Merchant": 4, "Address": 5}
            t_idx = type_map.get(node_type, 0)
            feat[t_idx] = 1.0

            self.node_attributes[node_id] = {
                "type": node_type,
                "features": feat,
                "first_seen": time.time(),
                "last_seen": time.time(),
                "tx_count": 0,
            }
            self.nx_graph.add_node(node_id, type=node_type)
        return self.node_to_idx[node_id]

    def add_transaction(self, tx: Transaction) -> None:
        """Incrementally adds a transaction and creates temporal edges across all associated entities."""
        u_idx = self._get_or_create_node(tx.user_id, "User")
        c_idx = self._get_or_create_node(tx.card_id, "Card")
        d_idx = self._get_or_create_node(tx.device_id, "Device")
        ip_idx = self._get_or_create_node(tx.ip_address, "IP")
        m_idx = self._get_or_create_node(tx.merchant_id, "Merchant")
        a_idx = self._get_or_create_node(tx.address_id, "Address")

        # Update node metadata
        for nid in [tx.user_id, tx.card_id, tx.device_id, tx.ip_address, tx.merchant_id, tx.address_id]:
            meta = self.node_attributes[nid]
            meta["last_seen"] = tx.timestamp
            meta["tx_count"] += 1
            meta["features"][6] += math.log1p(tx.amount)  # Total amount accumulated
            meta["features"][7] += 1.0                     # Total tx count

        # Add multi-relational edges
        edge_data = {
            "tx_id": tx.tx_id,
            "timestamp": tx.timestamp,
            "amount": tx.amount,
            "is_fraud": tx.is_fraud,
        }

        # User -> Card (owns)
        self.nx_graph.add_edge(tx.user_id, tx.card_id, relation="OWNS", **edge_data)
        # User -> Device (uses)
        self.nx_graph.add_edge(tx.user_id, tx.device_id, relation="USES_DEVICE", **edge_data)
        # Device -> IP (connected_from)
        self.nx_graph.add_edge(tx.device_id, tx.ip_address, relation="CONNECTED_FROM", **edge_data)
        # Card -> Merchant (transacted)
        self.nx_graph.add_edge(tx.card_id, tx.merchant_id, relation="TRANSACTED", **edge_data)
        # User -> Address (ships_to)
        self.nx_graph.add_edge(tx.user_id, tx.address_id, relation="SHIPS_TO", **edge_data)

    def get_1hop_neighbors(self, node_id: str) -> List[str]:
        if node_id not in self.nx_graph:
            return []
        neighbors = set(self.nx_graph.successors(node_id)) | set(self.nx_graph.predecessors(node_id))
        return list(neighbors)

    def get_2hop_neighborhood(self, node_id: str) -> Dict[str, Any]:
        """Extracts subgraph up to 2 hops away for visual inspection and graph evidence."""
        if node_id not in self.nx_graph:
            return {"nodes": [], "edges": []}

        nodes = {node_id}
        for n1 in self.get_1hop_neighbors(node_id):
            nodes.add(n1)
            for n2 in self.get_1hop_neighbors(n1):
                nodes.add(n2)

        subg = self.nx_graph.subgraph(nodes)
        node_records = []
        for n in subg.nodes():
            meta = self.node_attributes.get(n, {})
            node_records.append({
                "id": n,
                "type": meta.get("type", "Unknown"),
                "tx_count": meta.get("tx_count", 0),
            })

        edge_records = []
        for u, v, k, d in subg.edges(keys=True, data=True):
            edge_records.append({
                "source": u,
                "target": v,
                "relation": d.get("relation", "LINKED"),
                "tx_id": d.get("tx_id", ""),
                "amount": d.get("amount", 0.0),
                "is_fraud": d.get("is_fraud", 0),
            })

        return {"nodes": node_records, "edges": edge_records}

    def to_pyg_data(self, current_time: Optional[float] = None) -> Data:
        """Converts the current graph state into PyTorch Geometric Data tensor representation."""
        num_nodes = len(self.node_to_idx)
        if num_nodes == 0:
            return Data(
                x=torch.zeros((0, 8), dtype=torch.float32),
                edge_index=torch.zeros((2, 0), dtype=torch.long),
                edge_attr=torch.zeros((0, 3), dtype=torch.float32),
            )

        # Node feature matrix X (N x 8)
        x_mat = np.zeros((num_nodes, 8), dtype=np.float32)
        for nid, idx in self.node_to_idx.items():
            x_mat[idx] = self.node_attributes[nid]["features"]

        src_list, dst_list = [], []
        attr_list = []
        t_now = current_time if current_time is not None else time.time()

        for u, v, d in self.nx_graph.edges(data=True):
            u_i = self.node_to_idx[u]
            v_i = self.node_to_idx[v]
            src_list.append(u_i)
            dst_list.append(v_i)

            # Temporal decay weight: exp(-lambda * delta_t)
            edge_t = d.get("timestamp", t_now)
            delta_t = max(0.0, t_now - edge_t)
            decay_weight = math.exp(-self.time_decay_lambda * delta_t)

            amt = d.get("amount", 0.0)
            is_frd = float(d.get("is_fraud", 0))
            attr_list.append([decay_weight, math.log1p(amt), is_frd])

            # Undirected message-passing reciprocity
            src_list.append(v_i)
            dst_list.append(u_i)
            attr_list.append([decay_weight, math.log1p(amt), is_frd])

        x_tensor = torch.tensor(x_mat, dtype=torch.float32)
        edge_index = torch.tensor([src_list, dst_list], dtype=torch.long) if src_list else torch.zeros((2, 0), dtype=torch.long)
        edge_attr = torch.tensor(attr_list, dtype=torch.float32) if attr_list else torch.zeros((0, 3), dtype=torch.float32)

        return Data(x=x_tensor, edge_index=edge_index, edge_attr=edge_attr)
