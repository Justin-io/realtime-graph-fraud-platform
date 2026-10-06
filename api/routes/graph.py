"""Graph API routes for dynamic heterogeneous topology exploration and fraud ring detection."""

from __future__ import annotations

from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, Query
from api.app_state import platform_state

router = APIRouter(prefix="/api/graph", tags=["Heterogeneous Graph"])


@router.get("/entity/{entity_id}")
def get_entity_neighborhood(
    entity_id: str,
    max_hops: int = Query(2, ge=1, le=3),
):
    """Retrieves 2-hop ego-network around an entity for interactive graph rendering."""
    if not platform_state.is_initialized:
        platform_state.initialize()

    nx_g = platform_state.graph.nx_graph
    if entity_id not in nx_g:
        # Search for case-insensitive match or prefix
        candidates = [n for n in nx_g.nodes if n.upper() == entity_id.upper()]
        if not candidates:
            raise HTTPException(
                status_code=404,
                detail=f"Entity '{entity_id}' not found in active entity graph.",
            )
        entity_id = candidates[0]

    neighborhood = platform_state.graph.get_2hop_neighborhood(entity_id)

    # Format nodes and edges with visual styling metadata
    type_color_map = {
        "User": "#3B82F6",      # Blue
        "Card": "#10B981",      # Emerald Green
        "Device": "#F59E0B",    # Amber
        "IP": "#8B5CF6",        # Purple
        "Merchant": "#EC4899",  # Pink
        "Address": "#64748B",   # Slate Grey
    }

    formatted_nodes = []
    for n in neighborhood.get("nodes", []):
        ntype = n.get("type", "Unknown")
        formatted_nodes.append({
            "id": n["id"],
            "label": f"{ntype}: {n['id']}",
            "type": ntype,
            "color": type_color_map.get(ntype, "#6B7280"),
            "degree": nx_g.degree(n["id"]) if n["id"] in nx_g else 1,
            "is_center": n["id"] == entity_id,
        })

    formatted_edges = []
    for e in neighborhood.get("edges", []):
        formatted_edges.append({
            "source": e["source"],
            "target": e["target"],
            "relation": e.get("relation", "CONNECTED_TO"),
            "weight": round(e.get("weight", 1.0), 3),
        })

    return {
        "center_node": entity_id,
        "node_count": len(formatted_nodes),
        "edge_count": len(formatted_edges),
        "nodes": formatted_nodes,
        "edges": formatted_edges,
    }


@router.get("/rings")
def get_detected_fraud_rings(min_users: int = Query(3, ge=2, le=20)):
    """Extracts all active syndicated fraud rings and shared hardware hubs."""
    if not platform_state.is_initialized:
        platform_state.initialize()

    rings = platform_state.ring_detector.detect_active_fraud_rings(min_users_threshold=min_users)

    return {
        "active_ring_count": len(rings),
        "rings": [r.model_dump() for r in rings],
    }


@router.get("/stats")
def get_graph_statistics():
    """Returns top-level topology statistics across all heterogeneous entity and edge classes."""
    if not platform_state.is_initialized:
        platform_state.initialize()

    nx_g = platform_state.graph.nx_graph

    node_counts_by_type: Dict[str, int] = {}
    for _, data in nx_g.nodes(data=True):
        t = data.get("type", "Unknown")
        node_counts_by_type[t] = node_counts_by_type.get(t, 0) + 1

    edge_counts_by_relation: Dict[str, int] = {}
    for _, _, data in nx_g.edges(data=True):
        rel = data.get("relation", "RELATION")
        edge_counts_by_relation[rel] = edge_counts_by_relation.get(rel, 0) + 1

    total_nodes = nx_g.number_of_nodes()
    total_edges = nx_g.number_of_edges()

    return {
        "total_nodes": total_nodes,
        "total_edges": total_edges,
        "node_types": node_counts_by_type,
        "edge_relations": edge_counts_by_relation,
        "density": round(float(total_edges / max(1, total_nodes * (total_nodes - 1))), 6)
        if total_nodes > 1
        else 0.0,
    }
