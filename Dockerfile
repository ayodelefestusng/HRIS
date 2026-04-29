# ── Build stage ───────────────────────────────────────────────
FROM python:3.13-slim-bookworm AS builder

WORKDIR /app

# Install build tools and native dependencies for pycairo, psycopg2, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libcairo2-dev pkg-config python3-dev libpq-dev \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv (reproducible)
RUN uv sync --frozen --no-dev

# ── Runtime image ──────────────────────────────────────────────
FROM python:3.13-slim-bookworm

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/usr/local/bin:$PATH"

# Install runtime system libraries only (no compilers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy the virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
COPY --from=builder /app /app

# Copy project source
COPY . .

# Collect static files (dummy DB just for collectstatic)
RUN touch db.sqlite3 && python manage.py collectstatic --no-input --clear

EXPOSE 8000

CMD ["gunicorn", "myproject.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]