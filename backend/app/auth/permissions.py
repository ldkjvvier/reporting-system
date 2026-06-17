"""Dependencias y helpers de autorización por roles y equipos.

Roles:
- ``User.is_admin``: administrador global (acceso total a todos los equipos).
- ``TeamMembership.role``: rol por equipo, "editor" (lectura+escritura) o "viewer" (lectura).
"""
from typing import List, Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.db import get_db
from app.models import Report, TeamMembership, User


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Dependencia: exige que el usuario sea administrador global."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de administrador",
        )
    return user


def team_role(db: Session, user: User, team_id: int) -> Optional[str]:
    """Rol efectivo del usuario en un equipo.

    Admin → "editor" (acceso total). Si no es miembro → ``None``.
    """
    if user.is_admin:
        return "editor"
    membership = (
        db.query(TeamMembership)
        .filter(TeamMembership.user_id == user.id, TeamMembership.team_id == team_id)
        .first()
    )
    return membership.role if membership else None


def user_team_ids(db: Session, user: User) -> List[int]:
    """IDs de los equipos a los que pertenece el usuario (para filtrar listados)."""
    rows = (
        db.query(TeamMembership.team_id)
        .filter(TeamMembership.user_id == user.id)
        .all()
    )
    return [r[0] for r in rows]


def require_report_access(
    db: Session, report_id: int, user: User, need_edit: bool = False
) -> Report:
    """Devuelve el reporte si el usuario puede accederlo; si no, 404/403.

    - Admin: acceso total.
    - Miembro del equipo del reporte: lectura siempre; escritura solo si es "editor".
    - No miembro: 404 (no revela existencia de reportes de otros equipos).
    """
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")

    role = team_role(db, user, report.team_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    if need_edit and role != "editor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu rol en este equipo es de solo lectura",
        )
    return report
