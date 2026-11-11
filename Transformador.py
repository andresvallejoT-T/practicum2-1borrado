import re
import unicodedata
from collections.abc import Iterable, Mapping
from datetime import date, datetime
from typing import Any


class Transformador:
    def __init__(self, datos_crudos: Iterable[Mapping[str, Any]]) -> None:
        self.datos = [dict(registro) for registro in datos_crudos]
        self.indicadores_calidad: dict[str, int] = {
            "filas_entrada": len(self.datos),
            "filas_salida": len(self.datos),
            "filas_eliminadas_nulos": 0,
            "duplicados_eliminados": 0,
        }

    @staticmethod
    def _nombre_columna(columna: str) -> str:
        texto = columna.strip().lower().replace("ñ", "n")
        texto = unicodedata.normalize("NFKD", texto)
        texto = "".join(caracter for caracter in texto if not unicodedata.combining(caracter))
        texto = re.sub(r"[^a-z0-9]+", "_", texto)
        return re.sub(r"_+", "_", texto).strip("_")

    @staticmethod
    def _es_nulo(valor: Any) -> bool:
        return valor is None or (isinstance(valor, str) and not valor.strip())

    def normalizar_columnas(self) -> list[dict[str, Any]]:
        registros: list[dict[str, Any]] = []
        for numero_fila, registro in enumerate(self.datos, start=1):
            normalizado: dict[str, Any] = {}
            for columna, valor in registro.items():
                if not isinstance(columna, str):
                    raise TypeError(f"El nombre de columna en la fila {numero_fila} debe ser texto.")
                nombre = self._nombre_columna(columna)
                if not nombre:
                    raise ValueError(f"La columna de la fila {numero_fila} tiene un nombre vacío.")
                if nombre in normalizado:
                    raise ValueError(
                        f"Columnas duplicadas después de normalizar en fila {numero_fila}: "
                        f"'{nombre}'."
                    )
                normalizado[nombre] = valor
            registros.append(normalizado)
        self.datos = registros
        return self.datos

    def _renombrar_columnas(self, reglas: Mapping[str, Any]) -> None:
        renombres = reglas.get("renombrar_columnas", {})
        if not isinstance(renombres, Mapping):
            raise TypeError("'renombrar_columnas' debe ser un diccionario.")
        mapa = {
            self._nombre_columna(origen): self._nombre_columna(destino)
            for origen, destino in renombres.items()
            if isinstance(origen, str) and isinstance(destino, str)
        }
        registros: list[dict[str, Any]] = []
        for numero_fila, registro in enumerate(self.datos, start=1):
            renombrado: dict[str, Any] = {}
            for columna, valor in registro.items():
                destino = mapa.get(columna, columna)
                if not destino:
                    raise ValueError("Los nombres de columna transformados no pueden estar vacíos.")
                if destino in renombrado:
                    raise ValueError(
                        f"El renombrado genera una columna duplicada en la fila {numero_fila}: "
                        f"'{destino}'."
                    )
                renombrado[destino] = valor
            registros.append(renombrado)
        self.datos = registros

    @staticmethod
    def _convertir_valor(valor: Any, tipo: Any, fila: int, columna: str) -> Any:
        if valor is None or (isinstance(valor, str) and not valor.strip()):
            return None
        nombre_tipo = tipo if isinstance(tipo, str) else getattr(tipo, "__name__", "")
        nombre_tipo = nombre_tipo.lower()
        try:
            if nombre_tipo in {"date", "datetime", "fecha"}:
                if isinstance(valor, (date, datetime)):
                    return valor.isoformat()
                if not isinstance(valor, str):
                    raise ValueError("la fecha debe estar en formato de texto")
                try:
                    return date.fromisoformat(valor.strip()).isoformat()
                except ValueError:
                    formatos = ("%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y")
                    for formato in formatos:
                        try:
                            return datetime.strptime(valor.strip(), formato).date().isoformat()
                        except ValueError:
                            continue
                    raise ValueError("formato de fecha no reconocido")
            if nombre_tipo in {"int", "integer", "entero"}:
                if isinstance(valor, bool):
                    raise ValueError("un booleano no es un entero de datos válido")
                return int(valor)
            if nombre_tipo in {"float", "number", "decimal", "numero"}:
                return float(str(valor).replace(",", "."))
            if nombre_tipo in {"bool", "boolean", "booleano"}:
                if isinstance(valor, bool):
                    return valor
                normalizado = str(valor).strip().lower()
                if normalizado in {"1", "true", "si", "sí", "yes", "verdadero"}:
                    return True
                if normalizado in {"0", "false", "no", "falso"}:
                    return False
                raise ValueError("valor booleano no reconocido")
            if nombre_tipo in {"str", "string", "texto"}:
                return str(valor)
            raise ValueError(f"tipo no soportado: {tipo!r}")
        except (TypeError, ValueError, OverflowError) as error:
            raise ValueError(
                f"Error convirtiendo fila {fila}, columna '{columna}' "
                f"al tipo '{nombre_tipo}': {valor!r}"
            ) from error

    def normalizar_tipos_y_fechas(
        self,
        reglas: Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        reglas = reglas or {}
        self._renombrar_columnas(reglas)
        tipos = reglas.get("tipos", {})
        fechas = reglas.get("fechas", [])
        if not isinstance(tipos, Mapping):
            raise TypeError("'tipos' debe ser un diccionario de columnas y tipos.")
        if isinstance(fechas, str):
            fechas = [fechas]
        if not isinstance(fechas, Iterable):
            raise TypeError("'fechas' debe ser una lista de columnas.")

        tipos_normalizados = {
            self._nombre_columna(columna): tipo
            for columna, tipo in tipos.items()
            if isinstance(columna, str)
        }
        fechas_normalizadas = {
            self._nombre_columna(columna)
            for columna in fechas
            if isinstance(columna, str)
        }
        registros: list[dict[str, Any]] = []
        for numero_fila, registro in enumerate(self.datos, start=1):
            convertido: dict[str, Any] = {}
            for columna, valor in registro.items():
                tipo = tipos_normalizados.get(columna)
                if tipo is not None:
                    convertido[columna] = self._convertir_valor(
                        valor, tipo, numero_fila, columna
                    )
                elif columna in fechas_normalizadas:
                    convertido[columna] = self._convertir_valor(
                        valor, "date", numero_fila, columna
                    )
                else:
                    convertido[columna] = valor
            registros.append(convertido)
        self.datos = registros
        return self.datos

    def aplicar_reglas_validacion(
        self,
        reglas: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        if not isinstance(reglas, Mapping):
            raise TypeError("'reglas' debe ser un diccionario.")

        requeridas = reglas.get("columnas_requeridas", [])
        if isinstance(requeridas, str):
            requeridas = [requeridas]
        if not isinstance(requeridas, Iterable):
            raise TypeError("'columnas_requeridas' debe ser una lista de columnas.")
        columnas_requeridas = {
            self._nombre_columna(columna)
            for columna in requeridas
            if isinstance(columna, str)
        }
        disponibles = {columna for registro in self.datos for columna in registro}
        faltantes = columnas_requeridas - disponibles
        if faltantes:
            raise ValueError(
                "Faltan columnas requeridas: " + ", ".join(sorted(faltantes))
            )

        eliminar_nulos = reglas.get("eliminar_nulos", False)
        if not isinstance(eliminar_nulos, bool):
            raise TypeError("'eliminar_nulos' debe ser booleano.")
        filas_antes = len(self.datos)
        if eliminar_nulos:
            self.datos = [
                registro
                for registro in self.datos
                if not any(self._es_nulo(valor) for valor in registro.values())
            ]
        eliminadas = filas_antes - len(self.datos)

        eliminar_duplicados = reglas.get("eliminar_duplicados", True)
        if not isinstance(eliminar_duplicados, bool):
            raise TypeError("'eliminar_duplicados' debe ser booleano.")
        duplicados = 0
        if eliminar_duplicados:
            unicos: list[dict[str, Any]] = []
            vistos: set[str] = set()
            for registro in self.datos:
                llave = repr(sorted(registro.items()))
                if llave in vistos:
                    duplicados += 1
                else:
                    vistos.add(llave)
                    unicos.append(registro)
            self.datos = unicos

        self.indicadores_calidad.update(
            {
                "filas_salida": len(self.datos),
                "filas_eliminadas_nulos": eliminadas,
                "duplicados_eliminados": duplicados,
            }
        )
        return self.datos
