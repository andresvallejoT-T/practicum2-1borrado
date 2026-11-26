"""API de consulta del esquema relacional."""
from decimal import Decimal
from fastapi import FastAPI, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from GestorPersistencia import GestorPersistencia
import modelo as m

app = FastAPI(title="OpenData ETL API", version="2.0.0",
    description="Fuentes y observaciones relacionales, versiones y cruce por DPA/año.")

def consultar(funcion):
    gestor = None
    try:
        gestor = GestorPersistencia()
        return jsonable_encoder(funcion(gestor), custom_encoder={Decimal: str})
    except SQLAlchemyError as exc:
        raise HTTPException(503, "No se pudo consultar la base de datos") from exc
    finally:
        if gestor:
            gestor.engine.dispose()

@app.get("/health")
def health():
    def comprobar(g):
        with g.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"estado": "disponible", "base_datos": g.engine.dialect.name, "modelo": "relacional-v2"}
    return consultar(comprobar)

@app.get("/api/v1/fuentes")
def fuentes(limite: int = Query(500, ge=1, le=1000)):
    return consultar(lambda g: {"fuentes": (rows := g.obtener_fuentes(limite)), "total": len(rows)})

@app.get("/api/v1/observaciones")
@app.get("/api/v1/registros", deprecated=True)
def observaciones(origen: str | None = None, codigo_dpa: str | None = None,
                  anio: int | None = Query(None, ge=1900, le=2100),
                  limite: int = Query(1000, ge=1, le=10000)):
    return consultar(lambda g: {"observaciones": (rows := g.obtener_observaciones(origen, limite, codigo_dpa, anio)),
                                "total": len(rows)})

@app.get("/api/v1/cruce")
def cruce(indicador_a: str, indicador_b: str, anio: int = Query(..., ge=1900, le=2100),
          limite: int = Query(1000, ge=1, le=10000)):
    if indicador_a == indicador_b:
        raise HTTPException(422, "Selecciona dos indicadores diferentes")
    return consultar(lambda g: {"cruce": (rows := g.cruzar_indicadores(indicador_a, indicador_b, anio, limite)),
                                "total": len(rows)})

def endpoint_catalogo(tabla, clave):
    def endpoint(limite: int = Query(500, ge=1, le=1000)):
        return consultar(lambda g: {clave: (rows := g.listar(tabla, limite)), "total": len(rows)})
    endpoint.__name__ = clave
    return endpoint

for ruta, tabla in (("ejecuciones", m.ejecucion), ("versiones", m.version_fuente),
                    ("indicadores", m.indicador), ("territorios", m.territorio),
                    ("errores", m.error_ejecucion), ("metricas", m.metrica_calidad), ("reglas", m.regla)):
    app.get("/api/v1/" + ruta)(endpoint_catalogo(tabla, ruta))
