from fastapi import APIRouter, Request, Response

from app.api.dependencies import CurrentUser, Session
from app.core.config import get_settings
from app.schemas.contracts import Credentials, Register, TokenOut, UserOut
from app.services import auth

router = APIRouter(tags=["Autenticação"])


@router.post("/auth/register", response_model=UserOut, status_code=201, summary="Cadastrar cliente")
async def register(data: Register, session: Session, response: Response):
    user = await auth.register(session, data)
    response.headers["Location"] = "/users/me"
    return user


@router.post("/auth/login", response_model=TokenOut, summary="Login com JSON e access token")
async def login(data: Credentials, session: Session, request: Request):
    request.app.state.login_limiter.check(request.client.host if request.client else "unknown")
    token = await auth.login(session, data)
    return TokenOut(access_token=token, expires_in=get_settings().access_token_minutes * 60)


@router.get("/users/me", response_model=UserOut)
async def me(user: CurrentUser):
    return user
