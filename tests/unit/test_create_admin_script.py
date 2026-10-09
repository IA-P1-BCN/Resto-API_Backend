"""Tests unitarios del script `python -m app.scripts.create_admin` (main y __main__).

create_admin() ya está probado en tests/test_permissions.py; aquí se prueba la
línea de comandos. El engine y SessionLocal se cambian por los de la BD de test
para no tocar nunca la BD configurada en DATABASE_URL.
"""

import runpy
import sys
import warnings

import pytest
from sqlalchemy.orm import sessionmaker

from app import database
from app.crud.crud_user import verify_password
from app.models.model_user import Role, User
from app.scripts import create_admin as script


@pytest.fixture
def test_db(db, monkeypatch):
    engine = db.get_bind()
    factory = sessionmaker(bind=engine)
    for module in (script, database):
        monkeypatch.setattr(module, "engine", engine)
        monkeypatch.setattr(module, "SessionLocal", factory)
    return db


def test_main_creates_admin_and_prints_it(test_db, capsys):
    script.main(["jefa@test.com", "clave-segura", "Jefa"])

    user = test_db.query(User).filter_by(email="jefa@test.com").one()
    assert user.role == Role.admin.value
    assert user.name == "Jefa"
    assert verify_password("clave-segura", user.password_hash)
    assert f"Admin listo: jefa@test.com (id {user.id})" in capsys.readouterr().out


def test_main_without_name_uses_default(test_db):
    script.main(["jefa@test.com", "clave-segura"])

    assert test_db.query(User).filter_by(email="jefa@test.com").one().name == "Admin"


@pytest.mark.parametrize("argv", [[], ["solo@test.com"], ["a@test.com", "b", "c", "d"]])
def test_main_with_wrong_arguments_exits_with_usage(test_db, argv):
    with pytest.raises(SystemExit) as exc:
        script.main(argv)

    assert "Uso: python -m app.scripts.create_admin" in str(exc.value)
    assert test_db.query(User).count() == 0


def test_running_as_module_calls_main(test_db, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["create_admin", "modulo@test.com", "clave-segura"])

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        runpy.run_module("app.scripts.create_admin", run_name="__main__")

    assert "Admin listo: modulo@test.com" in capsys.readouterr().out
    assert test_db.query(User).filter_by(email="modulo@test.com").one().role == Role.admin.value
