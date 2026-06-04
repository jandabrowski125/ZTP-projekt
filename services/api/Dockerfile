FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY services/api ./services/api

RUN pip install --no-cache-dir \
    "fastapi>=0.115.0" \
    "uvicorn[standard]>=0.32.0" \
    "httpx>=0.28.0" \
    "pydantic[email]>=2.10.0" \
    "pydantic-settings>=2.6.0"

ENV PYTHONPATH=/app/services/api
ENV API_HOST=0.0.0.0
ENV API_PORT=8000
ENV EVENTS_SERVICE_URL=http://events-service:8001
ENV USER_SERVICE_URL=http://user-service:8002

EXPOSE 8000

CMD ["uvicorn", "gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
