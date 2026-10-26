from starlette.concurrency import run_in_threadpool

from app.core.exceptions import unauthorized
from app.core.security import DUMMY_HASH, create_access_token, hash_password, verify_password
from app.models import User
from app.repositories import store
from app.services.scheduling import commit


async def register(session, data, role="client"):
    hashed = await run_in_threadpool(hash_password, data.password)
    user = User(email=str(data.email).lower(), password_hash=hashed, role=role)
    session.add(user)
    await commit(session)
    await session.refresh(user)
    return user


async def login(session, data):
    user = await store.user_by_email(session, str(data.email).lower())
    valid = await run_in_threadpool(
        verify_password, data.password, user.password_hash if user else DUMMY_HASH
    )
    if not valid or not user or not user.is_active:
        raise unauthorized()
    return create_access_token(user.id)
