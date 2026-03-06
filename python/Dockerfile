# Build from project root:
# docker build -f python/Dockerfile -t gcr.io/snop-system/snop-upload .

FROM python:3.11-slim

WORKDIR /app

# System deps for pandas/numpy/openpyxl
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY python/requirements-cloudrun.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Application files (copy from project root context)
COPY python/app.py          ./app.py
COPY inventory_utils2.py    ./inventory_utils2.py
COPY utils.py               ./utils.py

ENV PORT=8080
EXPOSE 8080

# gunicorn: 1 worker + 16 threads (SSE support)
CMD exec gunicorn \
    --bind 0.0.0.0:$PORT \
    --workers 1 \
    --threads 16 \
    --timeout 3600 \
    --keep-alive 75 \
    --worker-class gthread \
    app:app
