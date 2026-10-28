FROM python:3.10-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN useradd --create-home --shell /usr/sbin/nologin appuser

COPY requirements.txt ./requirements.txt

# CPU-only torch keeps the image ~2 GB smaller. For a GPU server, drop the
# --index-url line and run the container with GPU access.
RUN python -m pip install --upgrade pip \
    && python -m pip install "torch>=2.2,<3" --index-url https://download.pytorch.org/whl/cpu \
    && python -m pip install -r requirements.txt

COPY configs ./configs
COPY data ./data
COPY scripts ./scripts
COPY service ./service

# Models are NOT baked in (several GB). Mount them, see docker-compose.yml:
#   htr/models -> /app/models     htr/.cache -> /app/.cache
USER appuser

EXPOSE 8000

CMD ["uvicorn", "service.app:app", "--host", "0.0.0.0", "--port", "8000"]
