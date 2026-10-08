"""Integration tests for /tables (HU-09).

Assumptions: see PENDING-CONTRACTS.md (E1).
"""

from datetime import datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.reservation import Reservation

MISSING_ID = 999_999


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_table(
    client: TestClient,
    admin_headers: dict[str, str],
    number: int,
    capacity: int = 4,
    location: str = "indoor",
) -> dict[str, Any]:
    response = client.post(
        "/tables",
        json={"number": number, "capacity": capacity, "location": location},
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _assert_error(response: Any, status_code: int, code: str) -> None:
    """Check the {"detail": str, "code": str} error format (E1)."""
    assert response.status_code == status_code, response.text
    body = response.json()
    assert isinstance(body["detail"], str)
    # ASSUMPTION E1: code provisional, por confirmar con Rita.
    assert body["code"] == code


# --- GET /tables -----------------------------------------------------------------------------


def test_list_tables_without_token_returns_401(client: TestClient) -> None:
    assert client.get("/tables").status_code == 401


def test_list_tables_as_admin_returns_empty_page(
    client: TestClient, admin_token: str
) -> None:
    response = client.get("/tables", headers=_bearer(admin_token))

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "page": 1, "size": 20}


def test_list_tables_as_waiter_returns_200(
    client: TestClient, waiter_token: str
) -> None:
    assert client.get("/tables", headers=_bearer(waiter_token)).status_code == 200


def test_list_tables_as_customer_returns_403(
    client: TestClient, customer_token: str
) -> None:
    assert client.get("/tables", headers=_bearer(customer_token)).status_code == 403


def test_list_tables_pagination(client: TestClient, admin_token: str) -> None:
    headers = _bearer(admin_token)
    for number in (1, 2, 3):
        _create_table(client, headers, number)

    response = client.get("/tables", params={"page": 1, "size": 2}, headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 2
    assert body["total"] == 3
    assert (body["page"], body["size"]) == (1, 2)


def test_list_tables_size_over_limit_returns_422(
    client: TestClient, admin_token: str
) -> None:
    response = client.get("/tables", params={"size": 101}, headers=_bearer(admin_token))

    assert response.status_code == 422


def test_list_tables_page_zero_returns_422(
    client: TestClient, admin_token: str
) -> None:
    response = client.get("/tables", params={"page": 0}, headers=_bearer(admin_token))

    assert response.status_code == 422


# --- GET /tables/{table_id} ------------------------------------------------------------------


def test_get_table_without_token_returns_401(client: TestClient) -> None:
    assert client.get(f"/tables/{MISSING_ID}").status_code == 401


def test_get_table_as_admin_returns_200(client: TestClient, admin_token: str) -> None:
    headers = _bearer(admin_token)
    created = _create_table(client, headers, number=10)

    response = client.get(f"/tables/{created['id']}", headers=headers)

    assert response.status_code == 200
    assert response.json() == created


def test_get_table_as_waiter_returns_200(
    client: TestClient, admin_token: str, waiter_token: str
) -> None:
    created = _create_table(client, _bearer(admin_token), number=11)

    response = client.get(f"/tables/{created['id']}", headers=_bearer(waiter_token))

    assert response.status_code == 200
    assert response.json() == created


def test_get_table_not_found_returns_404(client: TestClient, admin_token: str) -> None:
    response = client.get(f"/tables/{MISSING_ID}", headers=_bearer(admin_token))

    _assert_error(response, 404, "not_found")


# --- POST /tables ----------------------------------------------------------------------------


def test_create_table_without_token_returns_401(client: TestClient) -> None:
    response = client.post(
        "/tables", json={"number": 1, "capacity": 4, "location": "indoor"}
    )

    assert response.status_code == 401


def test_create_table_as_waiter_returns_403(
    client: TestClient, waiter_token: str
) -> None:
    response = client.post(
        "/tables",
        json={"number": 1, "capacity": 4, "location": "indoor"},
        headers=_bearer(waiter_token),
    )

    assert response.status_code == 403


def test_create_table_as_admin_returns_201(
    client: TestClient, admin_token: str
) -> None:
    response = client.post(
        "/tables",
        json={"number": 20, "capacity": 6, "location": "terrace"},
        headers=_bearer(admin_token),
    )

    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["id"], int)
    assert body["number"] == 20
    assert body["capacity"] == 6
    assert body["location"] == "terrace"
    assert body["status"] == "available"


