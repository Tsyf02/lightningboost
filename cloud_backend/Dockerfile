FROM python:3.12-slim-trixie

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# 1. Copy workspace root + member pyproject.toml files for dependency caching
COPY pyproject.toml uv.lock ./
COPY cloud_backend/pyproject.toml ./cloud_backend/
COPY shared/pyproject.toml ./shared/
COPY local_agent/pyproject.toml ./local_agent/
COPY frontend/pyproject.toml ./frontend/

# 2. Install dependencies only (skip workspace projects for cache efficiency)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-workspace

# 3. Copy the rest of the source code
COPY . .

# 4. Install the workspace projects themselves
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app/cloud_backend
EXPOSE 8000


CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]