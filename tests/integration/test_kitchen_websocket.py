"""Tests de integración de /ws/kitchen: conexión, mensajes y desconexión.

No prueban la validación de rol del WebSocket (HU-08, fuera de HU-17): solo el
ciclo de vida de la conexión que ya existe.
"""

import logging

from app.routers import websocket_kitchen
from app.websocket.kitchen import kitchen_manager


def test_kitchen_message_is_logged(client, caplog):
    with (
        caplog.at_level(logging.INFO, logger=websocket_kitchen.__name__),
        client.websocket_connect("/ws/kitchen") as ws,
    ):
        ws.send_text("ping")
        ws.close()

    assert "Mensaje de cocina: ping" in caplog.text


def test_kitchen_disconnect_removes_the_connection(client):
    with client.websocket_connect("/ws/kitchen") as ws:
        assert len(kitchen_manager.active_connections) == 1
        ws.close()

    assert kitchen_manager.active_connections == []


# HU-07/HU-08 (contexto): la cocina recibe pedidos por /ws/kitchen; aquí se cubre
# el alta y la baja de la conexión (app/routers/websocket_kitchen.py) para HU-17.
