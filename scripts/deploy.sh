#!/bin/bash
set -e

echo "=== ElectricityTradingPlatform 部署脚本 ==="

# 1. 前端构建
echo "[1/4] 构建前端..."
cd web-frontend
npm ci
npm run build
cd ..

# 2. 数据库迁移
echo "[2/4] 执行数据库迁移..."
cd api-server
alembic upgrade head
cd ..

# 3. Docker Compose 部署
echo "[3/4] 启动 Docker Compose 服务..."
docker compose up -d --build

# 4. 健康检查
echo "[4/4] 等待服务启动..."
sleep 10

echo "检查服务健康状态..."
curl -sf http://localhost:8000/api/v1/health && echo " - api-server: OK" || echo " - api-server: FAILED"
curl -sf http://localhost:80/ > /dev/null && echo " - web-frontend: OK" || echo " - web-frontend: FAILED"

echo "=== 部署完成 ==="