def test_create_table_duplicate_number_returns_409(
    client: TestClient, admin_token: str
) -> None:
    headers = _bearer(admin_token)
    _create_table(client, headers, number=21)

    response = client.post(
        "/tables",
        json={"number": 21, "capacity": 2, "location": "bar"},
        headers=headers,
    )

    _assert_error(response, 409, "conflict")


def test_create_table_capacity_zero_returns_422(
    client: TestClient, admin_token: str
) -> None:
    response = client.post(
        "/tables",
        json={"number": 22, "capacity": 0, "location": "indoor"},
        headers=_bearer(admin_token),
    )

    assert response.status_code == 422


def test_create_table_invalid_location_returns_422(
    client: TestClient, admin_token: str
) -> None:
    response = client.post(
        "/tables",
        json={"number": 23, "capacity": 4, "location": "jardin"},
        headers=_bearer(admin_token),
    )

    assert response.status_code == 422


# --- PUT /tables/{table_id} ------------------------------------------------------------------

FULL_UPDATE = {"number": 31, "capacity": 8, "location": "terrace", "status": "reserved"}


def test_update_table_without_token_returns_401(client: TestClient) -> None:
    assert client.put(f"/tables/{MISSING_ID}", json=FULL_UPDATE).status_code == 401


def test_update_table_as_waiter_returns_403(
    client: TestClient, admin_token: str, waiter_token: str
) -> None:
    created = _create_table(client, _bearer(admin_token), number=30)

    response = client.put(
        f"/tables/{created['id']}", json=FULL_UPDATE, headers=_bearer(waiter_token)
    )

    assert response.status_code == 403


def test_update_table_as_admin_returns_200(
    client: TestClient, admin_token: str
) -> None:
    headers = _bearer(admin_token)
    created = _create_table(client, headers, number=30, capacity=4, location="indoor")

    response = client.put(f"/tables/{created['id']}", json=FULL_UPDATE, headers=headers)

    assert response.status_code == 200
    assert response.json() == {"id": created["id"], **FULL_UPDATE}


def test_update_table_not_found_returns_404(
    client: TestClient, admin_token: str
) -> None:
    response = client.put(
        f"/tables/{MISSING_ID}", json=FULL_UPDATE, headers=_bearer(admin_token)
    )

    _assert_error(response, 404, "not_found")


def test_update_table_to_taken_number_returns_409(
    client: TestClient, admin_token: str
) -> None:
    headers = _bearer(admin_token)
    _create_table(client, headers, number=32)
    other = _create_table(client, headers, number=33)

    response = client.put(
        f"/tables/{other['id']}", json={**FULL_UPDATE, "number": 32}, headers=headers
    )

    _assert_error(response, 409, "conflict")


# --- PATCH /tables/{table_id}/status ---------------------------------------------------------


def test_change_status_without_token_returns_401(client: TestClient) -> None:
    response = client.patch(f"/tables/{MISSING_ID}/status", json={"status": "occupied"})

    assert response.status_code == 401


def test_change_status_as_admin_returns_200(
    client: TestClient, admin_token: str
) -> None:
    headers = _bearer(admin_token)
    created = _create_table(client, headers, number=40)

    response = client.patch(
        f"/tables/{created['id']}/status", json={"status": "occupied"}, headers=headers
    )

    assert response.status_code == 200
    assert response.json()["status"] == "occupied"


