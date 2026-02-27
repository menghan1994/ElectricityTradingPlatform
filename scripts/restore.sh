#!/bin/bash
set -e

if [ -z "$1" ]; then
    echo "用法: ./restore.sh <备份文件路径>"
    echo "示例: ./restore.sh ./backups/electricity_trading_20260226_120000.dump"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "错误: 备份文件不存在: ${BACKUP_FILE}"
    exit 1
fi

echo "=== PostgreSQL 数据恢复 ==="
echo "恢复文件: ${BACKUP_FILE}"
echo "警告: 此操作将覆盖当前数据库数据！"
read -p "确认继续？(y/N) " confirm

if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "已取消"
    exit 0
fi

docker compose exec -T postgresql pg_restore \
    -U "${POSTGRES_USER:-postgres}" \
    -d "${POSTGRES_DB:-electricity_trading}" \
    --clean \
    --if-exists \
    < "$BACKUP_FILE"

echo "数据恢复完成"
