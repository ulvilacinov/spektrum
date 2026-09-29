# One image: the FastAPI backend serving the built React frontend.

FROM node:24-slim AS frontend
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app/backend

COPY backend/pyproject.toml backend/README.md ./
COPY backend/app ./app
RUN pip install .
COPY backend/alembic ./alembic
COPY backend/alembic.ini ./
COPY --from=frontend /src/frontend/dist /app/frontend/dist

RUN useradd --system --uid 10001 --user-group --no-create-home app \
    && mkdir -p /data/uploads && chown app:app /data/uploads
# Starts as root only to take over the mounted uploads volume, then drops to "app".
COPY --chmod=755 docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

ENV ENVIRONMENT=production \
    FRONTEND_DIST_DIR=/app/frontend/dist \
    UPLOAD_DIR=/data/uploads \
    SESSION_COOKIE_SECURE=true
EXPOSE 8000

# Migrations run before each deploy (fly.toml release_command: alembic upgrade head).
# Behind the hosting proxy, trust X-Forwarded-For so the login throttle sees the client.
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*", "--timeout-graceful-shutdown", "10"]
