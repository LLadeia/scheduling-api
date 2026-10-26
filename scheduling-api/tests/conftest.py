import os
from datetime import UTC, datetime, timedelta

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Never fall back to the production URL. The fixture refuses non-test DB names.
os.environ.setdefault("JWT_SECRET", "test-only-secret-at-least-32-characters-long")
os.environ.setdefault(
    "DATABASE_URL",
    os.getenv("TEST_DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/scheduling_test"),
)
from app.core.security import create_access_token, hash_password
from app.db.session import get_session
from app.main import create_app
from app.models import Resource, User


@pytest.fixture
def interval():
    start = datetime.now(UTC) + timedelta(days=5)

    def make(offset=0, minutes=60, resource_id=1):
        return {
            "resource_id": resource_id,
            "starts_at": (start + timedelta(minutes=offset)).isoformat(),
            "ends_at": (start + timedelta(minutes=offset + minutes)).isoformat(),
        }

    return make


@pytest_asyncio.fixture
async def db():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.fail("Integração exige TEST_DATABASE_URL e PostgreSQL real; não há fallback SQLite")
    from sqlalchemy.engine import make_url

    if not make_url(url).database.endswith("_test"):
        pytest.fail("Banco de teste deve terminar com _test (fixture usa TRUNCATE)")
    engine = create_async_engine(url, pool_size=5, max_overflow=5)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        version = await conn.scalar(text("SELECT version_num FROM alembic_version"))
        assert version == "0001"
        await conn.execute(text("TRUNCATE appointments, resources, users RESTART IDENTITY CASCADE"))
    hashed = hash_password("test-password-123")
    async with factory() as session:
        session.add_all(
            [
                User(email="admin@example.com", password_hash=hashed, role="admin"),
                User(email="a@example.com", password_hash=hashed),
                User(email="b@example.com", password_hash=hashed),
                Resource(name="Room 1"),
                Resource(name="Room 2"),
            ]
        )
        await session.commit()
    yield factory
    await engine.dispose()


@pytest_asyncio.fixture
async def app(db):
    app = create_app()

    async def override():
        async with db() as session:
            try:
                yield session
            finally:
                await session.rollback()

    app.dependency_overrides[get_session] = override
    yield app


@pytest_asyncio.fixture
async def client(app):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest.fixture
def headers():
    return {
        role: {"Authorization": f"Bearer {create_access_token(id)}"}
        for role, id in [("admin", 1), ("a", 2), ("b", 3)]
    }
