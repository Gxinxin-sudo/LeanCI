# syntax=docker/dockerfile:1

FROM node:24.16.0-bookworm-slim AS frontend-build

WORKDIR /build/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/index.html frontend/tsconfig.json frontend/tsconfig.app.json ./
COPY frontend/tsconfig.node.json frontend/vite.config.ts ./
COPY frontend/src ./src
RUN npm run build


FROM python:3.12.13-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ENVIRONMENT=production \
    LLM_PROVIDER=paritok \
    PORT=8000

WORKDIR /app

RUN groupadd --gid 10001 leanci \
    && useradd --uid 10001 --gid 10001 --create-home --no-log-init leanci

COPY backend/requirements-container.txt /tmp/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --upgrade "pip==26.1.2" \
    && python -m pip install --requirement /tmp/requirements.txt

COPY --chown=10001:10001 backend/app /app/backend/app
COPY --chown=10001:10001 benchmarks /app/benchmarks
COPY --chown=10001:10001 examples /app/examples
COPY --chown=10001:10001 paritok.yaml /app/paritok.yaml
COPY --chown=10001:10001 scripts/container_entrypoint.py /app/scripts/container_entrypoint.py
COPY --from=frontend-build --chown=10001:10001 /build/frontend/dist /app/frontend/dist

RUN mkdir -p /app/runtime \
    && chown 10001:10001 /app/runtime

USER 10001:10001

EXPOSE 8000
STOPSIGNAL SIGTERM

HEALTHCHECK --interval=30s --timeout=15s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import json,os,urllib.request; port=os.environ.get('PORT','8000'); data=json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health',timeout=12)); assert data['service']=='leanci-api' and data['paritok_connected'] is True"]

ENTRYPOINT ["python", "/app/scripts/container_entrypoint.py"]
