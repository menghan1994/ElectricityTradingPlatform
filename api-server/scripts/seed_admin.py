"""种子数据脚本 — 创建默认管理员账户

用法：
    cd api-server
    python -m scripts.seed_admin

如果 admin 用户已存在则跳过创建。
"""

import asyncio
import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User
from app.services.user_service import generate_temp_password

ADMIN_USERNAME = os.getenv("SEED_ADMIN_USERNAME", "admin")
# 未设置环境变量时自动生成随机密码，避免硬编码可猜测的默认密码
ADMIN_PASSWORD = os.getenv("SEED_ADMIN_PASSWORD") or generate_temp_password(16)
_PASSWORD_FROM_ENV = bool(os.getenv("SEED_ADMIN_PASSWORD"))
ADMIN_DISPLAY_NAME = "系统管理员"


async def seed() -> None:
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        result = await session.execute(select(User).where(User.username == ADMIN_USERNAME))
        existing = result.scalar_one_or_none()

        if existing:
            print(f"管理员账户 '{ADMIN_USERNAME}' 已存在，跳过创建。")
        else:
            admin = User(
                username=ADMIN_USERNAME,
                hashed_password=hash_password(ADMIN_PASSWORD),
                display_name=ADMIN_DISPLAY_NAME,
                is_active=True,
                role="admin",
            )
            session.add(admin)
            await session.commit()
            print(f"管理员账户 '{ADMIN_USERNAME}' 创建成功。")
            if _PASSWORD_FROM_ENV:
                print("初始密码由环境变量 SEED_ADMIN_PASSWORD 指定。")
            else:
                # 自动生成的密码写入临时文件而非 stdout/日志，防止在 Docker/CI 日志中持久化
                import tempfile
                fd, pw_file = tempfile.mkstemp(prefix="admin_password_", suffix=".txt")
                with os.fdopen(fd, "w") as f:
                    f.write(ADMIN_PASSWORD)
                os.chmod(pw_file, 0o600)
                print(f"初始密码已写入文件: {pw_file}（仅 owner 可读）")
                print("⚠️  请立即读取并删除此文件！")
            print("⚠️  请首次登录后立即修改密码！")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
