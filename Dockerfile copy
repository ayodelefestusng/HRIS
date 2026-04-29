# 1. Use a lightweight Python image
# FROM python:3.11-slim
FROM python:3.12-slim

# 2. Set environment variables
# Prevents Python from writing .pyc files and ensures output is sent straight to terminal
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONUTF8=1
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# 3. Set working directory
WORKDIR /code

# 4. Install system dependencies
# We need build-essential and libpq-dev for psycopg2 (PostgreSQL driver)
# We need libjpeg and zlib for Pillow (Image processing)
# Install system dependencies for pycairo and psycopg2
RUN apt-get update && apt-get install -y \
    pkg-config \
    libcairo2-dev \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /code

# Install python dependencies
COPY requirements.txt /code/
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . /code/

# 7. Django-specific configuration
ENV DJANGO_SETTINGS_MODULE=myproject.settings

# Run collectstatic. The '|| true' ensures the build doesn't fail if 
# the DB isn't connected yet (common during the build phase).
RUN python manage.py collectstatic --noinput --clear || true

# 8. Expose the port Gunicorn will run on
EXPOSE 8000

# 9. Start the application using Gunicorn
CMD ["gunicorn", "myproject.wsgi:application", "-b", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]