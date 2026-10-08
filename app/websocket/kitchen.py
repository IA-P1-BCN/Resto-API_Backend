"""
Gestor de conexiones WebSocket para la cocina.

Mantiene una lista de clientes conectados y permite enviar
mensajes a todos ellos cuando hay un evento nuevo.
"""

import json
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class KitchenConnectionManager:
    """Administra las conexiones WebSocket activas de la cocina."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Acepta una nueva conexión de un cliente de cocina."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Cocinero conectado. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Elimina una conexión cuando el cliente se desconecta."""
        self.active_connections.remove(websocket)
        logger.info(f"Cocinero desconectado. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Envía un mensaje a TODOS los cocineros conectados."""
        json_message = json.dumps(message)

        for connection in self.active_connections:
            try:
                await connection.send_text(json_message)
            except (ConnectionError, RuntimeError):
                self.disconnect(connection)


# Instancia global única (singleton)
kitchen_manager = KitchenConnectionManager()
