import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from app.models import Appointment
from app.services import scheduling

pytestmark = pytest.mark.integration


async def test_http_competing_reservations_30_times(client, headers, interval, db):
    original = scheduling.active_resource
    for iteration in range(30):
        barrier = asyncio.Barrier(2)

        async def coordinated(session, resource_id, barrier=barrier):
            resource = await original(session, resource_id)
            # Both transactions already hold compatible resource SHARE locks.
            await asyncio.wait_for(barrier.wait(), timeout=10)
            return resource

        with patch("app.services.scheduling.active_resource", side_effect=coordinated):
            body = interval(offset=iteration * 120)
            responses = await asyncio.wait_for(
                asyncio.gather(
                    client.post("/appointments", headers=headers["a"], json=body),
                    client.post("/appointments", headers=headers["b"], json=body),
                ),
                timeout=20,
            )
        assert sorted(r.status_code for r in responses) == [201, 409]
        async with db() as session:
            count = await session.scalar(
                select(func.count())
                .select_from(Appointment)
                .where(
                    Appointment.starts_at == datetime.fromisoformat(body["starts_at"]),
                    Appointment.status == "scheduled",
                )
            )
            assert count == 1


async def test_database_constraint_without_services(db):
    start = datetime.now(UTC) + timedelta(days=10)
    barrier = asyncio.Barrier(2)

    async def insert(user_id):
        async with db() as session:
            session.add(
                Appointment(
                    user_id=user_id,
                    resource_id=1,
                    starts_at=start,
                    ends_at=start + timedelta(hours=1),
                )
            )
            await asyncio.wait_for(barrier.wait(), timeout=10)
            try:
                await session.commit()
                return "created"
            except IntegrityError as exc:
                assert exc.orig.sqlstate == "23P01"
                await session.rollback()
                return "conflict"

    assert sorted(await asyncio.wait_for(asyncio.gather(insert(2), insert(3)), timeout=20)) == [
        "conflict",
        "created",
    ]


async def test_cancel_wins_locked_reschedule(client, headers, interval, db):
    response = await client.post("/appointments", headers=headers["a"], json=interval())
    appointment_id = response.json()["id"]
    locked = asyncio.Event()
    release = asyncio.Event()
    original = scheduling.read_appointment

    async def coordinated(session, user, id, lock=False):
        appointment = await original(session, user, id, lock)
        if lock and not locked.is_set():
            locked.set()
            await asyncio.wait_for(release.wait(), timeout=10)
        return appointment

    async def drive():
        path = f"/appointments/{appointment_id}"
        with patch("app.services.scheduling.read_appointment", side_effect=coordinated):
            cancel = asyncio.create_task(
                client.patch(path, headers=headers["a"], json={"action": "cancel"})
            )
            await asyncio.wait_for(locked.wait(), timeout=10)
            move = asyncio.create_task(
                client.patch(
                    path,
                    headers=headers["a"],
                    json={
                        "action": "reschedule",
                        **{k: v for k, v in interval(offset=120).items() if k != "resource_id"},
                    },
                )
            )
            # Verify actual PostgreSQL lock contention before releasing cancellation.
            async with db() as session:
                for _ in range(200):
                    waiting = await session.scalar(
                        text(
                            "SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND wait_event_type='Lock' AND query LIKE '%appointments%FOR UPDATE%'"
                        )
                    )
                    if waiting:
                        break
                    await asyncio.sleep(0.01)
                assert waiting, "Reschedule did not wait for row lock"
            release.set()
            return await asyncio.gather(cancel, move)

    cancel, move = await asyncio.wait_for(drive(), timeout=20)
    assert cancel.status_code == 200 and move.status_code == 409
    final = (await client.get(f"/appointments/{appointment_id}", headers=headers["a"])).json()
    assert final["status"] == "cancelled" and final["starts_at"] == response.json()["starts_at"]


async def test_unrelated_integrity_not_mapped(db):
    async with db() as session:
        start = datetime.now(UTC) + timedelta(days=10)
        session.add(
            Appointment(
                user_id=999999, resource_id=1, starts_at=start, ends_at=start + timedelta(hours=1)
            )
        )
        with pytest.raises(IntegrityError):
            await scheduling.commit(session)
        assert not session.in_transaction()
