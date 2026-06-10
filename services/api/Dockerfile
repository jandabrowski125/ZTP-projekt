FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY services/common ./services/common
COPY services/api ./services/api

RUN pip install --no-cache-dir \
    "fastapi>=0.115.0" \
    "uvicorn[standard]>=0.32.0" \
    "httpx>=0.28.0" \
    "pydantic[email]>=2.10.0" \
    "pydantic-settings>=2.6.0" \
    "sqlalchemy>=2.0.36" \
    "psycopg[binary]>=3.2.0" \
    "psycopg2-binary>=2.9.0" \
    "alembic>=1.14.0" \
    "passlib[bcrypt]>=1.7.4" \
    "PyJWT>=2.10.0" \
    "google-auth>=2.36.0" \
    "firebase-admin>=7.4.0" \
    "requests>=2.32.0"

ENV PYTHONPATH=/app/services/api:/app/services/common
ENV API_HOST=0.0.0.0
ENV API_PORT=8000
ENV EVENTS_SERVICE_URL=http://events-service:8001
ENV USER_SERVICE_URL=http://user-service:8002

EXPOSE 8000

CMD ["uvicorn", "gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
