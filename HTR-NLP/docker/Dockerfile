# Handwriting recognition service. Build context: ./HTR-NLP (see docker-compose.yml).
FROM python:3.10-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN useradd --create-home --shell /usr/sbin/nologin appuser

COPY service/requirements.txt ./service-requirements.txt

# CPU-only torch keeps the image about 2 GB smaller. On a GPU server, drop the
# --index-url option and run the container with GPU access.
RUN python -m pip install --upgrade pip \
    && python -m pip install "torch>=2.2,<3" --index-url https://download.pytorch.org/whl/cpu \
    && python -m pip install -r service-requirements.txt

COPY configs ./configs
COPY scripts ./scripts
COPY service ./service
COPY outputs/bullinger_htr_delivery/scripts ./outputs/bullinger_htr_delivery/scripts
COPY outputs/bullinger_htr_delivery/data/historical_aliases.json outputs/bullinger_htr_delivery/data/source_aliases.json ./outputs/bullinger_htr_delivery/data/

# The models (about 3 GB) are NOT baked in. Mount them, see docker-compose.yml:
#   HTR-NLP/models -> /app/models
USER appuser

EXPOSE 8000

CMD ["uvicorn", "service.app:app", "--host", "0.0.0.0", "--port", "8000"]
