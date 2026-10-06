# Stage 1: Build React/TypeScript Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Production Python API Service
FROM python:3.13-slim
WORKDIR /app

# Install system utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY api/ ./api/
COPY simulation/ ./simulation/
COPY streaming/ ./streaming/
COPY feature_store/ ./feature_store/
COPY graph/ ./graph/
COPY models/ ./models/
COPY scoring/ ./scoring/
COPY monitoring/ ./monitoring/
COPY eval/ ./eval/

# Copy built frontend assets
COPY --from=frontend-builder /build/dist ./frontend/dist

# Expose API and UI port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Launch production server
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
