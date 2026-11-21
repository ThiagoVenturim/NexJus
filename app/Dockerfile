FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    NEXJUS_DATABASE_URL=sqlite:////data/nexjus.db

COPY pyproject.toml README.md alembic.ini ./
COPY src ./src
RUN pip install ".[postgres]" \
    && useradd --create-home --uid 10001 nexjus \
    && mkdir -p /data \
    && chown nexjus:nexjus /data

USER nexjus
VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"]

CMD ["nexjus-backend", "serve", "--host", "0.0.0.0", "--port", "8000"]
