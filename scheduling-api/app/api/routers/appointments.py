from datetime import UTC
from typing import Literal

from fastapi import APIRouter, Query, Response
from pydantic import AwareDatetime

from app.api.dependencies import CurrentUser, Session
from app.core.exceptions import DomainError
from app.repositories import store
from app.schemas.contracts import (
    AppointmentCreate,
    AppointmentOut,
    AppointmentPage,
    AppointmentPatch,
)
from app.services import scheduling

router = APIRouter(prefix="/appointments", tags=["Reservas"])


@router.post("", status_code=201, response_model=AppointmentOut)
async def create(data: AppointmentCreate, session: Session, user: CurrentUser, response: Response):
    appointment = await scheduling.create_appointment(session, user, data)
    response.headers["Location"] = f"/appointments/{appointment.id}"
    return appointment


@router.get(
    "",
    response_model=AppointmentPage,
    description="Filtros de início em [starts_from, starts_before). Total e itens respeitam propriedade.",
)
async def list_appointments(
    session: Session,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    starts_from: AwareDatetime | None = None,
    starts_before: AwareDatetime | None = None,
    status: Literal["scheduled", "cancelled"] | None = None,
    user_id: int | None = Query(None, gt=0),
):
    if user_id is not None and user.role != "admin":
        raise DomainError(403, "Filtro por usuário é administrativo")
    if starts_from and starts_before and starts_before <= starts_from:
        raise DomainError(422, "Filtros de data inválidos")
    items, total = await store.appointments(
        session,
        user,
        page,
        limit,
        starts_from.astimezone(UTC) if starts_from else None,
        starts_before.astimezone(UTC) if starts_before else None,
        status,
        user_id,
    )
    return dict(items=items, total=total, page=page, limit=limit)


@router.get("/{appointment_id}", response_model=AppointmentOut)
async def read(appointment_id: int, session: Session, user: CurrentUser):
    return await scheduling.read_appointment(session, user, appointment_id)


@router.patch(
    "/{appointment_id}",
    response_model=AppointmentOut,
    description="action=cancel para cancelamento definitivo; action=reschedule exige início e fim.",
)
async def patch(appointment_id: int, data: AppointmentPatch, session: Session, user: CurrentUser):
    return await scheduling.patch_appointment(session, user, appointment_id, data)
