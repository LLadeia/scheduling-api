from datetime import UTC, datetime, timedelta

import jwt
import pytest
from sqlalchemy import update

from app.core.config import get_settings
from app.db.session import get_session
from app.models import Appointment, User

pytestmark = pytest.mark.integration


async def reserve(client, headers, interval, role="a", **kwargs):
    response = await client.post("/appointments", headers=headers[role], json=interval(**kwargs))
    assert response.status_code == 201, response.text
    assert response.headers["Location"] == f"/appointments/{response.json()['id']}"
    return response.json()


async def test_register_login(client, headers):
    credentials = {"email": "New@example.com", "password": "safe-password-123"}
    assert (
        await client.post("/auth/register", json={**credentials, "role": "admin"})
    ).status_code == 422
    response = await client.post("/auth/register", json=credentials)
    assert response.status_code == 201 and response.headers["Location"] == "/users/me"
    assert response.json()["role"] == "client" and "password_hash" not in response.json()
    assert response.json()["email"] == "new@example.com"
    assert (await client.post("/auth/register", json=credentials)).status_code == 409
    response = await client.post("/auth/login", json=credentials)
    assert response.status_code == 200 and response.json()["expires_in"] == 900
    token = response.json()["access_token"]
    assert (
        await client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    ).status_code == 200
    for data in (
        {**credentials, "password": "wrong"},
        {**credentials, "email": "unknown@example.com"},
    ):
        response = await client.post("/auth/login", json=data)
        assert response.status_code == 401 and response.headers["WWW-Authenticate"] == "Bearer"
    assert (await client.get("/users/me")).status_code == 401
    assert (
        await client.get("/users/me", headers={"Authorization": "Bearer garbage"})
    ).status_code == 401


@pytest.mark.parametrize(
    "kind", ["expired", "tampered", "algorithm", "issuer", "audience", "missing", "subject"]
)
async def test_invalid_tokens(client, kind, mocker):
    settings = get_settings()
    if kind == "algorithm":
        from pydantic import SecretStr

        mocker.patch.object(
            settings, "jwt_secret", SecretStr("test-secret-for-wrong-algorithm-" + "x" * 48)
        )
    now = datetime.now(UTC)
    payload = {
        "sub": "2",
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }
    if kind == "expired":
        payload["exp"] = now - timedelta(seconds=1)
    if kind == "issuer":
        payload["iss"] = "other"
    if kind == "audience":
        payload["aud"] = "other"
    if kind == "missing":
        payload.pop("iat")
    if kind == "subject":
        payload["sub"] = "99999"
    token = jwt.encode(
        payload,
        settings.jwt_secret.get_secret_value()
        if kind != "tampered"
        else "another-long-test-secret-at-least-32-chars",
        algorithm="HS384" if kind == "algorithm" else "HS256",
    )
    assert (
        await client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    ).status_code == 401


async def test_active_user_current_role(client, headers, db):
    async with db() as session:
        await session.execute(update(User).where(User.id == 1).values(role="client"))
        await session.commit()
    assert (
        await client.post("/resources", headers=headers["admin"], json={"name": "new"})
    ).status_code == 403
    async with db() as session:
        await session.execute(update(User).where(User.id == 2).values(is_active=False))
        await session.commit()
    assert (await client.get("/users/me", headers=headers["a"])).status_code == 401
    assert (
        await client.post(
            "/auth/login", json={"email": "a@example.com", "password": "test-password-123"}
        )
    ).status_code == 401


async def test_permissions(client, headers, interval):
    reservation = await reserve(client, headers, interval, role="b")
    path = f"/appointments/{reservation['id']}"
    assert (await client.get(path, headers=headers["a"])).status_code == 404
    for data in (
        {"action": "cancel"},
        {
            "action": "reschedule",
            **{k: v for k, v in interval(offset=120).items() if k != "resource_id"},
        },
    ):
        assert (await client.patch(path, headers=headers["a"], json=data)).status_code == 404
    assert (await client.get(path, headers=headers["admin"])).status_code == 200
    assert (
        await client.patch(path, headers=headers["admin"], json={"action": "cancel"})
    ).status_code == 200
    assert (
        await client.post("/resources", headers=headers["a"], json={"name": "x"})
    ).status_code == 403
    assert (
        await client.patch("/resources/1", headers=headers["a"], json={"is_active": False})
    ).status_code == 403
    assert (await client.get("/appointments/99999", headers=headers["admin"])).status_code == 404


