# Digital Munshi ERP — production container (Railway/Render/any Docker host)
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System libs (Pillow, psycopg2, reportlab/xhtml2pdf ke liye safe)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev libjpeg-dev zlib1g-dev libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Static files build-time pe collect (DEBUG default, DB nahi chahiye)
RUN python manage.py collectstatic --noinput || true

EXPOSE 8000

# Container start: migrate + gunicorn ($PORT Railway deta hai)
CMD python manage.py migrate --noinput && \
    gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3 --timeout 120
