from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.core.exceptions import DomainError
from app.models import Appointment, Resource
from app.repositories import store
from app.schemas.contracts import Cancel, Interval


async def commit(session):
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        cause = getattr(exc.orig, "__cause__", None)
        code = getattr(exc.orig, "sqlstate", None)
        constraint = getattr(cause, "constraint_name", None)
        if code == "23P01" and constraint == "ex_appointments_no_overlap":
            raise DomainError(409, "Horário indisponível") from exc
        if code == "23505" and constraint == "users_email_key":
            raise DomainError(409, "E-mail já cadastrado") from exc
        raise


def require_future(start):
    if start <= datetime.now(UTC):
        raise DomainError(422, "Início deve estar no futuro")


async def active_resource(session, resource_id):
    # Serialize reservation vs resource deactivation, held through commit.
    resource = await store.get_resource(session, resource_id, lock=True, shared=True)
    if resource is None:
        raise DomainError(404, "Recurso não encontrado")
    if not resource.is_active:
        raise DomainError(409, "Recurso inativo")
    return resource


async def create_resource(session, data):
    resource = Resource(**data.model_dump())
    session.add(resource)
    await commit(session)
    await session.refresh(resource)
    return resource


async def patch_resource(session, resource_id, data):
    resource = await store.get_resource(session, resource_id, lock=True)
    if resource is None:
        raise DomainError(404, "Recurso não encontrado")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(resource, key, value)
    await commit(session)
    await session.refresh(resource)
    return resource


async def create_appointment(session, user, data):
    await active_resource(session, data.resource_id)
    require_future(data.starts_at)
    appointment = Appointment(user_id=user.id, **data.model_dump())
    session.add(appointment)
    await commit(session)
    await session.refresh(appointment)
    return appointment


async def read_appointment(session, user, appointment_id, lock=False):
    appointment = await store.get_appointment(session, appointment_id, user, lock=lock)
    if appointment is None:
        raise DomainError(404, "Reserva não encontrada")
    return appointment


async def patch_appointment(session, user, appointment_id, data):
    appointment = await read_appointment(session, user, appointment_id, lock=True)
    if isinstance(data, Cancel) and appointment.status == "cancelled":
        return appointment
    if appointment.status == "cancelled":
        raise DomainError(409, "Cancelamento definitivo")
    require_future(appointment.starts_at)
    if isinstance(data, Cancel):
        appointment.status = "cancelled"
    else:
        await active_resource(session, appointment.resource_id)
        require_future(appointment.starts_at)
        require_future(data.starts_at)
        appointment.starts_at, appointment.ends_at = data.starts_at, data.ends_at
    await commit(session)
    await session.refresh(appointment)
    return appointment


async def availability(session, resource_id, start, end):
    window = Interval(starts_at=start, ends_at=end)
    if window.ends_at - window.starts_at > timedelta(days=get_settings().availability_max_days):
        raise DomainError(422, "Janela de disponibilidade excedida")
    resource = await store.get_resource(session, resource_id)
    if resource is None:
        raise DomainError(404, "Recurso não encontrado")
    free, cursor = [], window.starts_at
    if resource.is_active:
        for reservation in await store.busy_intervals(
            session, resource_id, window.starts_at, window.ends_at
        ):
            if reservation.starts_at > cursor:
                free.append(
                    Interval(starts_at=cursor, ends_at=min(reservation.starts_at, window.ends_at))
                )
            cursor = max(cursor, reservation.ends_at)
        if cursor < window.ends_at:
            free.append(Interval(starts_at=cursor, ends_at=window.ends_at))
    return dict(
        resource_id=resource_id,
        starts_at=window.starts_at,
        ends_at=window.ends_at,
        free_intervals=free,
    )
