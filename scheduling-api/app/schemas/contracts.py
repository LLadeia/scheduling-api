from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)


class Credentials(StrictInput):
    email: EmailStr = Field(examples=["cliente@example.com"])
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return str(value).lower()


class Register(Credentials):
    password: str = Field(min_length=12, max_length=128)


class Output(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    @field_serializer("*")
    def serialize_utc(self, value):
        return value.astimezone(UTC) if isinstance(value, datetime) else value


class UserOut(Output):
    id: int
    email: str
    role: Literal["admin", "client"]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class ResourceCreate(StrictInput):
    name: str = Field(min_length=1, max_length=120, examples=["Sala de reuniões"])
    description: str | None = Field(default=None, max_length=4000)

    @field_validator("name")
    @classmethod
    def nonblank(cls, value):
        if value is None:
            raise ValueError("Nome obrigatório")
        value = value.strip()
        if not value:
            raise ValueError("Nome não pode estar vazio")
        return value


class ResourcePatch(ResourceCreate):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_patch(self):
        if (
            not self.model_fields_set
            or ("name" in self.model_fields_set and self.name is None)
            or ("is_active" in self.model_fields_set and self.is_active is None)
        ):
            raise ValueError("PATCH vazio ou campo obrigatório nulo")
        return self


class ResourceOut(Output):
    id: int
    name: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class Interval(StrictInput):
    starts_at: AwareDatetime = Field(examples=["2030-01-10T13:00:00Z"])
    ends_at: AwareDatetime = Field(examples=["2030-01-10T14:00:00Z"])

    @field_validator("starts_at", "ends_at")
    @classmethod
    def utc(cls, value):
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def ordered(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("Fim deve ser posterior ao início")
        return self


class AppointmentCreate(Interval):
    resource_id: int = Field(gt=0, examples=[1])


class Reschedule(Interval):
    action: Literal["reschedule"]


class Cancel(StrictInput):
    action: Literal["cancel"]


AppointmentPatch = Annotated[Reschedule | Cancel, Field(discriminator="action")]


class AppointmentOut(Output):
    id: int
    user_id: int
    resource_id: int
    starts_at: datetime
    ends_at: datetime
    status: Literal["scheduled", "cancelled"]
    created_at: datetime
    updated_at: datetime


class AppointmentPage(BaseModel):
    items: list[AppointmentOut]
    total: int
    page: int
    limit: int


class AvailabilityOut(BaseModel):
    resource_id: int
    starts_at: datetime
    ends_at: datetime
    free_intervals: list[Interval]
    reservation_guaranteed: bool = False
