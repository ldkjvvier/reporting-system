"""Esquemas Pydantic para requests y responses."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from croniter import croniter


# ---------- Equipos ----------
TEAM_ROLES = {"editor", "viewer"}


class TeamCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class TeamOut(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


# ---------- Membresías (usuario ↔ equipo + rol) ----------
class MembershipIn(BaseModel):
    team_id: int
    role: str = "viewer"

    @field_validator("role")
    @classmethod
    def valid_role(cls, v):
        if v not in TEAM_ROLES:
            raise ValueError(f"role debe ser uno de {sorted(TEAM_ROLES)}")
        return v


class MembershipOut(BaseModel):
    team_id: int
    team_name: str
    role: str


# ---------- Auth / Usuarios ----------
class UserOut(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    is_admin: bool
    memberships: List[MembershipOut] = []

    model_config = {"from_attributes": True}


class AdminUserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    is_admin: bool = False
    memberships: List[MembershipIn] = []


class AdminUserUpdate(BaseModel):
    """Actualización parcial; 'memberships' (si se envía) reemplaza el set completo."""
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=6)
    memberships: Optional[List[MembershipIn]] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Reportes ----------
ALLOWED_WINDOWS = {"last_1h", "last_24h", "last_7d", "last_30d"}


class ReportBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    team_id: int
    source_type: str = "signals"
    query: str = "*"
    time_window: str = "last_24h"
    columns: List[str] = []
    output_format: str = "csv"
    recipients: List[EmailStr] = []
    cron: str = "0 8 * * *"
    timezone: str = "America/Santiago"
    enabled: bool = True

    @field_validator("source_type")
    @classmethod
    def valid_source(cls, v):
        if v not in {"logs", "signals", "metrics"}:
            raise ValueError("source_type debe ser 'logs', 'signals' o 'metrics'")
        return v

    @field_validator("output_format")
    @classmethod
    def valid_format(cls, v):
        if v not in {"csv", "xlsx"}:
            raise ValueError("output_format debe ser 'csv' o 'xlsx'")
        return v

    @field_validator("time_window")
    @classmethod
    def valid_window(cls, v):
        if v not in ALLOWED_WINDOWS:
            raise ValueError(f"time_window debe ser uno de {sorted(ALLOWED_WINDOWS)}")
        return v

    @field_validator("cron")
    @classmethod
    def valid_cron(cls, v):
        if not croniter.is_valid(v):
            raise ValueError("Expresión cron inválida (formato: m h dom mon dow)")
        return v


class ReportCreate(ReportBase):
    pass


class ReportUpdate(ReportBase):
    pass


class ReportOut(ReportBase):
    id: int
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    next_run: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---------- Corridas ----------
class ReportRunOut(BaseModel):
    id: int
    report_id: int
    status: str
    trigger: str
    started_at: datetime
    finished_at: Optional[datetime]
    row_count: int
    file_path: Optional[str]
    delivery_status: Optional[str]
    error_message: Optional[str]

    model_config = {"from_attributes": True}


# ---------- Datadog preview ----------
class PreviewRequest(BaseModel):
    source_type: str = "signals"
    query: str = "*"
    time_window: str = "last_24h"
    limit: int = 20


class PreviewResponse(BaseModel):
    fields: List[str]
    rows: List[dict]
    total: int


# ---------- Helpers ----------
def user_to_out(user) -> UserOut:
    """Construye UserOut a partir del modelo User, resolviendo el nombre del equipo."""
    return UserOut(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        is_admin=user.is_admin,
        memberships=[
            MembershipOut(team_id=m.team_id, team_name=m.team.name, role=m.role)
            for m in user.memberships
        ],
    )
