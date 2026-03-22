# ── Stage 1: build the React frontend ─────────────────────────────────────────
FROM node:22-slim AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build


# ── Stage 2: Python runtime ────────────────────────────────────────────────────
FROM python:3.13-slim

WORKDIR /app/backend

# Install dependencies first (layer cache)
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ ./

# Copy built frontend into the location main.py expects
COPY --from=frontend-builder /app/frontend/dist ../frontend/dist

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
