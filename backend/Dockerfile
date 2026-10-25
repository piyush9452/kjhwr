# Build context: repository root (see docker-compose.yml).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/app backend/app
COPY scripts scripts
COPY data data

RUN useradd --system --uid 10001 --no-create-home app
USER app

WORKDIR /srv/backend
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 CMD python -c "import urllib.request,sys; urllib.request.urlopen('http://localhost:8000/api/health'); sys.exit(0)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
