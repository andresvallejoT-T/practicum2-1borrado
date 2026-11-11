import hashlib
import json
import os
from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    JSON,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    create_engine,
    insert,
    select,
    update,
)


class GestorPersistencia:
    def __init__(self, conexion_db: str | None = None) -> None:
        self.db = conexion_db or os.getenv("DATABASE_URL", "sqlite:///opendata_etl.db")
        self.engine = create_engine(self.db, future=True)
        self.metadata = MetaData()
        self.registros = Table(
            "etl_registros",
            self.metadata,
            Column("id", Integer, primary_key=True),
            Column("origen", String(1024), nullable=False),
            Column("huella", String(64), nullable=False),
            Column("datos", JSON, nullable=False),
            UniqueConstraint("huella", name="uq_etl_registros_huella"),
        )
        self.ejecuciones = Table(
            "etl_ejecuciones",
            self.metadata,
            Column("id", Integer, primary_key=True),
            Column("inicio", DateTime(timezone=True), nullable=False),
            Column("fin", DateTime(timezone=True), nullable=False),
            Column("estado", String(32), nullable=False),
            Column("origen", String(1024), nullable=True),
            Column("duracion_segundos", Float, nullable=False),
            Column("filas_procesadas", Integer, nullable=False),
            Column("indicadores_calidad", JSON, nullable=False),
            Column("errores", JSON, nullable=False),
        )
        self.fuentes = Table(
            "etl_fuentes",
            self.metadata,
            Column("nombre", String(255), primary_key=True),
            Column("procedencia", String(2048), nullable=False),
            Column("licencia", String(512), nullable=False),
            Column("formato", String(32), nullable=False),
            Column("fecha_disponible", String(128), nullable=False),
            Column("version", String(128), nullable=False),
            Column("fecha_registro", DateTime(timezone=True), nullable=False),
            Column("columnas", JSON, nullable=False),
            Column("filas_disponibles", Integer, nullable=False),
        )
        self.metadata.create_all(self.engine)

    @staticmethod
    def _huella(registro: Mapping[str, Any]) -> str:
        contenido = json.dumps(
            registro,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        )
        return hashlib.sha256(contenido.encode("utf-8")).hexdigest()

    def comprobar_duplicados(self, registros: Sequence[Mapping[str, Any]]) -> int:
        huellas_vistas: set[str] = set()
        duplicados = 0
        huellas_unicas: list[str] = []
        for registro in registros:
            huella = self._huella(registro)
            if huella in huellas_vistas:
                duplicados += 1
            else:
                huellas_vistas.add(huella)
                huellas_unicas.append(huella)

        with self.engine.connect() as conexion:
            for inicio in range(0, len(huellas_unicas), 500):
                lote = huellas_unicas[inicio : inicio + 500]
                existentes = set(
                    conexion.execute(
                        select(self.registros.c.huella).where(
                            self.registros.c.huella.in_(lote)
                        )
                    ).scalars()
                )
                duplicados += len(existentes)
        return duplicados

    def almacenar_datos(
        self,
        datos_transformados: Sequence[Mapping[str, Any]],
        origen: str,
    ) -> int:
        filas_insertadas = 0
        huellas_procesadas: set[str] = set()

        with self.engine.begin() as conexion:
            for inicio in range(0, len(datos_transformados), 500):
                lote = datos_transformados[inicio : inicio + 500]
                valores = []
                for registro in lote:
                    huella = self._huella(registro)
                    if huella in huellas_procesadas:
                        continue
                    huellas_procesadas.add(huella)
                    valores.append(
                        {
                            "origen": origen,
                            "huella": huella,
                            "datos": dict(registro),
                        }
                    )

                if not valores:
                    continue
                existentes = set(
                    conexion.execute(
                        select(self.registros.c.huella).where(
                            self.registros.c.huella.in_(
                                [valor["huella"] for valor in valores]
                            )
                        )
                    ).scalars()
                )
                nuevos = [
                    valor for valor in valores if valor["huella"] not in existentes
                ]
                if nuevos:
                    conexion.execute(insert(self.registros), nuevos)
                    filas_insertadas += len(nuevos)

        return filas_insertadas

    def guardar_ejecucion(self, ejecucion: Mapping[str, Any]) -> None:
        with self.engine.begin() as conexion:
            conexion.execute(insert(self.ejecuciones).values(**dict(ejecucion)))

    def obtener_registros(
        self,
        origen: str | None = None,
        limite: int = 10000,
    ) -> list[dict[str, Any]]:
        if limite < 1:
            raise ValueError("'limite' debe ser mayor que cero.")

        consulta = select(self.registros).order_by(self.registros.c.id.desc()).limit(limite)
        if origen is not None:
            consulta = consulta.where(self.registros.c.origen == origen)

        with self.engine.connect() as conexion:
            return [dict(fila) for fila in conexion.execute(consulta).mappings()]

    def obtener_ejecuciones(self, limite: int = 500) -> list[dict[str, Any]]:
        if limite < 1:
            raise ValueError("'limite' debe ser mayor que cero.")

        consulta = (
            select(self.ejecuciones)
            .order_by(self.ejecuciones.c.id.desc())
            .limit(limite)
        )
        with self.engine.connect() as conexion:
            return [dict(fila) for fila in conexion.execute(consulta).mappings()]

    def registrar_fuente(self, fuente: Mapping[str, Any]) -> None:
        valores = dict(fuente)
        nombre = valores.get("nombre")
        if not isinstance(nombre, str) or not nombre.strip():
            raise ValueError("La fuente debe tener un nombre.")

        with self.engine.begin() as conexion:
            existente = conexion.execute(
                select(self.fuentes.c.nombre).where(self.fuentes.c.nombre == nombre)
            ).first()
            if existente:
                conexion.execute(
                    update(self.fuentes)
                    .where(self.fuentes.c.nombre == nombre)
                    .values(**{clave: valor for clave, valor in valores.items() if clave != "nombre"})
                )
            else:
                conexion.execute(insert(self.fuentes).values(**valores))

    def obtener_fuentes(self, limite: int = 500) -> list[dict[str, Any]]:
        if limite < 1:
            raise ValueError("'limite' debe ser mayor que cero.")
        consulta = select(self.fuentes).order_by(self.fuentes.c.nombre).limit(limite)
        with self.engine.connect() as conexion:
            return [dict(fila) for fila in conexion.execute(consulta).mappings()]
