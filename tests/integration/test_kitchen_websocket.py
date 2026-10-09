"""Tests de integración de /ws/kitchen: conexión, mensajes y desconexión.

No prueban la validación de rol del WebSocket (HU-08, fuera de HU-17): solo el
ciclo de vida de la conexión que ya existe.
"""

import logging

from app.models.model_user import Role
from app.routers import websocket_kitchen
from app.websocket.kitchen import kitchen_manager


def _kitchen_ws_url(auth_headers):
    """URL del WebSocket con el token de un usuario kitchen (lo exige HU-05)."""
    token = auth_headers(Role.kitchen)["Authorization"].removeprefix("Bearer ")
    return f"/ws/kitchen?token={token}"


def test_kitchen_message_is_logged(client, auth_headers, caplog):
    with (
        caplog.at_level(logging.INFO, logger=websocket_kitchen.__name__),
        client.websocket_connect(_kitchen_ws_url(auth_headers)) as ws,
    ):
        ws.send_text("ping")
        ws.close()

    assert "Mensaje de cocina: ping" in caplog.text


def test_kitchen_disconnect_removes_the_connection(client, auth_headers):
    with client.websocket_connect(_kitchen_ws_url(auth_headers)) as ws:
        assert len(kitchen_manager.active_connections) == 1
        ws.close()

    assert kitchen_manager.active_connections == []
