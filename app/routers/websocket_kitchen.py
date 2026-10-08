"""
Endpoint WebSocket para la cocina.

Los cocineros se conectan a /ws/kitchen y reciben
notificaciones en tiempo real cuando se crean pedidos
o cambian de estado.
"""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.websocket.kitchen import kitchen_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/kitchen")
async def kitchen_websocket(websocket: WebSocket):
    """
    Conexión WebSocket para la vista de cocina.

    El cliente se conecta y permanece escuchando.
    El servidor envía eventos cuando hay pedidos nuevos
    o cambios de estado.
    """
    await kitchen_manager.connect(websocket)

    try:
        while True:
            # Esperar mensajes del cliente (ping/pong o confirmaciones)
            data = await websocket.receive_text()
            logger.info(f"Mensaje de cocina: {data}")

    except WebSocketDisconnect:
        kitchen_manager.disconnect(websocket)
