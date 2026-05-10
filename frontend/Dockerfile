FROM python:3.12-slim-trixie

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY cloud_backend/pyproject.toml ./cloud_backend/
COPY shared/pyproject.toml ./shared/
COPY local_agent/pyproject.toml ./local_agent/
COPY frontend/pyproject.toml ./frontend/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-workspace

COPY . .

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app/frontend
EXPOSE 8501

CMD ["run", "streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]