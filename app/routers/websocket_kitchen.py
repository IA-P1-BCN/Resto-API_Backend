"""
Endpoint WebSocket para la cocina.

Los cocineros se conectan a /ws/kitchen y reciben
notificaciones en tiempo real cuando se crean pedidos
o cambian de estado.

El token se pasa como parámetro de query: /ws/kitchen?token=<token>
Solo pueden conectarse usuarios activos con rol admin o kitchen (HU-05).
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.core.permissions import KITCHEN
from app.core.security import decode_access_token
from app.database import get_db
from app.models.model_user import User
from app.websocket.kitchen import kitchen_manager

logger = logging.getLogger(__name__)

router = APIRouter()

ALLOWED_ROLES = {role.value for role in KITCHEN}


@router.websocket("/ws/kitchen")
async def kitchen_websocket(
    websocket: WebSocket,
    db: Annotated[Session, Depends(get_db)],
    token: str | None = None,
):
    """
    Conexión WebSocket para la vista de cocina.

    El cliente se conecta y permanece escuchando.
    El servidor envía eventos cuando hay pedidos nuevos
    o cambios de estado.

    Requiere token de autenticación como parámetro de query:
    ws://localhost:8000/ws/kitchen?token=<token>

    Cierra con 1008 si falta el token, no es válido o el usuario no existe,
    está desactivado o no tiene rol admin o kitchen.
    """
    user_id = decode_access_token(token) if token else None
    user = db.get(User, user_id) if user_id is not None else None
    allowed = user is not None and user.is_active and user.role in ALLOWED_ROLES
    # La sesión solo hace falta para esta comprobación: se libera ya para no
    # ocupar una conexión de la BD mientras la cocina sigue conectada.
    db.close()
    if not allowed:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await kitchen_manager.connect(websocket)

    try:
        while True:
            # Esperar mensajes del cliente (ping/pong o confirmaciones)
            data = await websocket.receive_text()
            logger.info(f"Mensaje de cocina: {data}")

    except WebSocketDisconnect:
        kitchen_manager.disconnect(websocket)
