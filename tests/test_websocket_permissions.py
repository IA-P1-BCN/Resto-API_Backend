"""Permisos de /ws/kitchen (HU-05): solo usuarios activos con rol admin o kitchen."""

import pytest
from fastapi import status
from starlette.websockets import WebSocketDisconnect

from app.core.security import create_access_token
from app.models.model_user import Role
from app.websocket.kitchen import kitchen_manager


def ws_url(token):
    return f"/ws/kitchen?token={token}"


def assert_rejected(client, url):
    with pytest.raises(WebSocketDisconnect) as exc, client.websocket_connect(url):
        pass
    assert exc.value.code == status.WS_1008_POLICY_VIOLATION
    assert kitchen_manager.active_connections == []


def test_ws_sin_token_1008(client):
    assert_rejected(client, "/ws/kitchen")

def test_ws_token_invalido_1008(client):
    assert_rejected(client, ws_url("no-es-un-jwt"))

def test_ws_usuario_inexistente_1008(client):
    assert_rejected(client, ws_url(create_access_token(999)))

def test_ws_usuario_desactivado_1008(client, make_user):
    user = make_user(Role.kitchen, is_active=False)
    assert_rejected(client, ws_url(create_access_token(user.id)))

@pytest.mark.parametrize("role", [Role.waiter, Role.customer])
def test_ws_rol_sin_permiso_1008(client, make_user, role):
    user = make_user(role)
    assert_rejected(client, ws_url(create_access_token(user.id)))

@pytest.mark.parametrize("role", [Role.admin, Role.kitchen])
def test_ws_admin_y_cocina_conectan(client, make_user, role):
    user = make_user(role)
    with client.websocket_connect(ws_url(create_access_token(user.id))) as ws:
        assert len(kitchen_manager.active_connections) == 1
        ws.close()
    assert kitchen_manager.active_connections == []
