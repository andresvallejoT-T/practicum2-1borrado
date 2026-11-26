"""Carga demostrativa relacional y comprobación HTTP real."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import urlopen
from sqlalchemy import text, select, func
from PipelineETL import PipelineETL
from demo import fuentes_demo
import modelo as m

def comprobar(condicion, mensaje):
    if not condicion:
        raise AssertionError(mensaje)

def main():
    motor = PipelineETL()
    gestor = motor.persistencia
    comprobar(gestor.engine.dialect.name == "postgresql", "Esta verificación requiere PostgreSQL")
    try:
        reporte = {"primera_carga": motor.ejecutar_dos_fuentes_csv(fuentes_demo()),
                   "segunda_carga": motor.ejecutar_dos_fuentes_csv(fuentes_demo())}
        comprobar(reporte["segunda_carga"]["filas_insertadas"] == 0, "Recarga no idempotente")
        cruce = gestor.cruzar_indicadores("demo_poblacion", "demo_ruc", 2026)
        comprobar([(r["codigo_dpa"], int(r["valor_a"]), int(r["valor_b"])) for r in cruce]
                   == [("1101", 200, 2), ("1102", 100, 1)], "Cruce incorrecto")
        reporte["cruce"] = cruce
        with gestor.engine.connect() as conn:
            reporte["conexion"] = dict(conn.execute(text("SELECT version(), current_database(), current_user")).mappings().one())
            reporte["conteos"] = {table.name: conn.scalar(select(func.count()).select_from(table))
                                  for table in m.metadata.sorted_tables}
            comprobar(not conn.execute(text("SELECT indicador_id FROM observacion GROUP BY indicador_id, territorio_id, anio, version_fuente_id HAVING count(*) > 1")).first(), "Duplicados en observacion")
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        with Path(".local/api-prueba.log").open("w", encoding="utf-8") as log:
            proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "api:app", "--host", "127.0.0.1", "--port", str(port)],
                stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            try:
                for _ in range(80):
                    try:
                        with urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as r:
                            reporte["health"] = json.load(r)
                        break
                    except OSError:
                        if proc.poll() is not None:
                            raise RuntimeError("La API no arrancó; revisa .local/api-prueba.log")
                        time.sleep(0.25)
                else:
                    raise RuntimeError("La API no responde")
                reporte["api"] = {}
                for endpoint in ("fuentes", "observaciones", "ejecuciones", "versiones", "indicadores", "territorios", "metricas", "reglas",
                                 "cruce?indicador_a=demo_poblacion&indicador_b=demo_ruc&anio=2026"):
                    with urlopen(f"http://127.0.0.1:{port}/api/v1/{endpoint}", timeout=10) as r:
                        payload = json.load(r)
                        comprobar(payload["total"] > 0, f"Respuesta vacía: {endpoint}")
                        reporte["api"][endpoint] = {"http": r.status, "total": payload["total"]}
            finally:
                proc.terminate()
                proc.wait(timeout=10)
        reporte["resultado"] = "OK"
        salida = json.dumps(reporte, indent=2, ensure_ascii=False, default=str)
        Path(".local/verificacion.json").write_text(salida, encoding="utf-8")
        print(salida)
    finally:
        gestor.engine.dispose()

if __name__ == "__main__":
    main()
