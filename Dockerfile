FROM python:3.11-slim

LABEL org.opencontainers.image.source="https://github.com/arrana16/evidence-trail-lab"
LABEL org.opencontainers.image.description="OpenEnv source-aware investigation tasks"

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md /app/
COPY evidence_trail /app/evidence_trail
RUN pip install --no-cache-dir .

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"
CMD ["uvicorn", "evidence_trail.server.app:app", "--host", "0.0.0.0", "--port", "8000"]
