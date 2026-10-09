"""
Endpoint WebSocket para la cocina.

Los cocineros se conectan a /ws/kitchen y reciben
notificaciones en tiempo real cuando se crean pedidos
o cambian de estado.

El token se pasa como parámetro de query: /ws/kitchen?token=<token>
"""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.core.security import decode_access_token
from app.websocket.kitchen import kitchen_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/kitchen")
async def kitchen_websocket(websocket: WebSocket, token: str | None = None):
    """
    Conexión WebSocket para la vista de cocina.

    El cliente se conecta y permanece escuchando.
    El servidor envía eventos cuando hay pedidos nuevos
    o cambios de estado.

    Requiere token de autenticación como parámetro de query:
    ws://localhost:8000/ws/kitchen?token=<token>
    """
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = decode_access_token(token)
    if user_id is None:
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
