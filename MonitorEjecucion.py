from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any


class MonitorEjecucion:
    def __init__(self) -> None:
        self.errores: list[str] = []
        self.duracion = 0.0
        self.filas_procesadas = 0
        self.indicadores_calidad: dict[str, Any] = {}
        self.inicio: datetime | None = None
        self.fin: datetime | None = None
        self.estado = "pendiente"
        self.origen: str | None = None

    def iniciar_cronometro(self) -> None:
        if self.inicio is not None:
            raise RuntimeError("El cronómetro de esta ejecución ya fue iniciado.")
        self.inicio = datetime.now(timezone.utc)
        self.estado = "en_proceso"

    def detener_cronometro(self) -> None:
        if self.inicio is None:
            raise RuntimeError("No se puede detener un cronómetro que no se inició.")
        if self.fin is not None:
            return
        self.fin = datetime.now(timezone.utc)
        self.duracion = (self.fin - self.inicio).total_seconds()

    def registrar_error(self, error: str) -> None:
        self.errores.append(error)
        self.estado = "fallida"

    def registrar_origen(self, origen: str) -> None:
        self.origen = origen

    def marcar_cancelada(self) -> None:
        self.estado = "cancelada"

    def actualizar_metricas(
        self,
        filas: int,
        calidad: Mapping[str, Any],
    ) -> None:
        self.filas_procesadas = filas
        self.indicadores_calidad = dict(calidad)
        if self.estado == "en_proceso":
            self.estado = "completada"

    def guardar_registro_ejecucion(self, persistencia: Any) -> None:
        if self.inicio is None or self.fin is None:
            raise RuntimeError("La ejecución debe iniciarse y detenerse antes de guardarse.")

        persistencia.guardar_ejecucion(
            {
                "inicio": self.inicio,
                "fin": self.fin,
                "estado": self.estado,
                "origen": self.origen,
                "duracion_segundos": self.duracion,
                "filas_procesadas": self.filas_procesadas,
                "indicadores_calidad": self.indicadores_calidad,
                "errores": self.errores,
            }
        )
