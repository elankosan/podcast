#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Automated Backup Script
# =============================================================================
# Usage: ./scripts/backup.sh
# Crontab: 0 2 * * * /opt/multi-lingual-podcast/scripts/backup.sh >> /var/log/multi-lingual-podcast/backup.log 2>&1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"
COMPOSE_FILE="${PROJECT_DIR}/docker-compose.prod.yml"
ENV_FILE="${PROJECT_DIR}/.env"
BACKUP_DIR="${PROJECT_DIR}/backups"
RETENTION_DAYS=7
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_NAME="backup-${TIMESTAMP}"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"

mkdir -p "${BACKUP_PATH}"

echo "=== Backup started at $(date) ==="
echo "Backup path: ${BACKUP_PATH}"

# =============================================================================
# Load environment
# =============================================================================
if [[ -f "${ENV_FILE}" ]]; then
    set -a
    source "${ENV_FILE}"
    set +a
fi

# =============================================================================
# PostgreSQL Backup
# =============================================================================
echo "=== Backing up PostgreSQL ==="
POSTGRES_CONTAINER="multi-lingual-podcast-postgres"
POSTGRES_DB="podcast"
POSTGRES_USER="postgres"

docker exec "${POSTGRES_CONTAINER}" pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Fc \
    > "${BACKUP_PATH}/postgres.dump" || {
        echo "ERROR: PostgreSQL backup failed"
        exit 1
    }

echo "PostgreSQL backup complete: ${BACKUP_PATH}/postgres.dump"

# =============================================================================
# Neo4j Backup
# =============================================================================
echo "=== Backing up Neo4j ==="
NEO4J_CONTAINER="multi-lingual-podcast-neo4j"
NEO4J_BACKUP_DIR="/var/lib/neo4j/backups"

# Neo4j community edition doesn't have online backup; use neo4j-admin dump
docker exec "${NEO4J_CONTAINER}" neo4j-admin database dump neo4j --to-path="${NEO4J_BACKUP_DIR}" || {
    echo "WARNING: Neo4j dump command failed, trying alternative method..."
    # Alternative: stop neo4j, copy data, start neo4j
    docker-compose -f "${COMPOSE_FILE}" -p multi-lingual-podcast stop neo4j
    docker cp "${NEO4J_CONTAINER}:/data" "${BACKUP_PATH}/neo4j_data"
    docker-compose -f "${COMPOSE_FILE}" -p multi-lingual-podcast start neo4j
}

if docker exec "${NEO4J_CONTAINER}" test -f "${NEO4J_BACKUP_DIR}/neo4j.dump"; then
    docker cp "${NEO4J_CONTAINER}:${NEO4J_BACKUP_DIR}/neo4j.dump" "${BACKUP_PATH}/neo4j.dump"
    docker exec "${NEO4J_CONTAINER}" rm -f "${NEO4J_BACKUP_DIR}/neo4j.dump"
    echo "Neo4j backup complete: ${BACKUP_PATH}/neo4j.dump"
else
    echo "Neo4j backup handled via data copy."
fi

# =============================================================================
# Create tarball
# =============================================================================
echo "=== Creating tarball ==="
cd "${BACKUP_DIR}"
tar -czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}"
rm -rf "${BACKUP_PATH}"

echo "Backup tarball: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"

# =============================================================================
# Retention Policy (keep last 7 days)
# =============================================================================
echo "=== Applying retention policy (keep ${RETENTION_DAYS} days) ==="
find "${BACKUP_DIR}" -maxdepth 1 -name 'backup-*.tar.gz' -type f -mtime +${RETENTION_DAYS} -delete

REMAINING=$(find "${BACKUP_DIR}" -maxdepth 1 -name 'backup-*.tar.gz' -type f | wc -l)
echo "Remaining backups: ${REMAINING}"

# =============================================================================
# Optional S3 Upload (placeholder)
# =============================================================================
if [[ -n "${S3_BUCKET:-}" && -n "${AWS_ACCESS_KEY_ID:-}" ]]; then
    echo "=== Uploading to S3 ==="
    aws s3 cp "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz" "s3://${S3_BUCKET}/backups/" || {
        echo "WARNING: S3 upload failed"
    }
    echo "S3 upload complete"
else
    echo "S3 upload skipped (S3_BUCKET or AWS credentials not configured)"
fi

echo "=== Backup completed at $(date) ==="
