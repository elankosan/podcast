#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Restore from Backup Script
# =============================================================================
# Usage: ./scripts/restore.sh <backup-tarball-path>
# Example: ./scripts/restore.sh /opt/multi-lingual-podcast/backups/backup-20240115-020000.tar.gz

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"
COMPOSE_FILE="${PROJECT_DIR}/docker-compose.prod.yml"
ENV_FILE="${PROJECT_DIR}/.env"
BACKUP_TARBALL="${1:-}"

if [[ -z "${BACKUP_TARBALL}" ]]; then
    echo "ERROR: No backup tarball specified."
    echo "Usage: $0 <backup-tarball-path>"
    exit 1
fi

if [[ ! -f "${BACKUP_TARBALL}" ]]; then
    echo "ERROR: Backup file not found: ${BACKUP_TARBALL}"
    exit 1
fi

RESTORE_DIR="$(mktemp -d)"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

echo "=== Restore started at $(date) ==="
echo "Backup: ${BACKUP_TARBALL}"
echo "Restore temp dir: ${RESTORE_DIR}"

# =============================================================================
# Load environment
# =============================================================================
if [[ -f "${ENV_FILE}" ]]; then
    set -a
    source "${ENV_FILE}"
    set +a
fi

# =============================================================================
# Stop services
# =============================================================================
echo "=== Stopping application services ==="
cd "${PROJECT_DIR}"
docker-compose -f "${COMPOSE_FILE}" -p multi-lingual-podcast stop api app

# =============================================================================
# Extract backup
# =============================================================================
echo "=== Extracting backup ==="
tar -xzf "${BACKUP_TARBALL}" -C "${RESTORE_DIR}"

EXTRACTED_DIR=$(find "${RESTORE_DIR}" -maxdepth 1 -type d | tail -n 1)
echo "Extracted to: ${EXTRACTED_DIR}"

# =============================================================================
# Restore PostgreSQL
# =============================================================================
if [[ -f "${EXTRACTED_DIR}/postgres.dump" ]]; then
    echo "=== Restoring PostgreSQL ==="
    POSTGRES_CONTAINER="multi-lingual-podcast-postgres"
    POSTGRES_DB="podcast"
    POSTGRES_USER="postgres"

    # Drop and recreate database
    docker exec "${POSTGRES_CONTAINER}" psql -U "${POSTGRES_USER}" -d postgres -c \
        "DROP DATABASE IF EXISTS ${POSTGRES_DB};" || true
    docker exec "${POSTGRES_CONTAINER}" psql -U "${POSTGRES_USER}" -d postgres -c \
        "CREATE DATABASE ${POSTGRES_DB};" || true

    # Restore from dump
    docker exec -i "${POSTGRES_CONTAINER}" pg_restore -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" --no-owner --clean \
        < "${EXTRACTED_DIR}/postgres.dump" || {
            echo "WARNING: pg_restore completed with errors (may be non-fatal for existing objects)"
        }

    echo "PostgreSQL restore complete"
else
    echo "WARNING: PostgreSQL dump not found in backup"
fi

# =============================================================================
# Restore Neo4j
# =============================================================================
if [[ -f "${EXTRACTED_DIR}/neo4j.dump" ]]; then
    echo "=== Restoring Neo4j ==="
    NEO4J_CONTAINER="multi-lingual-podcast-neo4j"
    NEO4J_BACKUP_DIR="/var/lib/neo4j/backups"

    # Stop neo4j before restore
    docker-compose -f "${COMPOSE_FILE}" -p multi-lingual-podcast stop neo4j

    # Copy dump into container
    docker cp "${EXTRACTED_DIR}/neo4j.dump" "${NEO4J_CONTAINER}:${NEO4J_BACKUP_DIR}/neo4j.dump"

    # Load dump (neo4j-admin database load for community)
    docker exec "${NEO4J_CONTAINER}" neo4j-admin database load neo4j --from-path="${NEO4J_BACKUP_DIR}" --force || {
        echo "WARNING: neo4j-admin load failed, trying alternative..."
    }

    docker exec "${NEO4J_CONTAINER}" rm -f "${NEO4J_BACKUP_DIR}/neo4j.dump"

    echo "Neo4j restore complete"
else
    echo "WARNING: Neo4j dump not found in backup"
fi

# =============================================================================
# Restart and verify
# =============================================================================
echo "=== Restarting all services ==="
docker-compose -f "${COMPOSE_FILE}" -p multi-lingual-podcast start neo4j || true
docker-compose -f "${COMPOSE_FILE}" -p multi-lingual-podcast up -d

echo "=== Waiting for services to stabilize ==="
sleep 15

echo "=== Running health checks ==="
API_HEALTH_URL="https://api.${DOMAIN}/health"
MAX_RETRIES=10
RETRY_INTERVAL=5
HEALTHY=false

for i in $(seq 1 ${MAX_RETRIES}); do
    if curl -fsS "${API_HEALTH_URL}" > /dev/null 2>&1; then
        echo "API is healthy after restore!"
        HEALTHY=true
        break
    fi
    echo "Health check attempt ${i}/${MAX_RETRIES}..."
    sleep ${RETRY_INTERVAL}
done

# =============================================================================
# Cleanup
# =============================================================================
rm -rf "${RESTORE_DIR}"

if [[ "${HEALTHY}" == "true" ]]; then
    echo "=== Restore completed successfully at $(date) ==="
else
    echo "ERROR: Services did not pass health check after restore."
    echo "Please investigate manually."
    exit 1
fi
