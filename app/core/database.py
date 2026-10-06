"""Puente temporal: reexporta `Base` y `get_db` desde app.database.

El plan (§7.1) propone `app/core/database.py` como ubicación definitiva.
Mientras tanto, este módulo reexporta lo que ya existe en `app/database.py`
(Carla, C-01) para que los módulos que siguen el plan (HU-09, HU-10...)
no rompan.

TODO: eliminar cuando se unifique la estructura con Carla.
"""
from app.database import Base, get_db

__all__ = ["Base", "get_db"]