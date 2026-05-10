FROM python:3.12-slim-trixie

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app

COPY pyproject.toml ./
COPY cloud_backend/pyproject.toml ./cloud_backend/
COPY shared/pyproject.toml ./shared/
COPY local_agent/pyproject.toml ./local_agent/
COPY frontend/pyproject.toml ./frontend/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-workspace

COPY . .

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync

WORKDIR /app/cloud_backend
EXPOSE 8000
ENV PATH="/app/.venv/bin:$PATH"

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
