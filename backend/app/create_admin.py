"""Crea (o promueve) el administrador global inicial.

No interactivo, pensado para ejecutarse a mano una sola vez tras desplegar:

    python -m app.create_admin --email admin@empresa.com --password "S3gura.123"

Si el correo ya existe, lo promueve a administrador y, si se pasa --password,
actualiza su contraseña. No hay registro público; el resto de cuentas las crea
el admin desde la API/UI.
"""
import argparse
import sys

from app.auth.security import hash_password
from app.db import session_scope
from app.init_db import main as init_db
from app.models import User


def create_admin(email: str, password: str) -> str:
    with session_scope() as db:
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            user = User(
                email=email,
                hashed_password=hash_password(password),
                is_admin=True,
                is_active=True,
            )
            db.add(user)
            return f"Administrador creado: {email}"
        user.is_admin = True
        user.is_active = True
        if password:
            user.hashed_password = hash_password(password)
        return f"Usuario existente promovido a administrador: {email}"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Crea o promueve el admin global inicial.")
    parser.add_argument("--email", required=True, help="Correo del administrador")
    parser.add_argument("--password", required=True, help="Contraseña (mín. 6 caracteres)")
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Crea las tablas antes de insertar (útil en un entorno nuevo)",
    )
    args = parser.parse_args(argv)

    if len(args.password) < 6:
        parser.error("La contraseña debe tener al menos 6 caracteres")

    if args.init_db:
        init_db()

    print(create_admin(args.email, args.password))
    return 0


if __name__ == "__main__":
    sys.exit(main())
