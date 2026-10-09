import pytest


@pytest.fixture
def admin(client, admin_headers):
    """Cliente que hace las peticiones como admin."""
    client.headers.update(admin_headers)
    return client

def user_data():
    return {
        "name": "Juan Pérez",
        "email": "juan@test.com",
        "password": "secreto123",
        "phone": "600123456"
    }

def test_create_user_success(admin):
    r = admin.post("/users/", json=user_data())
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == "juan@test.com"
    assert data["is_active"] is True
    assert data["role"] == "customer"
    assert "password_hash" not in data

def test_create_user_with_role(admin):
    r = admin.post("/users/", json={**user_data(), "role": "waiter"})
    assert r.status_code == 201
    assert r.json()["role"] == "waiter"

def test_create_user_invalid_role(admin):
    r = admin.post("/users/", json={**user_data(), "role": "chef"})
    assert r.status_code == 422

def test_create_user_duplicate_email(admin):
    admin.post("/users/", json=user_data())
    r = admin.post("/users/", json=user_data())
    assert r.status_code == 409

def test_create_user_invalid_data(admin):
    r = admin.post("/users/", json={"name": "", "email": "bad"})
    assert r.status_code == 422

def test_list_users_only_admin(admin):
    r = admin.get("/users/")
    assert r.status_code == 200
    assert [u["email"] for u in r.json()] == ["admin@test.com"]

def test_list_users_with_data(admin):
    admin.post("/users/", json=user_data())
    r = admin.get("/users/")
    assert r.status_code == 200
    assert len(r.json()) == 2

def test_get_user_by_id(admin):
    user_id = admin.post("/users/", json=user_data()).json()["id"]
    r = admin.get(f"/users/{user_id}")
    assert r.status_code == 200
    assert r.json()["id"] == user_id

def test_get_user_not_found(admin):
    r = admin.get("/users/999")
    assert r.status_code == 404

def test_update_user(admin):
    user_id = admin.post("/users/", json=user_data()).json()["id"]
    r = admin.put(f"/users/{user_id}", json={"name": "Juan Updated"})
    assert r.status_code == 200
    assert r.json()["name"] == "Juan Updated"

def test_update_user_role(admin):
    user_id = admin.post("/users/", json=user_data()).json()["id"]
    r = admin.put(f"/users/{user_id}", json={"role": "kitchen"})
    assert r.status_code == 200
    assert r.json()["role"] == "kitchen"

def test_update_user_duplicate_email(admin):
    admin.post("/users/", json=user_data())
    other_id = admin.post("/users/", json={**user_data(), "email": "other@test.com"}).json()["id"]
    r = admin.put(f"/users/{other_id}", json={"email": "juan@test.com"})
    assert r.status_code == 409

def test_update_user_not_found(admin):
    r = admin.put("/users/999", json={"name": "X"})
    assert r.status_code == 404

def test_deactivate_user(admin):
    user_id = admin.post("/users/", json=user_data()).json()["id"]
    r = admin.patch(f"/users/{user_id}/deactivate")
    assert r.status_code == 200
    assert r.json()["is_active"] is False

def test_deactivate_user_not_found(admin):
    r = admin.patch("/users/999/deactivate")
    assert r.status_code == 404
