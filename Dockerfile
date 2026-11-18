# syntax=docker/dockerfile:1
# Pokédex: one image, one process, one port (see docs/specs/deployment.md).
# Build context: the repository root, with pokedex.json present (not in git).

# --- 1. Frontend: only the built files reach the final image ----------------
FROM node:24-slim AS front
WORKDIR /front
RUN corepack enable pnpm
# Lockfile first: dependencies are reinstalled only when it changes.
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

# --- 2. Python dependencies, database and embedding model -------------------
FROM python:3.15-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    HF_HOME=/opt/hf

# Dependencies first (cached layer), then the project itself.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project
COPY README.md ./
COPY src ./src
# --no-editable: the venv holds the code, src/ is not needed at runtime.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

# Build pokedex.db here (reproducible); downloads the model into $HF_HOME.
COPY pokedex.json ./
COPY data ./data
RUN .venv/bin/pokedex-import --db /app/pokedex.db
# Fail the build if the model cannot be loaded offline, as it will be at runtime.
RUN HF_HUB_OFFLINE=1 .venv/bin/python -c \
    "from fullstack_pokedex.infrastructure.embeddings import Model2VecEmbedder; Model2VecEmbedder()"

# --- 3. Runtime: venv, model, database and built frontend only --------------
FROM python:3.15-slim
RUN useradd --system --no-create-home app \
    && mkdir /data && chown app /data
WORKDIR /app
# Same path as in the build stage: the venv's scripts use absolute paths.
COPY --from=build /app/.venv /app/.venv
COPY --from=build /opt/hf /opt/hf
COPY --from=build /app/pokedex.db /app/pokedex.db
COPY --from=front /front/dist /app/static

ENV PATH=/app/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    POKEDEX_HOST=0.0.0.0 \
    POKEDEX_PORT=8000 \
    POKEDEX_STATIC_DIR=/app/static \
    POKEDEX_DB=/app/pokedex.db \
    POKEDEX_FEEDBACK_DB=/data/feedback.db \
    HF_HOME=/opt/hf \
    HF_HUB_OFFLINE=1

USER app
VOLUME /data
EXPOSE 8000
# No curl in python:slim: Python is already here. Ignored by Kubernetes,
# which probes /api/health itself.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)"]
CMD ["fullstack-pokedex"]
