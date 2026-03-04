# === Base stage: install dependencies ===
FROM python:3.13-slim AS base

WORKDIR /app

# Install uv for fast dependency resolution
RUN pip install --no-cache-dir uv

# Copy dependency definition (layer caching)
COPY pyproject.toml .

# Install production dependencies
RUN uv pip install --system .

# === Production stage ===
FROM python:3.13-slim AS production

WORKDIR /app

COPY --from=base /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=base /usr/local/bin /usr/local/bin

COPY app/ app/
COPY config/ config/

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/api/health').raise_for_status()"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# === Development stage ===
FROM base AS development

# Install dev dependencies
RUN uv pip install --system ".[dev]"

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
