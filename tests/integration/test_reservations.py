"""Tests de integración de /reservations (HU-10).

Criterios de aceptación (§4.4): solapamiento → 409, party_size > capacity → 422,
reserva válida → 201, customer con reserva ajena → 403, cancelar libera el hueco,
mesa inexistente → 404, sin token → 401, rol sin permiso → 403.
"""

from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.models.dining_table import DiningTable
from app.models.model_user import Role, User
from app.routers import reservations as reservations_router

MISSING_ID = 999_999
DAY = "2026-10-10"


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


def _assert_error(response: Any, status_code: int, code: str) -> None:
    assert response.status_code == status_code, response.text
    body = response.json()
    assert isinstance(body["detail"], str)
    assert body["code"] == code


# --- Fixtures ----------------------------------------------------------------------------


@pytest.fixture
def make_table(db) -> Callable[..., DiningTable]:
    def _make(number: int, capacity: int = 4) -> DiningTable:
        table = DiningTable(number=number, capacity=capacity, location="indoor")
        db.add(table)
        db.commit()
        db.refresh(table)
        return table

    return _make


@pytest.fixture
def table(make_table) -> DiningTable:
    return make_table(number=1, capacity=4)


@pytest.fixture
def customer(make_user) -> User:
    return make_user(Role.customer, email="cliente@test.com")


@pytest.fixture
def other_customer(make_user) -> User:
    return make_user(Role.customer, email="otro@test.com")


@pytest.fixture
def customer_headers(customer) -> dict[str, str]:
    return _headers(customer)


@pytest.fixture
def other_headers(other_customer) -> dict[str, str]:
    return _headers(other_customer)


@pytest.fixture
def waiter_headers(make_user) -> dict[str, str]:
    return _headers(make_user(Role.waiter, email="camarero@test.com"))


@pytest.fixture
def kitchen_headers(make_user) -> dict[str, str]:
    return _headers(make_user(Role.kitchen, email="cocina@test.com"))


