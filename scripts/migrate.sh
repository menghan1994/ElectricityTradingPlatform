#!/bin/bash
set -e

echo "=== Alembic 数据库迁移 ==="

cd api-server

case "${1:-upgrade}" in
    upgrade)
        echo "执行迁移: upgrade head"
        alembic upgrade head
        ;;
    downgrade)
        if [ -z "$2" ]; then
            echo "用法: ./migrate.sh downgrade <revision>"
            exit 1
        fi
        echo "回滚迁移到: $2"
        alembic downgrade "$2"
        ;;
    history)
        echo "迁移历史:"
        alembic history
        ;;
    current)
        echo "当前版本:"
        alembic current
        ;;
    *)
        echo "用法: ./migrate.sh [upgrade|downgrade <revision>|history|current]"
        exit 1
        ;;
esac

echo "迁移操作完成"
