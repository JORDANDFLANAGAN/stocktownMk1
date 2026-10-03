# Stage 1: build the Vue frontend into static files.
FROM node:26-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: the Python app, which also serves the built frontend.
FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.19 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev
COPY stocktown/ ./stocktown/
COPY --from=frontend /app/frontend/dist ./frontend/dist
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
# Railway sets PORT. `exec` makes uvicorn receive the stop signal, so it closes the Alpaca socket cleanly.
CMD ["sh", "-c", "exec uvicorn stocktown.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
