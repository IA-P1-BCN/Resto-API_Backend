"""Tests unitarios de get_db (app/database.py).

En el resto de la suite get_db está sobrescrito por conftest.py; aquí se prueba
la dependencia real, cambiando solo la fábrica de sesiones por una de prueba.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from app import database


@pytest.fixture
def closed_sessions(db, monkeypatch) -> list[Session]:
    """Sustituye SessionLocal por una fábrica sobre la BD de test y anota las sesiones cerradas."""
    closed: list[Session] = []

    class TrackingSession(Session):
        def close(self) -> None:
            closed.append(self)
            super().close()

    factory = sessionmaker(bind=db.get_bind(), class_=TrackingSession)
    monkeypatch.setattr(database, "SessionLocal", factory)
    return closed


def test_get_db_yields_a_working_session(closed_sessions):
    gen = database.get_db()
    session = next(gen)

    assert isinstance(session, Session)
    assert session.execute(text("SELECT 1")).scalar() == 1

    gen.close()
    assert closed_sessions == [session]


def test_get_db_closes_the_session_when_the_request_fails(closed_sessions):
    gen = database.get_db()
    session = next(gen)

    with pytest.raises(RuntimeError):
        gen.throw(RuntimeError("fallo en el endpoint"))

    assert closed_sessions == [session]


def test_get_db_opens_one_session_per_call(closed_sessions):
    first, second = database.get_db(), database.get_db()

    assert next(first) is not next(second)

    first.close()
    second.close()
    assert len(closed_sessions) == 2
