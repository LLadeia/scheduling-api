from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings

password_hasher = PasswordHash.recommended()
DUMMY_HASH = password_hasher.hash("dummy-password-never-used-for-login")


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hasher.verify(password, hashed)


def create_access_token(user_id: int) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user_id),
            "iat": now,
            "exp": now + timedelta(minutes=settings.access_token_minutes),
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
        },
        settings.jwt_secret.get_secret_value(),
        algorithm="HS256",
    )


def decode_access_token(token: str) -> int:
    settings = get_settings()
    claims = jwt.decode(
        token,
        settings.jwt_secret.get_secret_value(),
        algorithms=["HS256"],
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        options={"require": ["sub", "exp", "iat", "iss", "aud"]},
    )
    user_id = int(claims["sub"])
    if user_id < 1:
        raise ValueError("Invalid subject")
    return user_id
