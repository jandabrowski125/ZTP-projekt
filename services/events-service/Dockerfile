FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY services/events-service ./services/events-service

RUN pip install --no-cache-dir \
    "fastapi>=0.115.0" \
    "uvicorn[standard]>=0.32.0" \
    "httpx>=0.28.0" \
    "pydantic>=2.10.0" \
    "pydantic-settings>=2.6.0"

ENV PYTHONPATH=/app/services/events-service
ENV EVENTS_SERVICE_HOST=0.0.0.0
ENV EVENTS_SERVICE_PORT=8001

EXPOSE 8001

CMD ["uvicorn", "events_app.main:app", "--host", "0.0.0.0", "--port", "8001"]
