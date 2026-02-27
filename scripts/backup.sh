#!/bin/bash
set -e

BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/electricity_trading_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "=== PostgreSQL 全量备份 ==="
echo "备份文件: ${BACKUP_FILE}"

docker compose exec -T postgresql pg_dump \
    -U "${POSTGRES_USER:-postgres}" \
    -d "${POSTGRES_DB:-electricity_trading}" \
    --format=custom \
    | gzip > "$BACKUP_FILE"

echo "备份完成: $(du -h "$BACKUP_FILE" | cut -f1)"

# 清理30天前的备份
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +30 -delete
echo "已清理30天前的旧备份"