@pytest.fixture
def book(client, table, customer_headers) -> Callable[..., dict[str, Any]]:
    """Crea una reserva (por defecto: customer, mesa 1, 2 personas) y devuelve el JSON."""

    def _book(
        hour: str = "20:00",
        duration_min: int = 90,
        headers: dict[str, str] | None = None,
        **extra: Any,
    ) -> dict[str, Any]:
        payload = {
            "table_id": table.id,
            "reserved_at": f"{DAY}T{hour}:00",
            "duration_min": duration_min,
            "party_size": 2,
            **extra,
        }
        response = client.post(
            "/reservations", json=payload, headers=headers or customer_headers
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _book


def _payload(table_id: int, hour: str, **extra: Any) -> dict[str, Any]:
    return {
        "table_id": table_id,
        "reserved_at": f"{DAY}T{hour}:00",
        "party_size": 2,
        **extra,
    }


# --- POST /reservations ------------------------------------------------------------------


def test_create_reservation_returns_201(client, table, customer, customer_headers):
    response = client.post(
        "/reservations",
        json=_payload(table.id, "20:00", party_size=4, notes="Ventana"),
        headers=customer_headers,
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["id"] > 0
    assert body["user_id"] == customer.id
    assert body["table_id"] == table.id
    assert body["reserved_at"] == f"{DAY}T20:00:00"
    assert body["duration_min"] == 90
    assert body["ends_at"] == f"{DAY}T21:30:00"
    assert body["party_size"] == 4
    assert body["status"] == "confirmed"
    assert body["notes"] == "Ventana"


def test_create_overlapping_reservation_returns_409(client, table, book, other_headers):
    book(hour="20:00")  # 20:00-21:30

    response = client.post(
        "/reservations", json=_payload(table.id, "21:00"), headers=other_headers
    )

    _assert_error(response, 409, "reservation_conflict")


def test_create_reservation_containing_another_returns_409(
    client, table, book, other_headers
):
    book(hour="20:00", duration_min=30)  # 20:00-20:30

    response = client.post(
        "/reservations",
        json=_payload(table.id, "19:00", duration_min=180),
        headers=other_headers,
    )

    _assert_error(response, 409, "reservation_conflict")


def test_create_back_to_back_reservations_do_not_overlap(
    client, table, book, other_headers
):
    book(hour="20:00")  # 20:00-21:30

    after = client.post(
        "/reservations", json=_payload(table.id, "21:30"), headers=other_headers
    )
    before = client.post(
        "/reservations",
        json=_payload(table.id, "18:30", duration_min=90),
        headers=other_headers,
    )

    assert after.status_code == 201, after.text
    assert before.status_code == 201, before.text


def test_same_time_on_another_table_is_allowed(client, make_table, book, other_headers):
    book(hour="20:00")
    table_2 = make_table(number=2)

    response = client.post(
        "/reservations", json=_payload(table_2.id, "20:00"), headers=other_headers
    )

    assert response.status_code == 201, response.text


def test_create_party_size_over_capacity_returns_422(client, table, customer_headers):
    response = client.post(
        "/reservations",
        json=_payload(table.id, "20:00", party_size=table.capacity + 1),
        headers=customer_headers,
    )

    _assert_error(response, 422, "party_size_exceeds_capacity")


@pytest.mark.parametrize("party_size", [0, -1])
def test_create_non_positive_party_size_returns_422(
    client, table, customer_headers, party_size
):
    response = client.post(
        "/reservations",
        json=_payload(table.id, "20:00", party_size=party_size),
        headers=customer_headers,
    )

    assert response.status_code == 422


def test_create_on_missing_table_returns_404(client, customer_headers):
    response = client.post(
        "/reservations", json=_payload(MISSING_ID, "20:00"), headers=customer_headers
    )

    _assert_error(response, 404, "table_not_found")


def test_create_without_token_returns_401(client, table):
    response = client.post("/reservations", json=_payload(table.id, "20:00"))

    assert response.status_code == 401


def test_create_as_kitchen_returns_403(client, table, kitchen_headers):
    response = client.post(
        "/reservations", json=_payload(table.id, "20:00"), headers=kitchen_headers
    )

    assert response.status_code == 403


def test_customer_cannot_create_for_another_user(
    client, table, other_customer, customer_headers
):
    response = client.post(
        "/reservations",
        json=_payload(table.id, "20:00", user_id=other_customer.id),
        headers=customer_headers,
    )

    _assert_error(response, 403, "reservation_forbidden")


def test_waiter_creates_reservation_for_customer(
    client, table, customer, waiter_headers
):
    response = client.post(
        "/reservations",
        json=_payload(table.id, "20:00", user_id=customer.id),
        headers=waiter_headers,
    )

    assert response.status_code == 201, response.text
    assert response.json()["user_id"] == customer.id


def test_waiter_creates_reservation_for_missing_user_returns_404(
    client, table, waiter_headers
):
    response = client.post(
        "/reservations",
        json=_payload(table.id, "20:00", user_id=MISSING_ID),
        headers=waiter_headers,
    )

    _assert_error(response, 404, "user_not_found")


def test_create_with_timezone_is_stored_as_utc(client, table, customer_headers):
    response = client.post(
        "/reservations",
        json={
            "table_id": table.id,
            "reserved_at": f"{DAY}T22:00:00+02:00",
            "party_size": 2,
        },
        headers=customer_headers,
    )

    assert response.status_code == 201, response.text
    assert response.json()["reserved_at"] == f"{DAY}T20:00:00"


def test_create_with_unknown_field_returns_422(client, table, customer_headers):
    response = client.post(
        "/reservations",
        json=_payload(table.id, "20:00", status="completed"),
        headers=customer_headers,
    )

    assert response.status_code == 422


# --- GET /reservations -------------------------------------------------------------------


def test_list_as_admin_returns_all_reservations(
    client, book, other_headers, admin_headers
):
    book(hour="13:00")
    book(hour="20:00", headers=other_headers)

    response = client.get("/reservations", headers=admin_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["page"] == 1
    assert body["size"] == 20
    assert [r["reserved_at"] for r in body["items"]] == [
        f"{DAY}T13:00:00",
        f"{DAY}T20:00:00",
    ]


def test_list_as_customer_returns_only_own(
    client, book, customer, customer_headers, other_headers
):
    book(hour="13:00")
    book(hour="20:00", headers=other_headers)

    response = client.get("/reservations", headers=customer_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["user_id"] == customer.id


def test_list_as_customer_filtering_other_user_returns_403(
    client, other_customer, customer_headers
):
    response = client.get(
        "/reservations",
        params={"user_id": other_customer.id},
        headers=customer_headers,
    )

    _assert_error(response, 403, "reservation_forbidden")


def test_list_filters_and_pagination(
    client, make_table, book, waiter_headers, other_customer
):
    first = book(hour="13:00")
    book(hour="20:00")
    table_2 = make_table(number=2)
    book(hour="20:00", table_id=table_2.id)
    client.patch(f"/reservations/{first['id']}/cancel", headers=waiter_headers)
    book(hour="13:00", reserved_at="2026-10-11T13:00:00")

    def total(**params: Any) -> int:
        response = client.get("/reservations", params=params, headers=waiter_headers)
        assert response.status_code == 200, response.text
        return response.json()["total"]

    assert total() == 4
    assert total(status="cancelled") == 1
    assert total(table_id=table_2.id) == 1
    assert total(date=DAY) == 3
    assert total(date="2026-10-11") == 1
    assert total(user_id=other_customer.id) == 0

    page_2 = client.get(
        "/reservations", params={"page": 2, "size": 3}, headers=waiter_headers
    ).json()
    assert page_2["total"] == 4
    assert page_2["page"] == 2
    assert page_2["size"] == 3
    assert len(page_2["items"]) == 1


@pytest.mark.parametrize("params", [{"page": 0}, {"size": 0}, {"status": "bogus"}])
def test_list_with_invalid_query_returns_422(client, admin_headers, params):
    response = client.get("/reservations", params=params, headers=admin_headers)

    assert response.status_code == 422


def test_list_without_token_returns_401(client):
    assert client.get("/reservations").status_code == 401


def test_list_as_kitchen_returns_403(client, kitchen_headers):
    assert client.get("/reservations", headers=kitchen_headers).status_code == 403


# --- GET /reservations/{id} --------------------------------------------------------------


def test_owner_gets_reservation(client, book, customer_headers):
    reservation = book()

    response = client.get(
        f"/reservations/{reservation['id']}", headers=customer_headers
    )

    assert response.status_code == 200
    assert response.json() == reservation


def test_waiter_gets_any_reservation(client, book, waiter_headers):
    reservation = book()

    response = client.get(f"/reservations/{reservation['id']}", headers=waiter_headers)

    assert response.status_code == 200


def test_customer_gets_other_reservation_returns_403(client, book, other_headers):
    reservation = book()

    response = client.get(f"/reservations/{reservation['id']}", headers=other_headers)

    assert response.status_code == 403


def test_get_missing_reservation_returns_404(client, admin_headers):
    response = client.get(f"/reservations/{MISSING_ID}", headers=admin_headers)

    _assert_error(response, 404, "reservation_not_found")


def test_get_reservation_without_token_returns_401(client, book):
    reservation = book()

    assert client.get(f"/reservations/{reservation['id']}").status_code == 401


# --- PATCH /reservations/{id} ------------------------------------------------------------


def test_owner_edits_reservation(client, book, customer_headers):
    reservation = book(hour="20:00")

    response = client.patch(
        f"/reservations/{reservation['id']}",
        json={"reserved_at": f"{DAY}T20:30:00", "party_size": 3, "notes": None},
        headers=customer_headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["reserved_at"] == f"{DAY}T20:30:00"
    assert body["party_size"] == 3
    assert body["notes"] is None


def test_edit_that_overlaps_returns_409(client, book, customer_headers):
    book(hour="20:00")  # 20:00-21:30
    second = book(hour="22:00")

    response = client.patch(
        f"/reservations/{second['id']}",
        json={"reserved_at": f"{DAY}T21:00:00"},
        headers=customer_headers,
    )

    _assert_error(response, 409, "reservation_conflict")


def test_edit_to_occupied_table_returns_409(client, make_table, book, customer_headers):
    table_2 = make_table(number=2)
    book(hour="20:00", table_id=table_2.id)
    reservation = book(hour="20:00")

    response = client.patch(
        f"/reservations/{reservation['id']}",
        json={"table_id": table_2.id},
        headers=customer_headers,
    )

    _assert_error(response, 409, "reservation_conflict")


def test_edit_party_size_over_capacity_returns_422(
    client, book, table, customer_headers
):
    reservation = book()

    response = client.patch(
        f"/reservations/{reservation['id']}",
        json={"party_size": table.capacity + 1},
        headers=customer_headers,
    )

    _assert_error(response, 422, "party_size_exceeds_capacity")


def test_edit_to_missing_table_returns_404(client, book, customer_headers):
    reservation = book()

    response = client.patch(
        f"/reservations/{reservation['id']}",
        json={"table_id": MISSING_ID},
        headers=customer_headers,
    )

    _assert_error(response, 404, "table_not_found")


def test_edit_null_required_field_returns_422(client, book, customer_headers):
    reservation = book()

    response = client.patch(
        f"/reservations/{reservation['id']}",
        json={"party_size": None},
        headers=customer_headers,
    )

    assert response.status_code == 422


def test_customer_cannot_change_status(client, book, customer_headers):
    reservation = book()

    response = client.patch(
        f"/reservations/{reservation['id']}",
        json={"status": "completed"},
        headers=customer_headers,
    )

    _assert_error(response, 403, "reservation_forbidden")


def test_waiter_changes_status(client, book, waiter_headers):
    reservation = book()

    response = client.patch(
        f"/reservations/{reservation['id']}",
        json={"status": "no_show"},
        headers=waiter_headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "no_show"


def test_cancel_via_patch_status_is_rejected(client, book, waiter_headers):
    reservation = book()

    response = client.patch(
        f"/reservations/{reservation['id']}",
        json={"status": "cancelled"},
        headers=waiter_headers,
    )

    assert response.status_code == 422


def test_reactivating_cancelled_reservation_checks_overlap(
    client, book, waiter_headers, other_headers
):
    cancelled = book(hour="20:00")
    client.patch(f"/reservations/{cancelled['id']}/cancel", headers=waiter_headers)
    book(hour="20:00", headers=other_headers)

    response = client.patch(
        f"/reservations/{cancelled['id']}",
        json={"status": "confirmed"},
        headers=waiter_headers,
    )

    _assert_error(response, 409, "reservation_conflict")


def test_customer_edits_other_reservation_returns_403(client, book, other_headers):
    reservation = book()

    response = client.patch(
        f"/reservations/{reservation['id']}",
        json={"party_size": 1},
        headers=other_headers,
    )

    assert response.status_code == 403


def test_edit_missing_reservation_returns_404(client, admin_headers):
    response = client.patch(
        f"/reservations/{MISSING_ID}", json={"party_size": 1}, headers=admin_headers
    )

    _assert_error(response, 404, "reservation_not_found")


# --- PATCH /reservations/{id}/cancel -----------------------------------------------------


@pytest.fixture
def sent_emails(monkeypatch) -> list[tuple[str, str, str]]:
    """Sustituye send_email por un mock que guarda los emails enviados."""
    sent: list[tuple[str, str, str]] = []
    monkeypatch.setattr(
        reservations_router, "send_email", lambda *args: sent.append(args)
    )
    return sent


def test_cancel_reservation_returns_200_and_sends_email(
    client, book, customer, customer_headers, sent_emails
):
    reservation = book(hour="20:00")

    response = client.patch(
        f"/reservations/{reservation['id']}/cancel", headers=customer_headers
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "cancelled"
    assert len(sent_emails) == 1
    to, subject, html = sent_emails[0]
    assert to == customer.email
    assert "cancelada" in subject
    assert "10/10/2026" in html
    assert "20:00" in html
    assert "mesa 1" in html


def test_cancelled_reservation_frees_the_slot(
    client, table, book, customer_headers, other_headers
):
    reservation = book(hour="20:00")
    client.patch(f"/reservations/{reservation['id']}/cancel", headers=customer_headers)

    response = client.post(
        "/reservations", json=_payload(table.id, "20:00"), headers=other_headers
    )

    assert response.status_code == 201, response.text


def test_cancel_twice_returns_409(client, book, customer_headers, sent_emails):
    reservation = book()
    url = f"/reservations/{reservation['id']}/cancel"
    client.patch(url, headers=customer_headers)

    response = client.patch(url, headers=customer_headers)

    _assert_error(response, 409, "reservation_not_cancellable")
    assert len(sent_emails) == 1


def test_customer_cancels_other_reservation_returns_403(
    client, book, other_headers, sent_emails
):
    reservation = book()

    response = client.patch(
        f"/reservations/{reservation['id']}/cancel", headers=other_headers
    )

    assert response.status_code == 403
    assert sent_emails == []


def test_cancel_missing_reservation_returns_404(client, admin_headers):
    response = client.patch(f"/reservations/{MISSING_ID}/cancel", headers=admin_headers)

    _assert_error(response, 404, "reservation_not_found")


# --- DELETE /reservations/{id} -----------------------------------------------------------


def test_owner_deletes_reservation(client, book, customer_headers):
    reservation = book()
    url = f"/reservations/{reservation['id']}"

    response = client.delete(url, headers=customer_headers)

    assert response.status_code == 204
    assert client.get(url, headers=customer_headers).status_code == 404


def test_customer_deletes_other_reservation_returns_403(client, book, other_headers):
    reservation = book()

    response = client.delete(
        f"/reservations/{reservation['id']}", headers=other_headers
    )

    assert response.status_code == 403


def test_delete_missing_reservation_returns_404(client, admin_headers):
    response = client.delete(f"/reservations/{MISSING_ID}", headers=admin_headers)

    _assert_error(response, 404, "reservation_not_found")


def test_delete_as_kitchen_returns_403(client, book, kitchen_headers):
    reservation = book()

    response = client.delete(
        f"/reservations/{reservation['id']}", headers=kitchen_headers
    )

    assert response.status_code == 403


def test_openapi_documents_reservations(client: TestClient):
    paths = client.get("/openapi.json").json()["paths"]

    assert {
        "/reservations",
        "/reservations/{reservation_id}",
        "/reservations/{reservation_id}/cancel",
    } <= paths.keys()
    assert paths["/reservations"]["post"]["tags"] == ["reservations"]
