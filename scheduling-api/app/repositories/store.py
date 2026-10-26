from sqlalchemy import func, select, true

from app.models import Appointment, Resource, User


async def user_by_email(session, email):
    return await session.scalar(select(User).where(User.email == email))


async def get_resource(session, resource_id, lock=False, shared=False):
    query = select(Resource).where(Resource.id == resource_id)
    if lock:
        query = query.with_for_update(read=shared)
    return await session.scalar(query)


async def resources(session):
    return (await session.scalars(select(Resource).order_by(Resource.id))).all()


async def get_appointment(session, appointment_id, user, lock=False):
    query = select(Appointment).where(Appointment.id == appointment_id)
    if user.role != "admin":
        query = query.where(Appointment.user_id == user.id)
    if lock:
        query = query.with_for_update()
    return await session.scalar(query)


async def appointments(session, user, page, limit, starts_from, starts_before, status, user_id):
    conditions = []
    if user.role != "admin":
        conditions.append(Appointment.user_id == user.id)
    elif user_id is not None:
        conditions.append(Appointment.user_id == user_id)
    if starts_from is not None:
        conditions.append(Appointment.starts_at >= starts_from)
    if starts_before is not None:
        conditions.append(Appointment.starts_at < starts_before)
    if status is not None:
        conditions.append(Appointment.status == status)
    # Single SQL statement, hence one snapshot for items and total.
    total = select(func.count(Appointment.id)).where(*conditions).scalar_subquery()
    paged = (
        select(Appointment)
        .where(*conditions)
        .order_by(Appointment.starts_at, Appointment.id)
        .offset((page - 1) * limit)
        .limit(limit)
        .subquery()
    )
    from sqlalchemy.orm import aliased

    entity = aliased(Appointment, paged)
    rows = (
        await session.execute(
            select(entity, total)
            .select_from(select(total.label("total")).subquery())
            .outerjoin(paged, true())
            .order_by(entity.starts_at, entity.id)
        )
    ).all()
    return [row[0] for row in rows if row[0] is not None], rows[0][1]


async def busy_intervals(session, resource_id, start, end):
    return (
        await session.scalars(
            select(Appointment)
            .where(
                Appointment.resource_id == resource_id,
                Appointment.status == "scheduled",
                Appointment.starts_at < end,
                Appointment.ends_at > start,
            )
            .order_by(Appointment.starts_at, Appointment.id)
        )
    ).all()
