from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings

engine = create_async_engine(
    get_settings().database_url,
    pool_pre_ping=True,
    connect_args={"timeout": 5, "command_timeout": 15},
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session():
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            # Services commit mutations. Reads/auth may autobegin; close rolls back.
            if session.in_transaction():
                await session.rollback()
