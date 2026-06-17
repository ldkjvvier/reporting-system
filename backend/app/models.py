"""Modelos ORM: usuarios, equipos, reportes y corridas de reportes."""
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

# Roles válidos dentro de un equipo (el rol global de admin vive en User.is_admin).
TEAM_ROLES = ("editor", "viewer")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Administrador global: gestiona todos los equipos, usuarios y reportes.
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    memberships: Mapped[list["TeamMembership"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    members: Mapped[list["TeamMembership"]] = relationship(
        back_populates="team", cascade="all, delete-orphan"
    )
    reports: Mapped[list["Report"]] = relationship(back_populates="team")


class TeamMembership(Base):
    """Pertenencia N:N usuario↔equipo, con un rol por equipo ('editor' | 'viewer')."""
    __tablename__ = "team_memberships"
    __table_args__ = (UniqueConstraint("user_id", "team_id", name="uq_membership_user_team"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), default="viewer", nullable=False)

    user: Mapped["User"] = relationship(back_populates="memberships")
    team: Mapped["Team"] = relationship(back_populates="members")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # El reporte pertenece a un equipo; created_by_id es solo auditoría del creador.
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False, index=True)
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")

    # Fuente Datadog: "logs" | "signals" (Cloud SIEM) | "metrics" (timeseries)
    source_type: Mapped[str] = mapped_column(String(20), default="signals", nullable=False)
    query: Mapped[str] = mapped_column(Text, default="*")
    time_window: Mapped[str] = mapped_column(String(20), default="last_24h")  # last_1h, last_24h, last_7d, last_30d
    columns: Mapped[list] = mapped_column(JSON, default=list)  # campos a incluir
    output_format: Mapped[str] = mapped_column(String(10), default="csv")  # csv | xlsx
    recipients: Mapped[list] = mapped_column(JSON, default=list)  # lista de correos

    # Programación
    cron: Mapped[str] = mapped_column(String(100), default="0 8 * * *")  # m h dom mon dow
    # Informativo: el scheduler interpreta el cron en SCHEDULER_TIMEZONE (horario de Chile).
    timezone: Mapped[str] = mapped_column(String(64), default="America/Santiago")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    team: Mapped["Team"] = relationship(back_populates="reports")
    runs: Mapped[list["ReportRun"]] = relationship(
        back_populates="report", cascade="all, delete-orphan", order_by="ReportRun.id.desc()"
    )


class ReportRun(Base):
    __tablename__ = "report_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|running|success|failed
    trigger: Mapped[str] = mapped_column(String(20), default="manual")  # manual|scheduled
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    delivery_status: Mapped[str | None] = mapped_column(String(20), nullable=True)  # mock_sent|sent|failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    report: Mapped["Report"] = relationship(back_populates="runs")
