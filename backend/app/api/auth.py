"""Endpoints de autenticación: login y usuario actual.

No hay registro público: las cuentas las crea un administrador (ver api/admin.py).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.security import create_access_token, get_current_user, verify_password
from app.db import get_db
from app.models import User
from app.schemas import LoginRequest, Token, UserOut, user_to_out

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta está desactivada",
        )
    token = create_access_token(str(user.id))
    return Token(access_token=token, user=user_to_out(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    """Datos del usuario autenticado (rol y equipos) para el frontend."""
    return user_to_out(user)
