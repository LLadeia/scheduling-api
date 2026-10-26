from datetime import UTC
from typing import Annotated

from fastapi import APIRouter, Query, Response
from pydantic import AwareDatetime

from app.api.dependencies import AdminUser, CurrentUser, Session
from app.core.exceptions import DomainError
from app.repositories import store
from app.schemas.contracts import AvailabilityOut, ResourceCreate, ResourceOut, ResourcePatch
from app.services import scheduling

router = APIRouter(prefix="/resources", tags=["Salas"])


@router.get("", response_model=list[ResourceOut])
async def list_resources(session: Session, user: CurrentUser):
    return await store.resources(session)


@router.post("", response_model=ResourceOut, status_code=201)
async def create_resource(
    data: ResourceCreate, session: Session, user: AdminUser, response: Response
):
    resource = await scheduling.create_resource(session, data)
    response.headers["Location"] = f"/resources/{resource.id}"
    return resource


@router.get("/{resource_id}", response_model=ResourceOut)
async def read_resource(resource_id: int, session: Session, user: CurrentUser):
    resource = await store.get_resource(session, resource_id)
    if resource is None:
        raise DomainError(404, "Recurso não encontrado")
    return resource


@router.patch("/{resource_id}", response_model=ResourceOut)
async def patch_resource(resource_id: int, data: ResourcePatch, session: Session, user: AdminUser):
    return await scheduling.patch_resource(session, resource_id, data)


@router.get(
    "/{resource_id}/availability",
    response_model=AvailabilityOut,
    description="Janela máxima padrão de 31 dias. Intervalos livres não garantem reserva.",
)
async def availability(
    resource_id: int,
    session: Session,
    user: CurrentUser,
    starts_at: Annotated[AwareDatetime, Query()],
    ends_at: Annotated[AwareDatetime, Query()],
):
    if ends_at <= starts_at:
        raise DomainError(422, "Fim deve ser posterior ao início")
    return await scheduling.availability(
        session, resource_id, starts_at.astimezone(UTC), ends_at.astimezone(UTC)
    )
