from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Callable, Sequence

from Extractor import Extractor
from GestorPersistencia import GestorPersistencia
from MonitorEjecucion import MonitorEjecucion
from Transformador import Transformador


class PipelineETL:
    def __init__(
        self,
        fuente: Any = None,
        reglas_transformacion: dict[str, Any] | None = None,
        conexion_db: str | None = None,
    ) -> None:
        self.fuente = fuente
        self.reglas = reglas_transformacion or {}
        self.monitor = MonitorEjecucion()
        self.extractor = Extractor(fuente)
        self.persistencia = GestorPersistencia(conexion_db)

    def ejecutar(self, ruta_archivo: str | None = None) -> dict[str, Any] | None:
        def extraer() -> tuple[str | None, list[dict[str, Any]] | None]:
            ruta = ruta_archivo or self.extractor.seleccionar_archivo()
            if not ruta:
                return None, None
            ruta_resuelta = Path(ruta).expanduser().resolve()
            return str(ruta_resuelta), self.extractor.leer_csv(ruta_resuelta)

        return self._ejecutar_con_extractor(extraer)

    def ejecutar_contenido_csv(
        self,
        contenido: bytes,
        nombre_archivo: str,
    ) -> dict[str, Any]:
        return self._ejecutar_con_extractor(
            lambda: (
                nombre_archivo,
                self.extractor.leer_csv_contenido(contenido, nombre_archivo),
            )
        )

    def comparar_fuentes_csv(
        self,
        contenido_a: bytes,
        nombre_a: str,
        contenido_b: bytes,
        nombre_b: str,
    ) -> dict[str, Any]:
        columnas_a = self._preparar_fuente(contenido_a, nombre_a)["columnas"]
        columnas_b = self._preparar_fuente(contenido_b, nombre_b)["columnas"]
        set_a = set(columnas_a)
        set_b = set(columnas_b)
        return {
            "compatible": bool(set_a) and set_a == set_b,
            "columnas_comunes": sorted(set_a & set_b),
            "solo_fuente_a": sorted(set_a - set_b),
            "solo_fuente_b": sorted(set_b - set_a),
        }

    def ejecutar_dos_fuentes_csv(
        self,
        fuentes: Sequence[dict[str, Any]],
    ) -> dict[str, Any]:
        self.monitor = MonitorEjecucion()
        self.monitor.iniciar_cronometro()
        try:
            if len(fuentes) != 2:
                raise ValueError("Para integrar información se requieren exactamente dos fuentes.")

            preparadas = [
                self._preparar_fuente(
                    fuente["contenido"],
                    fuente.get("archivo", fuente["nombre"]),
                )
                for fuente in fuentes
            ]
            columnas_a = set(preparadas[0]["columnas"])
            columnas_b = set(preparadas[1]["columnas"])
            if not columnas_a or columnas_a != columnas_b:
                raise ValueError(
                    "Las fuentes no son compatibles. Normaliza o renombra sus columnas "
                    "para que ambas tengan el mismo esquema antes de integrarlas. "
                    f"Solo en la primera: {sorted(columnas_a - columnas_b)}; "
                    f"solo en la segunda: {sorted(columnas_b - columnas_a)}."
                )

            nombres = [
                fuente.get("metadatos", {}).get("nombre", fuente["nombre"])
                for fuente in fuentes
            ]
            if len({nombre.strip().casefold() for nombre in nombres}) != 2:
                raise ValueError("Cada fuente debe tener un nombre único en el catálogo.")
            self.monitor.registrar_origen(" + ".join(nombres))
            filas_insertadas = 0
            duplicados_omitidos = 0
            filas_entrada = 0
            filas_transformadas = 0
            calidad_fuentes: dict[str, Any] = {}

            for fuente, preparada, nombre in zip(fuentes, preparadas, nombres):
                datos = preparada["datos"]
                filas_entrada += preparada["filas_entrada"]
                filas_transformadas += len(datos)
                calidad_fuentes[nombre] = preparada["calidad"]

                metadatos = dict(fuente.get("metadatos", {}))
                metadatos.update(
                    {
                        "nombre": nombre,
                        "formato": "CSV",
                        "columnas": preparada["columnas"],
                        "filas_disponibles": len(datos),
                        "fecha_registro": datetime.now(timezone.utc),
                    }
                )
                self.persistencia.registrar_fuente(metadatos)

                duplicados_omitidos += self.persistencia.comprobar_duplicados(datos)
                filas_insertadas += self.persistencia.almacenar_datos(datos, origen=nombre)

            metricas = {
                "fuentes_integradas": nombres,
                "compatibilidad": "compatible",
                "columnas_integradas": sorted(columnas_a),
                "filas_extraidas": filas_entrada,
                "filas_transformadas": filas_transformadas,
                "filas_insertadas": filas_insertadas,
                "duplicados_omitidos": duplicados_omitidos,
                "calidad_por_fuente": calidad_fuentes,
            }
            self.monitor.actualizar_metricas(
                filas_transformadas,
                {
                    "fuentes_integradas": len(nombres),
                    "columnas_comunes": len(columnas_a),
                    "filas_extraidas": filas_entrada,
                    "filas_insertadas": filas_insertadas,
                    "duplicados_omitidos": duplicados_omitidos,
                    "filas_eliminadas_nulos": sum(
                        calidad["filas_eliminadas_nulos"]
                        for calidad in calidad_fuentes.values()
                    ),
                    "duplicados_eliminados": sum(
                        calidad["duplicados_eliminados"]
                        for calidad in calidad_fuentes.values()
                    ),
                },
            )
            return metricas
        except Exception as error:
            self.monitor.registrar_error(f"{type(error).__name__}: {error}")
            raise
        finally:
            self.monitor.detener_cronometro()
            self.monitor.guardar_registro_ejecucion(self.persistencia)

    def _preparar_fuente(self, contenido: bytes, nombre: str) -> dict[str, Any]:
        datos_crudos = self.extractor.leer_csv_contenido(contenido, nombre)
        if not datos_crudos:
            raise ValueError(f"El archivo '{nombre}' no contiene registros para integrar.")

        transformador = Transformador(datos_crudos)
        datos = transformador.normalizar_columnas()
        datos = transformador.normalizar_tipos_y_fechas(self.reglas)
        datos = transformador.aplicar_reglas_validacion(self.reglas)
        columnas = sorted({columna for registro in datos for columna in registro})
        return {
            "datos": datos,
            "columnas": columnas,
            "filas_entrada": len(datos_crudos),
            "calidad": dict(transformador.indicadores_calidad),
        }

    def _ejecutar_con_extractor(
        self,
        extraer: Callable[
            [],
            tuple[str | None, list[dict[str, Any]] | None],
        ],
    ) -> dict[str, Any] | None:
        self.monitor = MonitorEjecucion()
        self.monitor.iniciar_cronometro()
        try:
            origen, datos_crudos = extraer()
            if origen is None or datos_crudos is None:
                self.monitor.marcar_cancelada()
                print("Selección de archivo cancelada.")
                return None

            self.monitor.registrar_origen(origen)

            transformador = Transformador(datos_crudos)
            datos_limpios = transformador.normalizar_columnas()
            datos_limpios = transformador.normalizar_tipos_y_fechas(self.reglas)
            datos_limpios = transformador.aplicar_reglas_validacion(self.reglas)

            duplicados = self.persistencia.comprobar_duplicados(datos_limpios)
            filas_insertadas = self.persistencia.almacenar_datos(
                datos_limpios,
                origen=origen,
            )
            metricas = {
                "filas_extraidas": len(datos_crudos),
                "filas_transformadas": len(datos_limpios),
                "filas_insertadas": filas_insertadas,
                "duplicados_omitidos": duplicados,
            }
            self.monitor.actualizar_metricas(len(datos_limpios), metricas)
            return metricas
        except Exception as error:
            self.monitor.registrar_error(f"{type(error).__name__}: {error}")
            raise
        finally:
            self.monitor.detener_cronometro()
            self.monitor.guardar_registro_ejecucion(self.persistencia)


if __name__ == "__main__":
    pipeline = PipelineETL(reglas_transformacion={})
    resultado = pipeline.ejecutar()
    if resultado is not None:
        print("Ejecución ETL finalizada.")
        print(f"Filas extraídas: {resultado['filas_extraidas']}")
        print(f"Filas insertadas: {resultado['filas_insertadas']}")
        print(f"Duplicados omitidos: {resultado['duplicados_omitidos']}")
        print(f"Duración: {pipeline.monitor.duracion:.2f} segundos")
        print(f"Estado: {pipeline.monitor.estado}")
