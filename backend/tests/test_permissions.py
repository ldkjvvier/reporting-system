"""Pruebas de autorización por equipos (require_report_access, team_role)."""
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth.permissions import require_report_access, team_role, user_team_ids
from app.db import Base
from app.models import Report, Team, TeamMembership, User


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def _seed(db):
    team_a = Team(name="Equipo A")
    team_b = Team(name="Equipo B")
    db.add_all([team_a, team_b])
    db.flush()

    admin = User(email="admin@x.com", hashed_password="x", is_admin=True)
    editor = User(email="editor@x.com", hashed_password="x")
    viewer = User(email="viewer@x.com", hashed_password="x")
    outsider = User(email="other@x.com", hashed_password="x")
    db.add_all([admin, editor, viewer, outsider])
    db.flush()

    db.add_all([
        TeamMembership(user_id=editor.id, team_id=team_a.id, role="editor"),
        TeamMembership(user_id=viewer.id, team_id=team_a.id, role="viewer"),
        TeamMembership(user_id=outsider.id, team_id=team_b.id, role="editor"),
    ])
    report = Report(team_id=team_a.id, created_by_id=editor.id, name="R1")
    db.add(report)
    db.commit()
    return dict(
        team_a=team_a, team_b=team_b, admin=admin, editor=editor,
        viewer=viewer, outsider=outsider, report=report,
    )


def test_team_role_resolution(db):
    s = _seed(db)
    assert team_role(db, s["editor"], s["team_a"].id) == "editor"
    assert team_role(db, s["viewer"], s["team_a"].id) == "viewer"
    assert team_role(db, s["outsider"], s["team_a"].id) is None
    # El admin tiene acceso total a cualquier equipo.
    assert team_role(db, s["admin"], s["team_a"].id) == "editor"


def test_user_team_ids(db):
    s = _seed(db)
    assert user_team_ids(db, s["editor"]) == [s["team_a"].id]
    assert user_team_ids(db, s["admin"]) == []  # admin no necesita membresías


def test_editor_can_read_and_edit(db):
    s = _seed(db)
    rid = s["report"].id
    assert require_report_access(db, rid, s["editor"]).id == rid
    assert require_report_access(db, rid, s["editor"], need_edit=True).id == rid


def test_viewer_can_read_but_not_edit(db):
    s = _seed(db)
    rid = s["report"].id
    assert require_report_access(db, rid, s["viewer"]).id == rid
    with pytest.raises(HTTPException) as exc:
        require_report_access(db, rid, s["viewer"], need_edit=True)
    assert exc.value.status_code == 403


def test_outsider_cannot_access(db):
    s = _seed(db)
    with pytest.raises(HTTPException) as exc:
        require_report_access(db, s["report"].id, s["outsider"])
    assert exc.value.status_code == 404


def test_admin_has_full_access(db):
    s = _seed(db)
    rid = s["report"].id
    assert require_report_access(db, rid, s["admin"], need_edit=True).id == rid
