"""Test de integración del endpoint raíz."""


def test_root_returns_200_with_message(client):
    r = client.get("/")

    assert r.status_code == 200
    assert r.json() == {"message": "API Resto working"}


def test_root_rejects_post_with_error_format(client):
    r = client.post("/")

    assert r.status_code == 405
    assert r.json()["code"] == "method_not_allowed"


# HU-16 (contexto): la raíz responde en la URL pública; HU-11: formato {"detail", "code"}.
