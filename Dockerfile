FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MINERU_DATA_AGENT_OUTPUT_DIR=/app/runs/api \
    MINERU_DATA_AGENT_ALLOWED_OUTPUT_BASE=/app \
    MINERU_DATA_AGENT_MAX_UPLOAD_MB=200

WORKDIR /app

RUN python -m pip install --no-cache-dir --upgrade pip

COPY pyproject.toml README.md LICENSE ./
COPY src ./src

RUN python -m pip install --no-cache-dir .

RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && mkdir -p /app/runs/api \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8080

CMD ["uvicorn", "mineru_data_agent.api:app", "--host", "0.0.0.0", "--port", "8080"]
