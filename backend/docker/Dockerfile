FROM python:3.10-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential gcc libpq-dev libgomp1 libpq5 curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /usr/sbin/nologin appuser

COPY requirements.txt ./requirements.txt

RUN python -m pip install --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 3000

# Serve FastAPI with uvicorn on container port 3000 (mapped to host 3011 in
# docker-compose.yml).
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3000"]
