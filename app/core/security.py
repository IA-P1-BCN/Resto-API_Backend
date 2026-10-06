"""Stub temporal de app/core/security.py (Carla, C-01 / plan 5.2).

El plan promete get_current_user() y require_role(*roles). Carla debia
publicar el stub el 02/10 y la implementacion real el 06/10. Como todavia
no estan en dev, este stub desbloquea los imports de HU-09.

ADVERTENCIA: este stub NO autentica de verdad. Solo permite importar sin
romper. Los tests que verifiquen 401/403 fallaran hasta que la
implementacion real este en dev.

TODO: eliminar cuando Carla mergee HU-05 a dev.
"""

from fastapi import Depends, HTTPException, status


def get_current_user() -> dict:
    """Stub: devuelve un admin fijo (contrato 5.2)."""
    return {"id": 1, "role": "admin", "email": "stub@restoapi.local"}


def require_role(*roles: str):
    """Stub: devuelve una dependencia que solo permite los roles indicados."""

    def dependency(current_user: dict = Depends(get_current_user)) -> dict:
        if roles and current_user.get("role") not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rol no autorizado",
            )
        return current_user

    return dependency


__all__ = ["get_current_user", "require_role"]
