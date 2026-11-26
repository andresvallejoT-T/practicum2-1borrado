"""Esquema del diagrama KBS. Creación aditiva: no borra tablas etl_*."""
from sqlalchemy import (MetaData, Table, Column as C, BigInteger, Integer, SmallInteger,
    String, Text, Date, DateTime, Numeric, Boolean, ForeignKey as FK,
    UniqueConstraint as UQ, CheckConstraint as CK)

metadata = MetaData()
ID = BigInteger().with_variant(Integer, "sqlite")

def pk():
    return C("id", ID, primary_key=True)

def ref(name, target, nullable=False, primary_key=False):
    return C(name, ID, FK(target), nullable=nullable, primary_key=primary_key)

fuente = Table("fuente", metadata, pk(),
    C("nombre", String(255), nullable=False, unique=True),
    C("publicador", String(255), nullable=False), C("url_descarga", Text, nullable=False),
    C("licencia", String(512), nullable=False), C("formato", String(32), nullable=False),
    C("estructura", String(32), nullable=False), C("descripcion", Text),
    C("activa", Boolean, nullable=False, default=True),
    C("creado_en", DateTime(timezone=True), nullable=False),
    CK("estructura IN ('agregada','registro')", name="ck_fuente_estructura"))

version_fuente = Table("version_fuente", metadata, pk(), ref("fuente_id", "fuente.id"),
    C("fecha_actualizacion_fuente", Date, nullable=False),
    C("fecha_descarga", DateTime(timezone=True), nullable=False),
    C("nombre_archivo", String(255), nullable=False), C("ruta_local", Text),
    C("hash_sha256", String(64), nullable=False, unique=True),
    C("tamano_bytes", BigInteger, nullable=False), C("filas_originales", Integer, nullable=False),
    CK("tamano_bytes >= 0 AND filas_originales >= 0", name="ck_version_tamanos"))

indicador = Table("indicador", metadata, pk(),
    C("codigo", String(128), nullable=False, unique=True),
    C("nombre", String(255), nullable=False), C("unidad", String(128), nullable=False),
    C("descripcion", Text), ref("fuente_id", "fuente.id"))

territorio = Table("territorio", metadata, pk(),
    C("codigo_dpa", String(6), nullable=False, unique=True),
    C("nombre", String(255), nullable=False), C("nombre_normalizado", String(255), nullable=False),
    C("nivel", String(32), nullable=False), ref("territorio_padre_id", "territorio.id", nullable=True),
    CK("(nivel = 'provincia' AND length(codigo_dpa) = 2 AND territorio_padre_id IS NULL) OR "
       "(nivel = 'canton' AND length(codigo_dpa) = 4 AND territorio_padre_id IS NOT NULL) OR "
       "(nivel = 'parroquia' AND length(codigo_dpa) = 6 AND territorio_padre_id IS NOT NULL)",
       name="ck_territorio_nivel"),
    CK("territorio_padre_id IS NULL OR territorio_padre_id <> id", name="ck_territorio_no_ciclo"))

ejecucion = Table("ejecucion", metadata, pk(),
    C("inicio", DateTime(timezone=True), nullable=False), C("fin", DateTime(timezone=True)),
    C("duracion_segundos", Numeric, nullable=False, default=0),
    C("estado", String(32), nullable=False),
    C("filas_leidas", Integer, nullable=False, default=0),
    C("filas_cargadas", Integer, nullable=False, default=0),
    C("filas_rechazadas", Integer, nullable=False, default=0), C("mensaje", Text),
    CK("estado IN ('en_curso','exitosa','fallida','parcial')", name="ck_ejecucion_estado"),
    CK("filas_leidas >= 0 AND filas_cargadas >= 0 AND filas_rechazadas >= 0 AND duracion_segundos >= 0",
       name="ck_ejecucion_contadores"))

observacion = Table("observacion", metadata, pk(),
    ref("indicador_id", "indicador.id"), ref("territorio_id", "territorio.id"),
    C("anio", SmallInteger, nullable=False), C("valor", Numeric, nullable=False),
    ref("version_fuente_id", "version_fuente.id"), ref("ejecucion_id", "ejecucion.id"),
    C("creado_en", DateTime(timezone=True), nullable=False),
    UQ("indicador_id", "territorio_id", "anio", "version_fuente_id", name="uq_observacion_version"),
    CK("anio BETWEEN 1900 AND 2100", name="ck_observacion_anio"))

ejecucion_version = Table("ejecucion_version", metadata,
    ref("ejecucion_id", "ejecucion.id", primary_key=True),
    ref("version_fuente_id", "version_fuente.id", primary_key=True),
    C("filas_leidas", Integer, nullable=False), C("filas_cargadas", Integer, nullable=False),
    CK("filas_leidas >= 0 AND filas_cargadas >= 0", name="ck_ev_contadores"))

regla = Table("regla", metadata, pk(), C("codigo", String(128), nullable=False, unique=True),
    C("nombre", String(255), nullable=False), C("tipo", String(32), nullable=False),
    C("descripcion", Text, nullable=False), C("activa", Boolean, nullable=False, default=True),
    CK("tipo IN ('transformacion','validacion')", name="ck_regla_tipo"))

error_ejecucion = Table("error_ejecucion", metadata, pk(), ref("ejecucion_id", "ejecucion.id"),
    ref("version_fuente_id", "version_fuente.id", nullable=True), ref("regla_id", "regla.id", nullable=True),
    C("fila_origen", Integer), C("columna", String(255)), C("valor_original", Text),
    C("tipo_error", String(128), nullable=False), C("mensaje", Text, nullable=False),
    C("registrado_en", DateTime(timezone=True), nullable=False))

metrica_calidad = Table("metrica_calidad", metadata, pk(), ref("ejecucion_id", "ejecucion.id"),
    ref("version_fuente_id", "version_fuente.id"), C("metrica", String(128), nullable=False),
    C("valor", Numeric, nullable=False), C("unidad", String(64), nullable=False),
    C("registrado_en", DateTime(timezone=True), nullable=False),
    UQ("ejecucion_id", "version_fuente_id", "metrica", name="uq_metrica_ejecucion_version"))
