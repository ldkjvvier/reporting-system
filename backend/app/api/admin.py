"""Endpoints de administración (solo admin global): gestión de usuarios y equipos."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.permissions import require_admin
from app.auth.security import hash_password
from app.db import get_db
from app.models import Team, TeamMembership, User
from app.schemas import (
    AdminUserCreate,
    AdminUserUpdate,
    MembershipIn,
    TeamCreate,
    TeamOut,
    UserOut,
    user_to_out,
)

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


# ---------- Equipos ----------
@router.get("/teams", response_model=List[TeamOut])
def list_teams(db: Session = Depends(get_db)):
    return db.query(Team).order_by(Team.name).all()


@router.post("/teams", response_model=TeamOut, status_code=201)
def create_team(payload: TeamCreate, db: Session = Depends(get_db)):
    if db.query(Team).filter(Team.name == payload.name).first():
        raise HTTPException(status_code=400, detail="Ya existe un equipo con ese nombre")
    team = Team(name=payload.name)
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


@router.patch("/teams/{team_id}", response_model=TeamOut)
def update_team(team_id: int, payload: TeamCreate, db: Session = Depends(get_db)):
    team = db.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    existing = db.query(Team).filter(Team.name == payload.name, Team.id != team_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe un equipo con ese nombre")
    team.name = payload.name
    db.commit()
    db.refresh(team)
    return team


@router.delete("/teams/{team_id}", status_code=204)
def delete_team(team_id: int, db: Session = Depends(get_db)):
    team = db.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    if team.reports:
        raise HTTPException(
            status_code=400,
            detail="No se puede eliminar un equipo con reportes asociados",
        )
    db.delete(team)
    db.commit()


# ---------- Usuarios ----------
def _apply_memberships(db: Session, user: User, memberships: List[MembershipIn]) -> None:
    """Reemplaza el conjunto de membresías del usuario validando que los equipos existan."""
    team_ids = {m.team_id for m in memberships}
    found = {t.id for t in db.query(Team.id).filter(Team.id.in_(team_ids)).all()} if team_ids else set()
    missing = team_ids - found
    if missing:
        raise HTTPException(status_code=400, detail=f"Equipos inexistentes: {sorted(missing)}")
    user.memberships = [
        TeamMembership(team_id=m.team_id, role=m.role) for m in memberships
    ]


@router.get("/users", response_model=List[UserOut])
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.email).all()
    return [user_to_out(u) for u in users]


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(payload: AdminUserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="El correo ya está registrado")
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        is_admin=payload.is_admin,
    )
    _apply_memberships(db, user, payload.memberships)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user_to_out(user)


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: AdminUserUpdate, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.is_admin is not None:
        user.is_admin = payload.is_admin
    if payload.password is not None:
        user.hashed_password = hash_password(payload.password)
    if payload.memberships is not None:
        _apply_memberships(db, user, payload.memberships)
    db.commit()
    db.refresh(user)
    return user_to_out(user)


@router.delete("/users/{user_id}", status_code=204)
def deactivate_user(user_id: int, db: Session = Depends(get_db)):
    """Desactiva la cuenta (no la borra) para preservar la auditoría de reportes creados."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    user.is_active = False
    db.commit()
