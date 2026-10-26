import os
import subprocess

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.integration


async def test_migration_roundtrip(db):
    # Dedicated test database, only; fixtures are sequential and next test reseeds.
    env = {**os.environ, "DATABASE_URL": os.environ["TEST_DATABASE_URL"]}
    import sys

    for target in ("base", "head"):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "alembic",
                "downgrade" if target == "base" else "upgrade",
                target,
            ],
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
    async with db() as session:
        assert await session.scalar(text("SELECT version_num FROM alembic_version")) == "0001"
        definition = await session.scalar(
            text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname='ex_appointments_no_overlap'"
            )
        )
        assert "tstzrange" in definition and "scheduled" in definition
        columns = (
            await session.execute(
                text(
                    "SELECT column_name, is_nullable, data_type FROM information_schema.columns WHERE table_name='appointments'"
                )
            )
        ).all()
        assert all(nullable == "NO" for name, nullable, type in columns)
        assert any(
            name == "starts_at" and type == "timestamp with time zone"
            for name, nullable, type in columns
        )
