"""种子数据脚本 — 创建默认管理员账户

用法：
    cd api-server
    python -m scripts.seed_admin

如果 admin 用户已存在则跳过创建。
"""

import asyncio

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.user import User

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Admin@2026"  # 初始密码，首次登录后应立即修改
ADMIN_DISPLAY_NAME = "系统管理员"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=14)).decode("utf-8")


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
            )
            session.add(admin)
            await session.commit()
            print(f"管理员账户 '{ADMIN_USERNAME}' 创建成功。初始密码: {ADMIN_PASSWORD}")
            print("⚠️  请首次登录后立即修改密码！")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
