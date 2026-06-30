# Backend: FastAPI + SQLite, installed with uv (matches the local workflow).
FROM python:3.12-slim

# uv for fast, reproducible installs (copied from the official uv image).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Install the project + its runtime deps into the system environment. Editable
# so the package data (app/eval/gold_set.json) resolves from the source tree.
COPY pyproject.toml ./
COPY app ./app
RUN uv pip install --system -e .

EXPOSE 8000

# 0.0.0.0 so the port is reachable from outside the container.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
