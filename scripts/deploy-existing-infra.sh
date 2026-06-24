#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"
COMPOSE_FILE="${PROJECT_DIR}/docker-compose.existing-infra.yml"
ENV_FILE="${PROJECT_DIR}/.env"
PROJECT_NAME="multi-lingual-podcast"
NETWORK_NAME="${TRAEFIK_DOCKER_NETWORK:-proxy}"
DB_NETWORK_NAME="${EXTERNAL_DB_NETWORK:-promethea_promethea_internal}"

echo "=== Multi-Lingual Podcast Deployment (existing infra) ==="
echo "Project dir: ${PROJECT_DIR}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "ERROR: Missing ${ENV_FILE}."
  echo "Create it from .env.podcast.digity.dev.example and set real values."
  exit 1
fi

set -a
source "${ENV_FILE}"
set +a

REQUIRED_VARS=("DOMAIN" "EXTERNAL_DATABASE_URL" "NEO4J_PASSWORD" "KIMI_API_KEY" "SECRET_KEY")
for var in "${REQUIRED_VARS[@]}"; do
  if [[ -z "${!var:-}" ]]; then
    echo "ERROR: Required environment variable ${var} is not set."
    exit 1
  fi
done

if ! docker network inspect "${NETWORK_NAME}" >/dev/null 2>&1; then
  echo "ERROR: Docker network '${NETWORK_NAME}' not found."
  echo "Set TRAEFIK_DOCKER_NETWORK in .env to your existing proxy network name."
  exit 1
fi

if ! docker network inspect "${DB_NETWORK_NAME}" >/dev/null 2>&1; then
  echo "ERROR: External DB network '${DB_NETWORK_NAME}' not found."
  echo "Set EXTERNAL_DB_NETWORK in .env to the network that contains your existing postgres container."
  exit 1
fi

COMPOSE_CMD="docker compose"
if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD="docker-compose"
fi

echo "=== Using compose command: ${COMPOSE_CMD} ==="
echo "=== Using external proxy network: ${NETWORK_NAME} ==="
echo "=== Using external DB network: ${DB_NETWORK_NAME} ==="
echo "=== No new Traefik or Postgres containers will be created ==="

cd "${PROJECT_DIR}"

${COMPOSE_CMD} -f "${COMPOSE_FILE}" -p "${PROJECT_NAME}" pull || true
${COMPOSE_CMD} -f "${COMPOSE_FILE}" -p "${PROJECT_NAME}" build --no-cache
${COMPOSE_CMD} -f "${COMPOSE_FILE}" -p "${PROJECT_NAME}" up -d

# Run migrations against external PostgreSQL
${COMPOSE_CMD} -f "${COMPOSE_FILE}" -p "${PROJECT_NAME}" exec -T -w /app/api api sh -lc 'PYTHONPATH=/app python -m alembic upgrade head'

echo "=== Waiting for api container health ==="
MAX_RETRIES=30
RETRY_INTERVAL=5
HEALTHY=false
for i in $(seq 1 ${MAX_RETRIES}); do
  STATUS=$(docker inspect --format='{{.State.Health.Status}}' multi-lingual-podcast-api 2>/dev/null || echo "unknown")
  if [[ "${STATUS}" == "healthy" ]]; then
    HEALTHY=true
    break
  fi
  echo "Attempt ${i}/${MAX_RETRIES}: api health is '${STATUS}', waiting ${RETRY_INTERVAL}s..."
  sleep ${RETRY_INTERVAL}
done

if [[ "${HEALTHY}" != "true" ]]; then
  echo "ERROR: API container did not become healthy."
  exit 1
fi

echo "=== Deployment successful (existing infra mode) ==="
echo "App: https://${DOMAIN}"
echo "API: https://api.${DOMAIN}/health"
