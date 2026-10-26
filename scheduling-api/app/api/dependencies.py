from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DomainError, unauthorized
from app.core.security import decode_access_token
from app.db.session import get_session
from app.models import User

Session = Annotated[AsyncSession, Depends(get_session)]
bearer = HTTPBearer(auto_error=False)


async def current_user(
    session: Session, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
):
    if credentials is None:
        raise unauthorized()
    try:
        user_id = decode_access_token(credentials.credentials)
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise unauthorized() from None
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise unauthorized()
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def admin_user(user: CurrentUser):
    if user.role != "admin":
        raise DomainError(403, "Ação administrativa proibida")
    return user


AdminUser = Annotated[User, Depends(admin_user)]
