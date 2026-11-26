"""Contadores y duración de una carga relacional, sin transacciones propias."""
from decimal import Decimal
from GestorPersistencia import ahora

class MonitorEjecucion:
    def __init__(self):
        self.inicio = ahora()

    def finalizar(self, estado, leidas, cargadas, rechazadas, mensaje):
        if estado not in {"exitosa", "fallida", "parcial"}:
            raise ValueError("Estado final inválido")
        fin = ahora()
        return dict(fin=fin, duracion_segundos=Decimal(str((fin-self.inicio).total_seconds())),
                    estado=estado, filas_leidas=leidas, filas_cargadas=cargadas,
                    filas_rechazadas=rechazadas, mensaje=mensaje)