def test_change_status_as_waiter_returns_200(
    client: TestClient, admin_token: str, waiter_token: str
) -> None:
    created = _create_table(client, _bearer(admin_token), number=41)

    response = client.patch(
        f"/tables/{created['id']}/status",
        json={"status": "occupied"},
        headers=_bearer(waiter_token),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "occupied"


def test_change_status_not_found_returns_404(
    client: TestClient, admin_token: str
) -> None:
    response = client.patch(
        f"/tables/{MISSING_ID}/status",
        json={"status": "occupied"},
        headers=_bearer(admin_token),
    )

    _assert_error(response, 404, "not_found")


def test_change_status_invalid_value_returns_422(
    client: TestClient, admin_token: str
) -> None:
    headers = _bearer(admin_token)
    created = _create_table(client, headers, number=42)

    response = client.patch(
        f"/tables/{created['id']}/status", json={"status": "cleaning"}, headers=headers
    )

    assert response.status_code == 422


# --- DELETE /tables/{table_id} ---------------------------------------------------------------


def test_delete_table_without_token_returns_401(client: TestClient) -> None:
    assert client.delete(f"/tables/{MISSING_ID}").status_code == 401


def test_delete_table_as_waiter_returns_403(
    client: TestClient, admin_token: str, waiter_token: str
) -> None:
    created = _create_table(client, _bearer(admin_token), number=50)

    response = client.delete(f"/tables/{created['id']}", headers=_bearer(waiter_token))

    assert response.status_code == 403


def test_delete_table_as_admin_returns_204(
    client: TestClient, admin_token: str
) -> None:
    headers = _bearer(admin_token)
    created = _create_table(client, headers, number=51)

    response = client.delete(f"/tables/{created['id']}", headers=headers)

    assert response.status_code == 204
    assert response.content == b""


def test_delete_table_not_found_returns_404(
    client: TestClient, admin_token: str
) -> None:
    response = client.delete(f"/tables/{MISSING_ID}", headers=_bearer(admin_token))

    _assert_error(response, 404, "not_found")


# --- GET /tables/available (HU-18) -----------------------------------------------------------

SLOT = {"reserved_at": "2026-10-10T20:00:00", "party_size": 2}


def _book_table(db: Session, make_user, table_id: int, reserved_at: str) -> None:
    db.add(
        Reservation(
            user_id=make_user("customer", email="reserva@test.com").id,
            table_id=table_id,
            reserved_at=datetime.fromisoformat(reserved_at),
            duration_min=90,
            party_size=2,
        )
    )
    db.commit()


def test_available_tables_without_token_returns_401(client: TestClient) -> None:
    assert client.get("/tables/available", params=SLOT).status_code == 401


def test_available_tables_as_kitchen_returns_403(
    client: TestClient, auth_headers
) -> None:
    response = client.get(
        "/tables/available", params=SLOT, headers=auth_headers("kitchen")
    )

    assert response.status_code == 403


def test_available_tables_as_customer_returns_403(
    client: TestClient, customer_token: str
) -> None:
    response = client.get(
        "/tables/available", params=SLOT, headers=_bearer(customer_token)
    )

    assert response.status_code == 403


def test_available_tables_as_waiter_excludes_booked_and_small_tables(
    client: TestClient, db: Session, make_user, admin_token: str, waiter_token: str
) -> None:
    admin = _bearer(admin_token)
    booked = _create_table(client, admin, number=60, capacity=4)
    _create_table(client, admin, number=61, capacity=2)
    free = _create_table(client, admin, number=62, capacity=4)
    _book_table(db, make_user, booked["id"], "2026-10-10T19:30:00")

    response = client.get(
        "/tables/available",
        params={"reserved_at": "2026-10-10T20:00:00", "party_size": 3},
        headers=_bearer(waiter_token),
    )

    assert response.status_code == 200, response.text
    assert response.json() == {"items": [free], "total": 1, "page": 1, "size": 20}


def test_available_tables_as_admin_after_booking_ends_returns_table(
    client: TestClient, db: Session, make_user, admin_token: str
) -> None:
    headers = _bearer(admin_token)
    table = _create_table(client, headers, number=63)
    _book_table(db, make_user, table["id"], "2026-10-10T18:30:00")

    response = client.get("/tables/available", params=SLOT, headers=headers)

    assert response.status_code == 200, response.text
    assert [item["id"] for item in response.json()["items"]] == [table["id"]]


def test_available_tables_paginates(client: TestClient, admin_token: str) -> None:
    headers = _bearer(admin_token)
    for number in range(64, 67):
        _create_table(client, headers, number=number)

    response = client.get(
        "/tables/available", params={**SLOT, "page": 2, "size": 2}, headers=headers
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["total"], body["page"], body["size"]) == (3, 2, 2)
    assert [item["number"] for item in body["items"]] == [66]


def test_available_tables_without_params_returns_422(
    client: TestClient, admin_token: str
) -> None:
    response = client.get("/tables/available", headers=_bearer(admin_token))

    assert response.status_code == 422


@pytest.mark.parametrize(
    "params",
    [
        {**SLOT, "party_size": 0},
        {**SLOT, "reserved_at": "not-a-date"},
        {**SLOT, "duration_min": 0},
        {**SLOT, "duration_min": 481},
    ],
)
def test_available_tables_invalid_params_returns_422(
    client: TestClient, admin_token: str, params: dict[str, Any]
) -> None:
    response = client.get(
        "/tables/available", params=params, headers=_bearer(admin_token)
    )

    assert response.status_code == 422
