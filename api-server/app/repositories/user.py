from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_username(self, username: str) -> User | None:
        stmt = select(User).where(User.username == username)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def increment_failed_attempts(self, user: User) -> None:
        user.failed_login_attempts += 1
        await self.session.flush()

    async def reset_failed_attempts(self, user: User) -> None:
        user.failed_login_attempts = 0
        user.is_locked = False
        user.locked_until = None
        await self.session.flush()

    async def lock_account(self, user: User, lock_minutes: int = 15) -> None:
        user.is_locked = True
        user.locked_until = datetime.now(UTC) + timedelta(minutes=lock_minutes)
        await self.session.flush()

    async def update_last_login(self, user: User) -> None:
        user.last_login_at = datetime.now(UTC)
        await self.session.flush()

    async def update_password(self, user: User, hashed_password: str) -> None:
        user.hashed_password = hashed_password
        await self.session.flush()

    async def get_all_paginated(
        self, page: int = 1, page_size: int = 20, search: str | None = None,
    ) -> tuple[list[User], int]:
        page_size = min(page_size, 100)
        stmt = select(User)
        count_stmt = select(func.count()).select_from(User)

        if search:
            escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            search_filter = or_(
                User.username.ilike(f"%{escaped}%", escape="\\"),
                User.display_name.ilike(f"%{escaped}%", escape="\\"),
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = stmt.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        users = list(result.scalars().all())

        return users, total
