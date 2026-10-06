"""FastAPI Production Server for Real-Time Graph Fraud Detection Platform."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api.app_state import platform_state
from api.routes import benchmark, graph, investigation, monitoring, scoring, streaming


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Prime platform state on startup: generate entities, fit models, establish baseline
    print("[FraudPlatform] Initializing platform state and warming up models...")
    platform_state.initialize(quick_warmup=True)
    print(f"[FraudPlatform] Platform initialized. Champion model: {platform_state.scoring_engine.champion_model_name}")
    yield
    print("[FraudPlatform] Shutting down platform...")


app = FastAPI(
    title="Real-Time Graph Fraud Detection Platform",
    description="Production-grade real-time fraud detection engine with dynamic heterogeneous graph topology, 8-model progression hierarchy, sub-second scoring, and live analyst console.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(scoring.router)
app.include_router(streaming.router)
app.include_router(graph.router)
app.include_router(benchmark.router)
app.include_router(monitoring.router)
app.include_router(investigation.router)


@app.get("/health", tags=["System Health"])
def healthcheck():
    """System health check and runtime state summary."""
    return {
        "status": "healthy",
        "service": "real-time-graph-fraud-platform",
        "version": "1.0.0",
        "is_initialized": platform_state.is_initialized,
        "champion_model": platform_state.scoring_engine.champion_model_name if platform_state.scoring_engine else None,
        "active_models": list(platform_state.scoring_engine.models.keys()) if platform_state.scoring_engine else [],
        "graph_nodes": platform_state.graph.nx_graph.number_of_nodes() if platform_state.graph else 0,
        "graph_edges": platform_state.graph.nx_graph.number_of_edges() if platform_state.graph else 0,
        "active_alerts": len(platform_state.alerts),
        "recent_transactions": len(platform_state.recent_transactions),
    }


# Mount static frontend build if present
frontend_dist_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.exists(frontend_dist_path):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist_path, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Serve index.html for frontend client routing if file doesn't exist
        file_candidate = os.path.join(frontend_dist_path, full_path)
        if full_path and os.path.exists(file_candidate) and os.path.isfile(file_candidate):
            return FileResponse(file_candidate)
        return FileResponse(os.path.join(frontend_dist_path, "index.html"))