async def test_overlap_adjacency_different_resource(client, headers, interval):
    await reserve(client, headers, interval)
    for offset in (0, 30, -30):
        assert (
            await client.post("/appointments", headers=headers["a"], json=interval(offset=offset))
        ).status_code == 409
    await reserve(client, headers, interval, offset=60)
    await reserve(client, headers, interval, resource_id=2)


async def test_cancel_reuse_and_rollback(client, headers, interval):
    first = await reserve(client, headers, interval)
    second = await reserve(client, headers, interval, offset=120)
    path = f"/appointments/{first['id']}"
    second_times = {k: second[k] for k in ("starts_at", "ends_at")}
    response = await client.patch(
        path, headers=headers["a"], json={"action": "reschedule", **second_times}
    )
    assert response.status_code == 409
    assert (await client.get(path, headers=headers["a"])).json()["starts_at"] == first["starts_at"]
    moved = await client.patch(
        path,
        headers=headers["a"],
        json={
            "action": "reschedule",
            **{k: v for k, v in interval(offset=240).items() if k != "resource_id"},
        },
    )
    assert moved.status_code == 200
    cancellation = await client.patch(path, headers=headers["a"], json={"action": "cancel"})
    repeated = await client.patch(path, headers=headers["a"], json={"action": "cancel"})
    assert cancellation.status_code == repeated.status_code == 200
    assert cancellation.json() == repeated.json()
    assert (
        await client.patch(
            path, headers=headers["a"], json={"action": "reschedule", **second_times}
        )
    ).status_code == 409
    await reserve(client, headers, interval, offset=240)


async def test_intervals_extra_fields_and_started(client, headers, interval, db):
    body = interval()
    for data in (
        {**body, "ends_at": body["starts_at"]},
        {**body, "starts_at": "2020-01-01T10:00:00Z", "ends_at": "2020-01-01T11:00:00Z"},
        {**body, "starts_at": "2030-01-01T10:00:00"},
        {**body, "user_id": 3},
        {**body, "resource_id": 0},
    ):
        assert (
            await client.post("/appointments", headers=headers["a"], json=data)
        ).status_code == 422
    first = await reserve(client, headers, interval)
    path = f"/appointments/{first['id']}"
    for extra in ({"user_id": 3}, {"resource_id": 2}, {"role": "admin"}):
        assert (
            await client.patch(path, headers=headers["a"], json={"action": "cancel", **extra})
        ).status_code == 422
    async with db() as session:
        await session.execute(
            update(Appointment)
            .where(Appointment.id == first["id"])
            .values(
                starts_at=datetime.now(UTC) - timedelta(hours=1),
                ends_at=datetime.now(UTC) + timedelta(hours=1),
            )
        )
        await session.commit()
    for data in (
        {"action": "cancel"},
        {
            "action": "reschedule",
            **{k: v for k, v in interval(offset=120).items() if k != "resource_id"},
        },
    ):
        assert (await client.patch(path, headers=headers["a"], json=data)).status_code == 422


