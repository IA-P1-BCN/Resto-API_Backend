"""Formato común de errores {"detail": str, "code": str} (R-04 / HU-11)."""

import logging

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.exceptions import (
    CONFLICT_CODE,
    INTERNAL_ERROR_CODE,
    INTERNAL_ERROR_DETAIL,
    NOT_FOUND_CODE,
    VALIDATION_ERROR_CODE,
    ConflictError,
    NotFoundError,
    ReservationConflict,
    register_exception_handlers,
)


@pytest.fixture
def error_app():
    """App mínima con los handlers globales y una ruta para cada tipo de error."""
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/not-found")
    def not_found():
        raise NotFoundError("Dish 42 not found")

    @app.get("/conflict")
    def conflict():
        raise ConflictError("Category already exists")

    @app.get("/custom-code")
    def custom_code():
        raise ReservationConflict("Table 3 is already booked")

    @app.get("/plain-http")
    def plain_http():
        raise HTTPException(status_code=401, detail="Not authenticated")

    @app.get("/items/{item_id}")
    def get_item(item_id: int):
        return {"id": item_id}

    @app.get("/boom")
    def boom():
        raise RuntimeError("db password=hunter2 exploded")

    return TestClient(app, raise_server_exceptions=False)


def test_not_found_error_returns_404_with_code(error_app):
    r = error_app.get("/not-found")
    assert r.status_code == 404
    assert r.json() == {"detail": "Dish 42 not found", "code": NOT_FOUND_CODE}


def test_conflict_error_returns_409_with_code(error_app):
    r = error_app.get("/conflict")
    assert r.status_code == 409
    assert r.json() == {"detail": "Category already exists",
                        "code": CONFLICT_CODE}


def test_subclass_keeps_its_own_code(error_app):
    r = error_app.get("/custom-code")
    assert r.status_code == 409
    assert r.json()["code"] == "reservation_conflict"


def test_plain_http_exception_gets_code_from_status(error_app):
    r = error_app.get("/plain-http")
    assert r.status_code == 401
    assert r.json() == {"detail": "Not authenticated", "code": "unauthorized"}


def test_unknown_route_returns_404_with_code(error_app):
    r = error_app.get("/does-not-exist")
    assert r.status_code == 404
    assert r.json()["code"] == NOT_FOUND_CODE


def test_wrong_method_returns_405_with_code(error_app):
    r = error_app.delete("/not-found")
    assert r.status_code == 405
    assert r.json()["code"] == "method_not_allowed"


def test_validation_error_returns_422_with_field_list(error_app):
    r = error_app.get("/items/abc")
    assert r.status_code == 422
    body = r.json()
    assert body["detail"] == "Invalid request data"
    assert body["code"] == VALIDATION_ERROR_CODE
    assert body["errors"][0]["loc"] == ["path", "item_id"]
    assert "input" not in body["errors"][0]


def test_unhandled_error_returns_generic_500(error_app):
    r = error_app.get("/boom")
    assert r.status_code == 500
    assert r.json() == {"detail": INTERNAL_ERROR_DETAIL,
                        "code": INTERNAL_ERROR_CODE}
    assert "hunter2" not in r.text


def test_unhandled_error_is_logged(error_app, caplog):
    with caplog.at_level(logging.ERROR, logger="app.core.exceptions"):
        error_app.get("/boom")
    record = next(r for r in caplog.records if r.getMessage()
                  == "Unhandled error")
    assert record.path == "/boom"
    assert record.exc_info is not None


def test_real_api_not_found_uses_common_format(client, admin_headers):
    r = client.get("/dishes/999", headers=admin_headers)
    assert r.status_code == 404
    assert r.json() == {"detail": "Dish not found", "code": NOT_FOUND_CODE}
