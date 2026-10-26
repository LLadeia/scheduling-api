"""Synthetic dataset for a dedicated database ending in _load. No production fallback."""

import argparse
import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from secrets import token_urlsafe

from sqlalchemy import select
from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password
from app.db.session import SessionLocal, engine
from app.models import Appointment, Resource, User


async def seed(output: Path):
    database = make_url(get_settings().database_url).database
    if not database or not database.endswith("_load"):
        raise SystemExit("Use somente banco dedicado com nome terminado em _load")
    base = (datetime.now(UTC) + timedelta(days=7)).replace(second=0, microsecond=0)
    async with SessionLocal() as session:
        if await session.scalar(select(User.id).limit(1)):
            raise SystemExit("Seed exige banco vazio. Não remove dados existentes.")
        hashed = hash_password(token_urlsafe(32))
        users = [User(email=f"load{i}@example.com", password_hash=hashed) for i in range(100)]
        rooms = [Resource(name=f"Load room {i}") for i in range(10)]
        session.add_all(users + rooms)
        await session.flush()
        data = []
        for room in rooms:
            for slot in range(1000):
                start = base + timedelta(minutes=slot * 30)
                data.append(
                    dict(
                        user_id=users[slot % 100].id,
                        resource_id=room.id,
                        starts_at=start,
                        ends_at=start + timedelta(minutes=20),
                        status="scheduled",
                    )
                )
        await session.execute(Appointment.__table__.insert(), data)
        await session.commit()
        credentials = [
            {
                "id": user.id,
                "index": i,
                "resource_id": rooms[i % 10].id,
                "token": create_access_token(user.id),
                "base": base.isoformat(),
            }
            for i, user in enumerate(users)
        ]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(credentials))
    output.chmod(0o600)
    print("Seed concluído: 100 usuários, 10 salas, 10000 reservas. Tokens no arquivo privado.")


async def refresh(output: Path):
    if not make_url(get_settings().database_url).database.endswith("_load"):
        raise SystemExit("Banco de carga dedicado obrigatório")
    credentials = json.loads(output.read_text())
    for item in credentials:
        item["token"] = create_access_token(item["id"])
    output.write_text(json.dumps(credentials))


async def run(args):
    try:
        await (refresh(args.output) if args.refresh else seed(args.output))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("reports/load_users.json"))
    parser.add_argument("--refresh", action="store_true")
    asyncio.run(run(parser.parse_args()))
