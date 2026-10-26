import json
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.core.logging import RequestLoggingMiddleware
from app.core.rate_limit import LoginLimiter
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.schemas.contracts import Interval, ResourcePatch
from app.services.scheduling import require_future


def test_password_and_token():
    hashed = hash_password("safe-test-password")
    assert hashed.startswith("$argon2id$")
    assert verify_password("safe-test-password", hashed)
    assert not verify_password("bad", hashed)
    assert decode_access_token(create_access_token(1)) == 1


@pytest.mark.parametrize(
    "start,end",
    [
        ("2030-01-01T10:00:00", "2030-01-01T11:00:00"),
        ("2030-01-01T10:00:00Z", "2030-01-01T10:00:00Z"),
    ],
)
def test_invalid_interval(start, end):
    with pytest.raises(ValidationError):
        Interval(starts_at=start, ends_at=end)


def test_utc_and_future():
    interval = Interval(starts_at="2030-01-01T10:00:00-03:00", ends_at="2030-01-01T11:00:00-03:00")
    assert interval.starts_at.hour == 13
    with pytest.raises(HTTPException, match="Início"):
        require_future(datetime.now(UTC) - timedelta(seconds=1))
    require_future(datetime.now(UTC) + timedelta(days=1))


@pytest.mark.parametrize(
    "data", [{}, {"name": None}, {"name": " "}, {"is_active": None}, {"name": "x" * 121}]
)
def test_invalid_resource_patch(data):
    with pytest.raises(ValidationError):
        ResourcePatch(**data)


def test_config_validation():
    with pytest.raises(ValidationError):
        Settings(database_url="sqlite://", jwt_secret="short", _env_file=None)


def test_rate_window(mocker):
    clock = mocker.patch("app.core.rate_limit.monotonic", return_value=10)
    limiter = LoginLimiter(2, 60)
    limiter.check("one")
    limiter.check("one")
    with pytest.raises(HTTPException) as exc:
        limiter.check("one")
    assert exc.value.status_code == 429
    limiter.check("two")
    clock.return_value = 71
    limiter.check("one")


async def test_structured_logging(caplog):
    async def downstream(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    messages = []

    async def send(message):
        messages.append(message)

    async def receive():
        return {}

    with caplog.at_level("INFO", logger="scheduling.requests"):
        await RequestLoggingMiddleware(downstream)({"type": "http", "method": "GET"}, receive, send)
    record = json.loads(caplog.records[-1].message)
    assert record["status"] == 200 and record["duration_ms"] >= 0
    assert b"x-request-id" in dict(messages[0]["headers"])
    await RequestLoggingMiddleware(downstream)({"type": "websocket"}, receive, send)


def test_missing_claims_and_subject():
    settings = get_settings()
    for sub in ("0", "not-id"):
        now = datetime.now(UTC)
        token = jwt.encode(
            {
                "sub": sub,
                "exp": now + timedelta(minutes=5),
                "iat": now,
                "iss": settings.jwt_issuer,
                "aud": settings.jwt_audience,
            },
            settings.jwt_secret.get_secret_value(),
            algorithm="HS256",
        )
        with pytest.raises(ValueError):
            decode_access_token(token)
    token = jwt.encode({"sub": "1"}, settings.jwt_secret.get_secret_value(), algorithm="HS256")
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token)
