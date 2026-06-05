FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY services/common ./services/common
COPY services/user-service ./services/user-service

RUN pip install --no-cache-dir \
    "fastapi>=0.115.0" \
    "uvicorn[standard]>=0.32.0" \
    "httpx>=0.28.0" \
    "pydantic[email]>=2.10.0" \
    "pydantic-settings>=2.6.0" \
    "sqlalchemy>=2.0.36" \
    "psycopg[binary]>=3.2.0" \
    "alembic>=1.14.0" \
    "passlib[bcrypt]>=1.7.4" \
    "bcrypt>=4.0.1,<4.1" \
    "PyJWT>=2.10.0" \
    "pytest>=8.3.0"

ENV PYTHONPATH=/app/services/user-service:/app/services/common
ENV USER_SERVICE_HOST=0.0.0.0
ENV USER_SERVICE_PORT=8002

EXPOSE 8002

WORKDIR /app/services/user-service
CMD ["sh", "-c", "python -m user_app.db.bootstrap && exec uvicorn user_app.main:app --host 0.0.0.0 --port 8002"]
