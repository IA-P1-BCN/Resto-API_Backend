"""Stub temporal de app/core/security.py (Carla, C-01 / plan 5.2).

El plan promete get_current_user() y require_role(*roles). Carla debia
publicar el stub el 02/10 y la implementacion real el 06/10. Como todavia
no estan en dev, este stub desbloquea los imports de HU-09.

ADVERTENCIA: este stub NO autentica de verdad. Solo permite importar sin
romper. Los tests que verifiquen 401/403 fallaran hasta que la
implementacion real este en dev.

TODO: eliminar cuando Carla mergee HU-05 a dev.
"""
from typing import Annotated

from fastapi import Depends, HTTPException, status


def get_current_user() -> dict:
    """Stub: devuelve un admin fijo (contrato 5.2)."""
    return {"id": 1, "role": "admin", "email": "stub@restoapi.local"}


def require_role(*roles: str):
    """Stub: devuelve una dependencia que solo permite los roles indicados."""

    def dependency(
        current_user: Annotated[dict, Depends(get_current_user)],
    ) -> dict:
        if roles and current_user.get("role") not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Rol no autorizado",
            )
        return current_user

    return dependency

def create_access_token(user_id: int, role: str = "admin") -> str:
    """Stub: devuelve un token ficticio.

    No es un JWT real. Solo sirve para que los tests importen la funcion
    sin romper. Cuando Carla mergee HU-05 a dev, se sustituye por la
    implementacion real.
    """
    return f"stub-token-user-{user_id}-role-{role}"def create_access_token(user_id: int, role: str = "admin") -> str:
    """Stub: devuelve un token ficticio.

    No es un JWT real. Solo sirve para que los tests importen la funcion
    sin romper. Cuando Carla mergee HU-05 a dev, se sustituye por la
    implementacion real.
    """
    return f"stub-token-user-{user_id}-role-{role}"


def decode_access_token(token: str) -> int | None:
    """Stub: extrae el user_id de un token ficticio.

    Formato esperado: 'stub-token-user-<id>-role-<role>'.
    Devuelve el id, o None si el token no sigue el formato.
    """
    if not token or not token.startswith("stub-token-user-"):
        return None
    try:
        # "stub-token-user-1-role-admin" → ["stub", "token", "user", "1", "role", "admin"]
        parts = token.split("-")
        return int(parts[3])
    except (IndexError, ValueError):
        return None

__all__ = ["create_access_token", "decode_access_token", "get_current_user", "require_role"]

