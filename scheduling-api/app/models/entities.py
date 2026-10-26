from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Timestamps:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class User(Timestamps, Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('admin', 'client')", name="ck_users_role"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="client", server_default="client")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))


class Resource(Timestamps, Base):
    __tablename__ = "resources"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))


class Appointment(Timestamps, Base):
    __tablename__ = "appointments"
    __table_args__ = (
        CheckConstraint("ends_at > starts_at", name="ck_appointments_interval"),
        CheckConstraint("status IN ('scheduled', 'cancelled')", name="ck_appointments_status"),
        ExcludeConstraint(
            ("resource_id", "="),
            (func.tstzrange(text("starts_at"), text("ends_at"), "[)"), "&&"),
            where=text("status = 'scheduled'"),
            using="gist",
            name="ex_appointments_no_overlap",
        ),
        Index("ix_appointments_user_start", "user_id", "starts_at", "id"),
        Index("ix_appointments_start", "starts_at", "id"),
        Index("ix_appointments_resource_start", "resource_id", "starts_at"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    resource_id: Mapped[int] = mapped_column(ForeignKey("resources.id", ondelete="RESTRICT"))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), default="scheduled", server_default="scheduled")
