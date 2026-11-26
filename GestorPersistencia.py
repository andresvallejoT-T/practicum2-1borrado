"""Persistencia relacional; las tablas etl_* antiguas no se modifican."""
import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, event, select, func, and_
from sqlalchemy.pool import NullPool
import modelo as m

def ahora():
    return datetime.now(timezone.utc)

class GestorPersistencia:
    def __init__(self, conexion_db=None):
        self.db = conexion_db or os.getenv("DATABASE_URL", "sqlite:///opendata_etl.db")
        opciones = {"poolclass": NullPool} if str(self.db).startswith("sqlite:") else {}
        self.engine = create_engine(self.db, pool_pre_ping=True, **opciones)
        if self.engine.dialect.name == "sqlite":
            @event.listens_for(self.engine, "connect")
            def foreign_keys(connection, _):
                connection.execute("PRAGMA foreign_keys=ON")
        self.metadata = m.metadata
        self.metadata.create_all(self.engine)

    def listar(self, tabla, limite=500):
        if limite < 1:
            raise ValueError("El límite debe ser positivo")
        with self.engine.connect() as conn:
            return [dict(row) for row in conn.execute(select(tabla).order_by(tabla.c.id.desc()).limit(limite)).mappings()]

    def obtener_fuentes(self, limite=500):
        return self.listar(m.fuente, limite)

    def obtener_ejecuciones(self, limite=500):
        return self.listar(m.ejecucion, limite)

    def obtener_observaciones(self, origen=None, limite=10000, codigo_dpa=None, anio=None):
        if limite < 1:
            raise ValueError("El límite debe ser positivo")
        query = select(m.observacion.c.id, m.fuente.c.nombre.label("fuente"),
            m.indicador.c.codigo.label("indicador"), m.indicador.c.unidad,
            m.territorio.c.codigo_dpa, m.territorio.c.nombre.label("territorio"), m.territorio.c.nivel,
            m.observacion.c.anio, m.observacion.c.valor, m.observacion.c.version_fuente_id,
            m.observacion.c.ejecucion_id, m.version_fuente.c.fecha_actualizacion_fuente).select_from(
                m.observacion.join(m.indicador).join(m.fuente, m.indicador.c.fuente_id == m.fuente.c.id)
                .join(m.territorio, m.observacion.c.territorio_id == m.territorio.c.id)
                .join(m.version_fuente, m.observacion.c.version_fuente_id == m.version_fuente.c.id))
        if origen:
            query = query.where(m.fuente.c.nombre == origen)
        if codigo_dpa:
            query = query.where(m.territorio.c.codigo_dpa == codigo_dpa)
        if anio is not None:
            query = query.where(m.observacion.c.anio == anio)
        with self.engine.connect() as conn:
            return [dict(row) for row in conn.execute(query.order_by(m.observacion.c.id.desc()).limit(limite)).mappings()]

    obtener_registros = obtener_observaciones

    def cruzar_indicadores(self, codigo_a, codigo_b, anio, limite=1000):
        """Una versión por indicador/territorio/año: publicación, descarga, id."""
        ranked = select(m.observacion.c.territorio_id, m.observacion.c.anio, m.observacion.c.valor,
            m.observacion.c.version_fuente_id, m.indicador.c.codigo,
            func.row_number().over(partition_by=(m.observacion.c.indicador_id,
                m.observacion.c.territorio_id, m.observacion.c.anio), order_by=(
                m.version_fuente.c.fecha_actualizacion_fuente.desc(),
                m.version_fuente.c.fecha_descarga.desc(), m.version_fuente.c.id.desc())).label("pos")
            ).select_from(m.observacion.join(m.indicador).join(m.version_fuente,
                m.observacion.c.version_fuente_id == m.version_fuente.c.id)
            ).where(m.observacion.c.anio == anio).subquery()
        a, b = ranked.alias("a"), ranked.alias("b")
        query = select(m.territorio.c.codigo_dpa, m.territorio.c.nombre.label("territorio"),
            a.c.anio, a.c.valor.label("valor_a"), b.c.valor.label("valor_b"),
            a.c.version_fuente_id.label("version_a"), b.c.version_fuente_id.label("version_b")
            ).select_from(a.join(b, and_(a.c.territorio_id == b.c.territorio_id, a.c.anio == b.c.anio))
            .join(m.territorio, a.c.territorio_id == m.territorio.c.id)
            ).where(a.c.codigo == codigo_a, b.c.codigo == codigo_b, a.c.pos == 1, b.c.pos == 1
            ).order_by(m.territorio.c.codigo_dpa).limit(limite)
        with self.engine.connect() as conn:
            return [dict(row) for row in conn.execute(query).mappings()]