async def test_resources_and_availability(client, headers, interval):
    response = await client.post(
        "/resources", headers=headers["admin"], json={"name": "Extra", "description": "Room"}
    )
    assert response.status_code == 201
    assert (await client.get(response.headers["Location"], headers=headers["a"])).status_code == 200
    assert len((await client.get("/resources", headers=headers["a"])).json()) == 3
    for path in ("/resources/999", "/resources/999/availability"):
        response = await client.get(
            path,
            headers=headers["a"],
            params={"starts_at": interval()["starts_at"], "ends_at": interval()["ends_at"]},
        )
        assert response.status_code == 404
    assert (
        await client.patch("/resources/999", headers=headers["admin"], json={"name": "X"})
    ).status_code == 404
    await reserve(client, headers, interval, offset=60)
    window = {"starts_at": interval()["starts_at"], "ends_at": interval(minutes=180)["ends_at"]}
    response = await client.get("/resources/1/availability", headers=headers["b"], params=window)
    assert response.status_code == 200 and len(response.json()["free_intervals"]) == 2
    assert "user_id" not in response.text and not response.json()["reservation_guaranteed"]
    assert (
        await client.get(
            "/resources/1/availability",
            headers=headers["a"],
            params={**window, "ends_at": window["starts_at"]},
        )
    ).status_code == 422
    assert (
        await client.get(
            "/resources/1/availability",
            headers=headers["a"],
            params={**window, "ends_at": interval(minutes=32 * 24 * 60)["ends_at"]},
        )
    ).status_code == 422
    assert (
        await client.patch(
            "/resources/1", headers=headers["admin"], json={"is_active": False, "description": None}
        )
    ).status_code == 200
    assert (
        await client.post("/appointments", headers=headers["a"], json=interval())
    ).status_code == 409
    assert (
        await client.post("/appointments", headers=headers["a"], json=interval(resource_id=999))
    ).status_code == 404
    response = await client.get("/resources/1/availability", headers=headers["a"], params=window)
    assert response.json()["free_intervals"] == []


async def test_pagination_filters(client, headers, interval):
    for offset in (0, 120, 240):
        await reserve(client, headers, interval, offset=offset)
    await reserve(client, headers, interval, role="b", resource_id=2)
    response = await client.get(
        "/appointments", headers=headers["a"], params={"page": 2, "limit": 2}
    )
    assert (
        response.status_code == 200
        and response.json()["total"] == 3
        and len(response.json()["items"]) == 1
    )
    empty = await client.get("/appointments", headers=headers["a"], params={"page": 10})
    assert empty.json()["items"] == [] and empty.json()["total"] == 3
    assert (await client.get("/appointments", headers=headers["admin"])).json()["total"] == 4
    assert (
        await client.get("/appointments", headers=headers["admin"], params={"user_id": 3})
    ).json()["total"] == 1
    assert (
        await client.get("/appointments", headers=headers["a"], params={"user_id": 3})
    ).status_code == 403
    for params in (
        {"page": 0},
        {"limit": 101},
        {"status": "bad"},
        {"starts_from": "2030-01-01T00:00:00Z", "starts_before": "2020-01-01T00:00:00Z"},
    ):
        assert (
            await client.get("/appointments", headers=headers["a"], params=params)
        ).status_code == 422
    filtered = await client.get(
        "/appointments",
        headers=headers["a"],
        params={
            "starts_from": interval(offset=120)["starts_at"],
            "starts_before": interval(offset=240)["starts_at"],
            "status": "scheduled",
        },
    )
    assert filtered.json()["total"] == 1


async def test_limiter_health_and_schema(client, headers, app):
    for _ in range(5):
        assert (
            await client.post("/auth/login", json={"email": "a@example.com", "password": "bad"})
        ).status_code == 401
    response = await client.post("/auth/login", json={"email": "a@example.com", "password": "bad"})
    assert response.status_code == 429 and "Retry-After" in response.headers
    assert (await client.get("/health/live")).status_code == 200
    assert (await client.get("/health")).status_code == 200
    schema = (await client.get("/openapi.json")).json()
    assert "AppointmentCreate" in schema["components"]["schemas"]
    assert "HTTPBearer" in schema["components"]["securitySchemes"]

    class BrokenSession:
        async def scalar(self, *args):
            raise OSError("offline")

    async def broken():
        yield BrokenSession()

    app.dependency_overrides[get_session] = broken
    assert (await client.get("/health")).status_code == 503
