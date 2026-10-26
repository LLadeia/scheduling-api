import logging
from contextlib import asynccontextmanager

from asyncpg import PostgresError
from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import Session
from app.api.routers import appointments, auth, resources
from app.core.config import get_settings
from app.core.logging import RequestLoggingMiddleware
from app.core.rate_limit import LoginLimiter
from app.db.session import engine


@asynccontextmanager
async def lifespan(app):
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    yield
    await engine.dispose()


ERROR_RESPONSES = {
    code: {
        "description": description,
        "content": {"application/json": {"example": {"detail": description}}},
    }
    for code, description in {
        401: "Credenciais ou token inválidos",
        403: "Ação proibida",
        404: "Registro não encontrado",
        409: "Conflito de horário ou estado",
        422: "Entrada inválida",
        429: "Limite de tentativas excedido",
    }.items()
}


def create_app():
    settings = get_settings()
    app = FastAPI(
        title="API de Agendamento de Salas",
        version="1.0.0",
        lifespan=lifespan,
        description="TFG: reservas com JWT, RBAC e integridade de intervalos no PostgreSQL.",
        responses=ERROR_RESPONSES,
    )
    app.state.login_limiter = LoginLimiter(settings.login_limit, settings.login_window_seconds)
    app.add_middleware(RequestLoggingMiddleware)
    for router in (auth.router, resources.router, appointments.router):
        app.include_router(router)

    @app.get("/health/live", tags=["Saúde"])
    async def live():
        return {"status": "alive"}

    @app.get(
        "/health",
        tags=["Saúde"],
        responses={503: {"description": "Banco indisponível ou migração ausente"}},
    )
    async def ready(session: Session):
        try:
            version = await session.scalar(text("SELECT version_num FROM alembic_version"))
            await session.execute(text("SELECT id FROM appointments LIMIT 0"))
            if version != "0001":
                raise HTTPException(503, "Migração pendente")
        except (SQLAlchemyError, PostgresError, OSError, TimeoutError):
            raise HTTPException(503, "Banco indisponível") from None
        return {"status": "ready"}

    return app


app = create_app()
