"""ETL relacional: dos CSV, unión por DPA/año y carga atómica."""
import hashlib
import json
import re
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from sqlalchemy import select, insert, update, text
from Extractor import Extractor
from Transformador import Transformador
from GestorPersistencia import GestorPersistencia, ahora
from MonitorEjecucion import MonitorEjecucion
import modelo as m


class ErrorValidacion(ValueError):
    def __init__(self, mensaje, fila=None, columna=None, valor=None):
        super().__init__(mensaje)
        self.fila = fila
        self.columna = columna
        self.valor = str(valor) if valor is not None else None


class PipelineETL:
    def __init__(self, fuente=None, reglas_transformacion=None, conexion_db=None):
        self.persistencia = GestorPersistencia(conexion_db)
        self.extractor = Extractor()
        self.reglas = reglas_transformacion or {}

    def preparar(self, fuente):
        self._filas_actuales = 0
        meta = dict(fuente.get("metadatos", {}))
        meta.setdefault("nombre", fuente.get("nombre", ""))
        for campo in ("nombre", "publicador", "url_descarga", "licencia", "fecha_actualizacion",
                      "indicador_codigo", "indicador_nombre", "unidad"):
            if not str(meta.get(campo, "")).strip():
                raise ErrorValidacion(f"Falta el metadato {campo}", columna=campo)
            meta[campo] = str(meta[campo]).strip()
        meta["estructura"] = meta.get("estructura", "agregada")
        if meta["estructura"] not in ("agregada", "registro"):
            raise ErrorValidacion("Estructura debe ser agregada o registro")
        try:
            meta["fecha_actualizacion"] = date.fromisoformat(meta["fecha_actualizacion"])
        except ValueError as exc:
            raise ErrorValidacion("Fecha de actualización: usa AAAA-MM-DD") from exc
        archivo = Path(fuente.get("archivo", "datos.csv")).name
        contenido = fuente["contenido"]
        raw = self.extractor.leer_csv_contenido(contenido, archivo)
        self._filas_actuales = len(raw)
        if not raw:
            raise ErrorValidacion("El CSV no contiene filas")
        transformador = Transformador(raw)
        rows = transformador.normalizar_columnas()
        reglas = dict(self.reglas)
        reglas.update(fuente.get("reglas", {}))
        # Los identificadores nunca deben convertirse a números (ceros iniciales).
        for column in reglas.get("tipos", {}):
            if Transformador._nombre_columna(column) in ("codigo_dpa", "ruc"):
                raise ErrorValidacion("DPA y RUC deben conservarse como texto")
        rows = transformador.normalizar_tipos_y_fechas(reglas)
        observaciones, territorios, rucs = {}, {}, defaultdict(set)
        duplicados = 0

        def territorio(codigo, nombre, padre, fila):
            if not nombre or not str(nombre).strip():
                raise ErrorValidacion(f"Falta el nombre del territorio {codigo}", fila, "territorio")
            nombre = str(nombre).strip()
            valor = {"codigo_dpa": codigo, "nombre": nombre,
                     "nombre_normalizado": Transformador._nombre_columna(nombre),
                     "nivel": {2: "provincia", 4: "canton", 6: "parroquia"}[len(codigo)],
                     "padre": padre}
            if codigo in territorios and territorios[codigo] != valor:
                raise ErrorValidacion(f"Nombres contradictorios para DPA {codigo}", fila, "territorio", nombre)
            territorios[codigo] = valor

        for numero, row in enumerate(rows, start=2):
            codigo = str(row.get("codigo_dpa") or "").strip()
            if not re.fullmatch(r"(?:[0-9]{2}|[0-9]{4}|[0-9]{6})", codigo):
                raise ErrorValidacion("DPA debe tener 2, 4 o 6 dígitos, incluidos ceros iniciales",
                                      numero, "codigo_dpa", codigo)
            if any(codigo[i:i+2] == "00" for i in range(0, len(codigo), 2)):
                raise ErrorValidacion("DPA contiene un segmento 00", numero, "codigo_dpa", codigo)
            try:
                anio_texto = str(row.get("anio", "")).strip()
                if not re.fullmatch(r"[0-9]{4}", anio_texto):
                    raise ValueError()
                anio = int(anio_texto)
                if not 1900 <= anio <= 2100:
                    raise ValueError()
            except ValueError as exc:
                raise ErrorValidacion("Año debe ser un entero entre 1900 y 2100", numero, "anio", row.get("anio")) from exc
            if len(codigo) >= 4:
                territorio(codigo[:2], row.get("provincia"), None, numero)
            if len(codigo) == 6:
                territorio(codigo[:4], row.get("canton"), codigo[:2], numero)
            territorio(codigo, row.get("territorio"), codigo[:-2] if len(codigo) > 2 else None, numero)
            llave = (codigo, anio)
            if meta["estructura"] == "registro":
                ruc = str(row.get("ruc") or "").strip()
                if not re.fullmatch(r"[0-9]{13}", ruc):
                    raise ErrorValidacion("RUC debe contener 13 dígitos", numero, "ruc", ruc)
                if ruc in rucs[llave]:
                    duplicados += 1
                rucs[llave].add(ruc)
            else:
                try:
                    valor = Decimal(str(row.get("valor", "")).strip().replace(",", "."))
                    if not valor.is_finite():
                        raise InvalidOperation()
                except InvalidOperation as exc:
                    raise ErrorValidacion("Valor debe ser un número finito", numero, "valor", row.get("valor")) from exc
                if llave in observaciones:
                    if observaciones[llave] != valor:
                        raise ErrorValidacion("Dos valores distintos para el mismo DPA/año", numero, "valor", valor)
                    duplicados += 1
                observaciones[llave] = valor
        if meta["estructura"] == "registro":
            observaciones = {k: Decimal(len(v)) for k, v in rucs.items()}
        return {"meta": meta, "archivo": archivo, "contenido": contenido,
                "hash": hashlib.sha256(contenido).hexdigest(), "filas": len(raw),
                "observaciones": observaciones, "territorios": territorios,
                "duplicados": duplicados, "reglas": reglas}

    def previsualizar(self, fuentes):
        if len(fuentes) != 2:
            raise ErrorValidacion("Selecciona exactamente dos fuentes")
        preparados = [self.preparar(f) for f in fuentes]
        self._validar_par(preparados)
        claves = [set(p["observaciones"]) for p in preparados]
        return {"coincidencias_dpa_anio": len(claves[0] & claves[1]),
                "solo_fuente_a": len(claves[0] - claves[1]),
                "solo_fuente_b": len(claves[1] - claves[0]),
                "observaciones": [len(k) for k in claves]}

    @staticmethod
    def _validar_par(preparados):
        if len({p["meta"]["nombre"].casefold() for p in preparados}) != 2:
            raise ErrorValidacion("Las dos fuentes deben tener nombres distintos")
        if len({p["meta"]["indicador_codigo"] for p in preparados}) != 2:
            raise ErrorValidacion("Usa códigos de indicador distintos para las dos fuentes")
        if not set(preparados[0]["observaciones"]) & set(preparados[1]["observaciones"]):
            raise ErrorValidacion("Las fuentes no comparten ningún DPA y año; revisa nivel territorial y periodo")

    @staticmethod
    def _id(conn, tabla, valores):
        return conn.execute(insert(tabla).values(**valores)).inserted_primary_key[0]

    def ejecutar_dos_fuentes_csv(self, fuentes):
        monitor = MonitorEjecucion()
        inicio = monitor.inicio
        with self.persistencia.engine.begin() as conn:
            eid = self._id(conn, m.ejecucion, {"inicio": inicio, "estado": "en_curso"})
        leidas = 0
        try:
            if len(fuentes) != 2:
                raise ErrorValidacion("Selecciona exactamente dos fuentes")
            preparados = []
            for fuente in fuentes:
                try:
                    p = self.preparar(fuente)
                except Exception:
                    leidas += self._filas_actuales
                    raise
                leidas += p["filas"]
                preparados.append(p)
            self._validar_par(preparados)
            comunes = set(preparados[0]["observaciones"]) & set(preparados[1]["observaciones"])
            cargadas, omitidas, versiones = 0, 0, []
            with self.persistencia.engine.begin() as conn:
                # Serializa las cargas de esta aplicación: evita carreras en catálogos/versiones.
                if conn.dialect.name == "postgresql":
                    conn.execute(text("SELECT pg_advisory_xact_lock(72412026)"))
                for p in preparados:
                    meta = p["meta"]
                    src = conn.execute(select(m.fuente).where(m.fuente.c.nombre == meta["nombre"])).mappings().first()
                    if src and src["estructura"] != meta["estructura"]:
                        raise ErrorValidacion("No cambies la estructura de una fuente existente")
                    if src:
                        fid = src["id"]
                    else:
                        fid = self._id(conn, m.fuente, {"nombre": meta["nombre"], "publicador": meta["publicador"],
                            "url_descarga": meta["url_descarga"], "licencia": meta["licencia"], "formato": "CSV",
                            "estructura": meta["estructura"], "descripcion": meta.get("descripcion", ""), "creado_en": ahora()})
                    ind = conn.execute(select(m.indicador).where(m.indicador.c.codigo == meta["indicador_codigo"])).mappings().first()
                    if ind and (ind["fuente_id"] != fid or ind["unidad"] != meta["unidad"]):
                        raise ErrorValidacion("El indicador existente pertenece a otra fuente o tiene otra unidad")
                    iid = ind["id"] if ind else self._id(conn, m.indicador, {
                        "codigo": meta["indicador_codigo"], "nombre": meta["indicador_nombre"],
                        "unidad": meta["unidad"], "fuente_id": fid, "descripcion": meta.get("descripcion", "")})
                    version = conn.execute(select(m.version_fuente).where(m.version_fuente.c.hash_sha256 == p["hash"])).mappings().first()
                    if version and (version["fuente_id"] != fid or version["fecha_actualizacion_fuente"] != meta["fecha_actualizacion"]):
                        raise ErrorValidacion("Este archivo ya está registrado con otra fuente o fecha de publicación")
                    if version:
                        vid = version["id"]
                    else:
                        archive = Path(__file__).resolve().parent / ".local" / "archivos"
                        archive.mkdir(parents=True, exist_ok=True)
                        path = archive / (p["hash"] + ".csv")
                        if not path.exists():
                            path.write_bytes(p["contenido"])
                        vid = self._id(conn, m.version_fuente, {
                            "fuente_id": fid, "fecha_actualizacion_fuente": meta["fecha_actualizacion"],
                            "fecha_descarga": ahora(), "nombre_archivo": p["archivo"], "ruta_local": str(path),
                            "hash_sha256": p["hash"], "tamano_bytes": len(p["contenido"]), "filas_originales": p["filas"]})
                    versiones.append(vid)
                    tids = {}
                    for codigo in sorted(p["territorios"], key=lambda c: (len(c), c)):
                        t = dict(p["territorios"][codigo])
                        padre = t.pop("padre")
                        t["territorio_padre_id"] = tids.get(padre)
                        old = conn.execute(select(m.territorio).where(m.territorio.c.codigo_dpa == codigo)).mappings().first()
                        if old and any(old[k] != t[k] for k in ("nombre_normalizado", "nivel", "territorio_padre_id")):
                            raise ErrorValidacion(f"El DPA {codigo} contradice el catálogo territorial")
                        tids[codigo] = old["id"] if old else self._id(conn, m.territorio, t)
                    existentes = conn.execute(select(m.observacion.c.indicador_id, m.territorio.c.codigo_dpa,
                        m.observacion.c.anio, m.observacion.c.valor).select_from(m.observacion.join(m.territorio)
                        ).where(m.observacion.c.version_fuente_id == vid)).all()
                    if existentes:
                        esperado = {(iid, codigo, anio): valor for (codigo, anio), valor in p["observaciones"].items()}
                        real = {(i, c, a): v for i, c, a, v in existentes}
                        if real != esperado:
                            raise ErrorValidacion("La versión ya fue cargada con otra interpretación; no se sobrescribe")
                    n = 0
                    if not existentes:
                        for (codigo, anio), valor in p["observaciones"].items():
                            self._id(conn, m.observacion, {"indicador_id": iid, "territorio_id": tids[codigo],
                                "anio": anio, "valor": valor, "version_fuente_id": vid,
                                "ejecucion_id": eid, "creado_en": ahora()})
                            n += 1
                    cargadas += n
                    duplicados = p["filas"] if existentes else p["duplicados"]
                    omitidas += duplicados
                    conn.execute(insert(m.ejecucion_version).values(ejecucion_id=eid, version_fuente_id=vid,
                        filas_leidas=p["filas"], filas_cargadas=n))
                    metricas = {"completitud": (100, "porcentaje"), "duplicados": (duplicados, "filas"),
                        "territorios_sin_cruce": (len(set(p["observaciones"]) - comunes), "territorios_anio"),
                        "observaciones_cargadas": (n, "observaciones")}
                    for codigo, (valor, unidad) in metricas.items():
                        conn.execute(insert(m.metrica_calidad).values(ejecucion_id=eid, version_fuente_id=vid,
                            metrica=codigo, valor=valor, unidad=unidad, registrado_en=ahora()))
                    descripcion = json.dumps({"reglas": p["reglas"], "estructura": meta["estructura"],
                        "validacion": "DPA 2/4/6, jerarquia, anio 1900-2100, valor finito o RUC 13 digitos; carga atomica"},
                        sort_keys=True, ensure_ascii=False)
                    codigo_regla = "perfil_" + hashlib.sha256(descripcion.encode()).hexdigest()
                    if not conn.execute(select(m.regla.c.id).where(m.regla.c.codigo == codigo_regla)).first():
                        self._id(conn, m.regla, {"codigo": codigo_regla, "nombre": "Perfil de carga",
                            "tipo": "transformacion", "descripcion": descripcion})
                conn.execute(update(m.ejecucion).where(m.ejecucion.c.id == eid).values(
                    **monitor.finalizar("exitosa", leidas, cargadas, 0,
                        f"Integración por DPA/año: {len(comunes)} coincidencias; {omitidas} duplicados omitidos")))
            return {"ejecucion_id": eid, "filas_extraidas": leidas, "filas_insertadas": cargadas,
                    "duplicados_omitidos": omitidas, "coincidencias_dpa_anio": len(comunes), "versiones": versiones}
        except Exception as exc:
            fin = ahora()
            with self.persistencia.engine.begin() as conn:
                if conn.dialect.name == "postgresql":
                    conn.execute(text("SELECT pg_advisory_xact_lock(72412026)"))
                rid = conn.execute(select(m.regla.c.id).where(m.regla.c.codigo == "validacion_relacional")).scalar()
                if rid is None:
                    rid = self._id(conn, m.regla, {"codigo": "validacion_relacional", "nombre": "Validación relacional",
                        "tipo": "validacion", "descripcion": "Metadatos, DPA, año, valores, identidad de versiones y referencias."})
                conn.execute(update(m.ejecucion).where(m.ejecucion.c.id == eid).values(
                    **monitor.finalizar("fallida", leidas, 0, leidas, str(exc))))
                conn.execute(insert(m.error_ejecucion).values(ejecucion_id=eid, regla_id=rid,
                    tipo_error=type(exc).__name__, mensaje=str(exc),
                    fila_origen=getattr(exc, "fila", None), columna=getattr(exc, "columna", None),
                    valor_original=getattr(exc, "valor", None), registrado_en=fin))
            raise
