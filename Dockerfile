FROM python:3.13-slim-bookworm AS builder

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency files first
COPY pyproject.toml  ./

# Install dependencies using uv
RUN uv sync --frozen --no-dev

# ── Runtime image ──────────────────────────────────────────────
FROM python:3.13-slim-bookworm

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/usr/local/bin:$PATH"

# Install system libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app
# Copy project source
COPY . .

# Collect static files (dummy DB just for collectstatic)
RUN touch db.sqlite3 && python manage.py collectstatic --no-input --clear

EXPOSE 8000

CMD ["gunicorn", "myproject.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "120"]
