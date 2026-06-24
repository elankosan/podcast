#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# One-Command Deployment Script
# =============================================================================
# Usage: ./scripts/deploy.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"
COMPOSE_FILE="${PROJECT_DIR}/docker-compose.prod.yml"
ENV_FILE="${PROJECT_DIR}/.env"
API_HEALTH_URL=""
MAX_RETRIES=30
RETRY_INTERVAL=5

echo "=== Multi-Lingual Podcast Deployment ==="
echo "Project dir: ${PROJECT_DIR}"

# =============================================================================
# Load environment variables
# =============================================================================
if [[ -f "${ENV_FILE}" ]]; then
    echo "=== Loading environment from .env ==="
    set -a
    source "${ENV_FILE}"
    set +a
else
    echo "WARNING: No .env file found at ${ENV_FILE}"
    echo "Ensure environment variables are exported before running this script."
fi

# Validate required vars
REQUIRED_VARS=("DOMAIN" "POSTGRES_PASSWORD" "NEO4J_PASSWORD" "KIMI_API_KEY" "SECRET_KEY" "ACME_EMAIL")
for var in "${REQUIRED_VARS[@]}"; do
    if [[ -z "${!var:-}" ]]; then
        echo "ERROR: Required environment variable ${var} is not set."
        exit 1
    fi
done

API_HEALTH_URL="https://api.${DOMAIN}/health"

cd "${PROJECT_DIR}"

# =============================================================================
# Docker Compose CLI Detection
# =============================================================================
COMPOSE_CMD="docker compose"
if ! command -v docker &> /dev/null || ! docker compose version &> /dev/null; then
    COMPOSE_CMD="docker-compose"
fi
echo "=== Using compose command: ${COMPOSE_CMD} ==="

# =============================================================================
# Git Pull
# =============================================================================
if [[ -d ".git" ]]; then
    echo "=== Pulling latest changes ==="
    git pull origin main || git pull origin master || echo "WARNING: Git pull failed, continuing with local code."
else
    echo "WARNING: Not a git repository, skipping git pull."
fi

# =============================================================================
# Docker Compose Build & Up
# =============================================================================
echo "=== Building and starting services ==="

# Tag current images for rollback
ROLLBACK_TAG="rollback-$(date +%Y%m%d-%H%M%S)"
echo "=== Tagging current images for rollback: ${ROLLBACK_TAG} ==="
for service in api app; do
    IMAGE=$(${COMPOSE_CMD} -f "${COMPOSE_FILE}" -p multi-lingual-podcast images -q "${service}" 2>/dev/null || true)
    if [[ -n "${IMAGE:-}" ]]; then
        docker tag "${IMAGE}" "multi-lingual-podcast-${service}:${ROLLBACK_TAG}" || true
    fi
done

${COMPOSE_CMD} -f "${COMPOSE_FILE}" -p multi-lingual-podcast pull || true
${COMPOSE_CMD} -f "${COMPOSE_FILE}" -p multi-lingual-podcast build --no-cache
${COMPOSE_CMD} -f "${COMPOSE_FILE}" -p multi-lingual-podcast up -d

# =============================================================================
# Health Check
# =============================================================================
echo "=== Waiting for services to be healthy ==="
echo "Health check URL: ${API_HEALTH_URL}"

HEALTHY=false
for i in $(seq 1 ${MAX_RETRIES}); do
    if curl -fsS "${API_HEALTH_URL}" > /dev/null 2>&1; then
        echo "API is healthy!"
        HEALTHY=true
        break
    fi
    echo "Attempt ${i}/${MAX_RETRIES}: API not ready yet, waiting ${RETRY_INTERVAL}s..."
    sleep ${RETRY_INTERVAL}
done

if [[ "${HEALTHY}" != "true" ]]; then
    echo "ERROR: Health check failed after ${MAX_RETRIES} attempts."
    echo "=== Rolling back deployment ==="

    for service in api app; do
        ROLLBACK_IMAGE="multi-lingual-podcast-${service}:${ROLLBACK_TAG}"
        if docker image inspect "${ROLLBACK_IMAGE}" > /dev/null 2>&1; then
            echo "Rolling back ${service} to ${ROLLBACK_IMAGE}"
            ${COMPOSE_CMD} -f "${COMPOSE_FILE}" -p multi-lingual-podcast stop "${service}" || true
            ${COMPOSE_CMD} -f "${COMPOSE_FILE}" -p multi-lingual-podcast rm -f "${service}" || true
            # Run the old image directly
            docker run -d --name "multi-lingual-podcast-${service}-rollback" \
                --network multi-lingual-podcast_backend \
                --network multi-lingual-podcast_frontend \
                "${ROLLBACK_IMAGE}" || true
        fi
    done

    echo "Rollback attempted. Please check container status manually."
    exit 1
fi

# =============================================================================
# Cleanup
# =============================================================================
echo "=== Cleaning up old images ==="
docker image prune -f || true

echo "=== Deployment successful! ==="
echo "App:      https://${DOMAIN}"
echo "API:      https://api.${DOMAIN}"
echo "Traefik:  https://traefik.${DOMAIN}"
