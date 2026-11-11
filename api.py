import os
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from sqlalchemy.exc import SQLAlchemyError

from GestorPersistencia import GestorPersistencia


app = FastAPI(
    title="OpenData ETL API",
    description="API de consulta del catálogo, registros integrados e historial ETL.",
    version="1.0.0",
)


def _persistencia() -> GestorPersistencia:
    try:
        return GestorPersistencia()
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=503,
            detail=f"No se pudo conectar con la base de datos: {error}",
        ) from error


@app.get("/health", tags=["estado"])
def health() -> dict[str, str]:
    return {
        "estado": "disponible",
        "base_datos": "PostgreSQL" if os.getenv("DATABASE_URL") else "SQLite local",
    }


@app.get("/api/v1/fuentes", tags=["catálogo"])
def listar_fuentes(
    limite: int = Query(default=500, ge=1, le=1000),
) -> dict[str, Any]:
    gestor = _persistencia()
    try:
        return {"total": len(fuentes := gestor.obtener_fuentes(limite)), "fuentes": jsonable_encoder(fuentes)}
    finally:
        gestor.engine.dispose()


@app.get("/api/v1/registros", tags=["datos"])
def listar_registros(
    origen: str | None = None,
    limite: int = Query(default=1000, ge=1, le=10000),
) -> dict[str, Any]:
    gestor = _persistencia()
    try:
        registros = gestor.obtener_registros(origen=origen, limite=limite)
        return {"total": len(registros), "registros": jsonable_encoder(registros)}
    finally:
        gestor.engine.dispose()


@app.get("/api/v1/ejecuciones", tags=["monitoreo"])
def listar_ejecuciones(
    limite: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    gestor = _persistencia()
    try:
        ejecuciones = gestor.obtener_ejecuciones(limite)
        return {"total": len(ejecuciones), "ejecuciones": jsonable_encoder(ejecuciones)}
    finally:
        gestor.engine.dispose()
