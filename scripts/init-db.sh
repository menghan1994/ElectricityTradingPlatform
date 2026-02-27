#!/bin/bash
set -e

# PostgreSQL 三Schema初始化脚本
# 初始化 public、langgraph、timeseries 三个Schema
# 创建专用数据库角色：app_user（api-server用）、agent_user（agent-engine用）

POSTGRES_DB="${POSTGRES_DB:-electricity_trading}"
APP_DB_PASSWORD="${APP_DB_PASSWORD:-app_user_password}"
AGENT_DB_PASSWORD="${AGENT_DB_PASSWORD:-agent_user_password}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-'EOSQL'
    -- 创建三个Schema
    CREATE SCHEMA IF NOT EXISTS public;
    CREATE SCHEMA IF NOT EXISTS langgraph;
    CREATE SCHEMA IF NOT EXISTS timeseries;

    -- 启用TimescaleDB扩展（数据库级别）
    CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

    -- 验证TimescaleDB扩展在timeseries schema中可用
    -- 创建验证表并立即删除，确保超表功能正常
    CREATE TABLE IF NOT EXISTS timeseries._timescaledb_verify (
        time TIMESTAMPTZ NOT NULL,
        value DOUBLE PRECISION
    );
    SELECT create_hypertable('timeseries._timescaledb_verify', 'time', if_not_exists => TRUE);
    DROP TABLE timeseries._timescaledb_verify;
EOSQL

# 创建专用数据库角色（密码从环境变量注入，使用非引号 heredoc 以展开 shell 变量）
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    DO \$\$
    BEGIN
        -- app_user: api-server使用，对public和timeseries有完全权限
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_user') THEN
            CREATE ROLE app_user WITH LOGIN PASSWORD '${APP_DB_PASSWORD}';
        END IF;

        -- agent_user: agent-engine使用，对public只读，对langgraph有完全权限
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'agent_user') THEN
            CREATE ROLE agent_user WITH LOGIN PASSWORD '${AGENT_DB_PASSWORD}';
        END IF;
    END
    \$\$;

    -- app_user 权限配置
    -- public schema: 完全权限
    GRANT USAGE ON SCHEMA public TO app_user;
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_user;
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO app_user;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO app_user;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO app_user;

    -- timeseries schema: 完全权限
    GRANT USAGE ON SCHEMA timeseries TO app_user;
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA timeseries TO app_user;
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA timeseries TO app_user;
    ALTER DEFAULT PRIVILEGES IN SCHEMA timeseries GRANT ALL PRIVILEGES ON TABLES TO app_user;
    ALTER DEFAULT PRIVILEGES IN SCHEMA timeseries GRANT ALL PRIVILEGES ON SEQUENCES TO app_user;

    -- agent_user 权限配置
    -- public schema: 只读
    GRANT USAGE ON SCHEMA public TO agent_user;
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO agent_user;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO agent_user;

    -- langgraph schema: 完全权限（agent-engine独占）
    GRANT USAGE ON SCHEMA langgraph TO agent_user;
    GRANT CREATE ON SCHEMA langgraph TO agent_user;
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA langgraph TO agent_user;
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA langgraph TO agent_user;
    ALTER DEFAULT PRIVILEGES IN SCHEMA langgraph GRANT ALL PRIVILEGES ON TABLES TO agent_user;
    ALTER DEFAULT PRIVILEGES IN SCHEMA langgraph GRANT ALL PRIVILEGES ON SEQUENCES TO agent_user;

    -- timeseries schema: 只读（agent可读取时序数据）
    GRANT USAGE ON SCHEMA timeseries TO agent_user;
    GRANT SELECT ON ALL TABLES IN SCHEMA timeseries TO agent_user;
    ALTER DEFAULT PRIVILEGES IN SCHEMA timeseries GRANT SELECT ON TABLES TO agent_user;
EOSQL

echo "Database initialization completed successfully."
echo "  - Schemas created: public, langgraph, timeseries"
echo "  - TimescaleDB extension enabled"
echo "  - Roles created: app_user (full access), agent_user (public read-only)"
