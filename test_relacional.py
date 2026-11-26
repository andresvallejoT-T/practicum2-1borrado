"""Pruebas aisladas: esquema PostgreSQL temporal o archivo SQLite temporal."""
import copy
from datetime import date
from decimal import Decimal
import os
from pathlib import Path
import tempfile
import unittest
import uuid
from sqlalchemy import create_engine, text, select, func, insert
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from PipelineETL import PipelineETL, ErrorValidacion
from GestorPersistencia import ahora
from demo import fuentes_demo
import modelo as m


class ModeloRelacionalTests(unittest.TestCase):
    def setUp(self):
        self.original_url = os.environ.get("DATABASE_URL")
        self.admin = None
        if self.original_url and self.original_url.startswith("postgresql"):
            self.schema = "test_etl_" + uuid.uuid4().hex
            self.admin = create_engine(self.original_url)
            with self.admin.begin() as conn:
                conn.execute(text(f'CREATE SCHEMA "{self.schema}"'))
            url = make_url(self.original_url).update_query_dict({"options": f"-csearch_path={self.schema}"})
            self.url = url.render_as_string(hide_password=False)
        else:
            self.temp = tempfile.TemporaryDirectory()
            self.url = "sqlite:///" + str(Path(self.temp.name) / "test.db")
        self.motor = PipelineETL(conexion_db=self.url)
        self.g = self.motor.persistencia
        self.fuentes = fuentes_demo()

    def tearDown(self):
        self.g.engine.dispose()
        if self.admin:
            # Solamente el esquema aleatorio creado por esta prueba, nunca public.
            assert self.schema.startswith("test_etl_") and len(self.schema) == 41
            with self.admin.begin() as conn:
                conn.execute(text(f'DROP SCHEMA "{self.schema}" CASCADE'))
            self.admin.dispose()
        else:
            self.temp.cleanup()

    def count(self, tabla):
        with self.g.engine.connect() as conn:
            return conn.scalar(select(func.count()).select_from(tabla))

    def test_carga_idempotencia_y_cruce(self):
        resultado = self.motor.ejecutar_dos_fuentes_csv(self.fuentes)
        self.assertEqual(resultado["filas_insertadas"], 4)
        self.assertEqual(resultado["duplicados_omitidos"], 1)
        self.assertEqual(self.motor.ejecutar_dos_fuentes_csv(self.fuentes)["filas_insertadas"], 0)
        self.assertEqual(self.count(m.fuente), 2)
        self.assertEqual(self.count(m.version_fuente), 2)
        self.assertEqual(self.count(m.observacion), 4)
        self.assertEqual(self.count(m.ejecucion_version), 4)
        cruce = self.g.cruzar_indicadores("demo_poblacion", "demo_ruc", 2026)
        self.assertEqual([(r["codigo_dpa"], int(r["valor_a"]), int(r["valor_b"])) for r in cruce],
                         [("1101", 200, 2), ("1102", 100, 1)])
        with self.g.engine.connect() as conn:
            hijos = conn.execute(select(m.territorio).where(m.territorio.c.nivel == "canton")).mappings().all()
            self.assertTrue(all(t["territorio_padre_id"] is not None for t in hijos))

    def test_nueva_version_y_cruce_sin_multiplicar_filas(self):
        self.motor.ejecutar_dos_fuentes_csv(self.fuentes)
        self.fuentes[0]["contenido"] = self.fuentes[0]["contenido"].replace(b",200", b",250")
        self.fuentes[0]["metadatos"]["fecha_actualizacion"] = "2026-11-27"
        self.assertEqual(self.motor.ejecutar_dos_fuentes_csv(self.fuentes)["filas_insertadas"], 2)
        self.assertEqual(self.count(m.version_fuente), 3)
        self.assertEqual(self.count(m.observacion), 6)
        cruce = self.g.cruzar_indicadores("demo_poblacion", "demo_ruc", 2026)
        self.assertEqual(len(cruce), 2)
        self.assertEqual(cruce[0]["valor_a"], Decimal(250))

    def test_rollback_si_segunda_fuente_contradice_territorio(self):
        self.fuentes[1]["contenido"] = self.fuentes[1]["contenido"].replace(b",Calvas,", b",Otro,")
        with self.assertRaisesRegex(ErrorValidacion, "contradice"):
            self.motor.ejecutar_dos_fuentes_csv(self.fuentes)
        for tabla in (m.fuente, m.version_fuente, m.observacion, m.territorio, m.ejecucion_version, m.metrica_calidad):
            self.assertEqual(self.count(tabla), 0, tabla.name)
        self.assertEqual(self.g.obtener_ejecuciones()[0]["estado"], "fallida")
        self.assertEqual(self.count(m.error_ejecucion), 1)

    def test_dpa_invalido_y_error_con_fila(self):
        self.fuentes[0]["contenido"] = self.fuentes[0]["contenido"].replace(b"1101", b"101", 1)
        with self.assertRaises(ErrorValidacion):
            self.motor.ejecutar_dos_fuentes_csv(self.fuentes)
        error = self.g.listar(m.error_ejecucion)[0]
        self.assertEqual(error["fila_origen"], 2)
        self.assertEqual(error["columna"], "codigo_dpa")
        self.assertEqual(self.count(m.observacion), 0)

    def test_sin_cruce_por_anio(self):
        self.fuentes[1]["contenido"] = self.fuentes[1]["contenido"].replace(b"2026", b"2025")
        with self.assertRaisesRegex(ErrorValidacion, "no comparten"):
            self.motor.ejecutar_dos_fuentes_csv(self.fuentes)
        self.assertEqual(self.count(m.fuente), 0)

    def test_valor_conflictivo_y_no_finito(self):
        for valor in (b"NaN", b"Infinity", b""):
            with self.subTest(valor=valor):
                fuentes = copy.deepcopy(self.fuentes)
                fuentes[0]["contenido"] = fuentes[0]["contenido"].replace(b",200", b"," + valor)
                with self.assertRaises(ErrorValidacion):
                    self.motor.ejecutar_dos_fuentes_csv(fuentes)
        self.fuentes[0]["contenido"] += b"1101,Loja,Loja,2026,999\n"
        with self.assertRaisesRegex(ErrorValidacion, "valores distintos"):
            self.motor.ejecutar_dos_fuentes_csv(self.fuentes)
        self.assertEqual(self.count(m.observacion), 0)

    def test_ceros_iniciales_y_parroquia(self):
        for f in self.fuentes:
            f["contenido"] = f["contenido"].replace(b"1101", b"010101").replace(b"1102", b"010102")
            lines = f["contenido"].decode().splitlines()
            f["contenido"] = ("\n".join([lines[0] + ",canton"] + [line + ",Canton demo" for line in lines[1:]]) + "\n").encode()
        self.motor.ejecutar_dos_fuentes_csv(self.fuentes)
        territorios = self.g.listar(m.territorio)
        self.assertEqual({t["codigo_dpa"] for t in territorios}, {"01", "0101", "010101", "010102"})
        self.assertEqual(self.count(m.observacion), 4)

    def test_fk_y_unicidad_en_base(self):
        self.motor.ejecutar_dos_fuentes_csv(self.fuentes)
        with self.g.engine.connect() as conn:
            row = dict(conn.execute(select(m.observacion)).mappings().first())
        row.pop("id")
        with self.assertRaises(IntegrityError):
            with self.g.engine.begin() as conn:
                conn.execute(insert(m.observacion).values(**row))
        row["territorio_id"] = 9999999
        with self.assertRaises(IntegrityError):
            with self.g.engine.begin() as conn:
                conn.execute(insert(m.observacion).values(**row))

    def test_reinterpretacion_de_version_rechazada(self):
        self.motor.ejecutar_dos_fuentes_csv(self.fuentes)
        self.fuentes[0]["metadatos"]["indicador_codigo"] = "otra_interpretacion"
        with self.assertRaisesRegex(ErrorValidacion, "otra interpretación"):
            self.motor.ejecutar_dos_fuentes_csv(self.fuentes)
        self.assertEqual(self.count(m.indicador), 2)
        self.assertEqual(self.count(m.observacion), 4)

    def test_cargas_concurrentes_postgresql(self):
        if self.g.engine.dialect.name != "postgresql":
            self.skipTest("Bloqueo asesor específico de PostgreSQL")
        from concurrent.futures import ThreadPoolExecutor
        segundo = PipelineETL(conexion_db=self.url)
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                resultados = list(pool.map(lambda motor: motor.ejecutar_dos_fuentes_csv(fuentes_demo()),
                                           [self.motor, segundo]))
            self.assertEqual(sorted(r["filas_insertadas"] for r in resultados), [0, 4])
            self.assertEqual(self.count(m.observacion), 4)
            self.assertEqual(self.count(m.version_fuente), 2)
        finally:
            segundo.persistencia.engine.dispose()

    def test_subida_de_archivos_en_tablero(self):
        from streamlit.testing.v1 import AppTest
        import streamlit as st
        st.cache_resource.clear()
        os.environ["DATABASE_URL"] = self.url
        try:
            app = AppTest.from_file(str(Path(__file__).parent / "app.py")).run(timeout=30)
            self.assertFalse(app.exception)
            for idx, fuente in enumerate(self.fuentes):
                meta = fuente["metadatos"]
                for field, valor in (("nombre", meta["nombre"]), ("publicador", meta["publicador"]),
                    ("url", meta["url_descarga"]), ("licencia", meta["licencia"])):
                    app.text_input(key=f"{field}_{idx}_Nueva fuente").set_value(valor)
                app.date_input(key=f"fecha_{idx}").set_value(date(2026, 11, 26))
                app.selectbox(key=f"estructura_{idx}_Nueva fuente").set_value(meta["estructura"])
                app.text_input(key=f"indicador_{idx}").set_value(meta["indicador_codigo"])
                app.text_input(key=f"indicador_nombre_{idx}").set_value(meta["indicador_nombre"])
                app.text_input(key=f"unidad_{idx}").set_value(meta["unidad"])
                app.file_uploader(key=f"archivo_fuente_{idx}").set_value(
                    (fuente["archivo"], fuente["contenido"], "text/csv"))
            app.run(timeout=30)
            next(b for b in app.button if b.label == "Integrar las dos fuentes").click().run(timeout=30)
            self.assertFalse(app.exception, [e.message for e in app.exception])
            self.assertFalse(app.error, [e.value for e in app.error])
            self.assertTrue(any("Carga completa" in s.value for s in app.success))
            self.assertEqual(self.count(m.observacion), 4)
            next(b for b in app.button if b.label == "Integrar las dos fuentes").click().run(timeout=30)
            self.assertFalse(app.exception)
            self.assertEqual(self.count(m.observacion), 4)
        finally:
            st.cache_resource.clear()
            if self.original_url is None:
                os.environ.pop("DATABASE_URL", None)
            else:
                os.environ["DATABASE_URL"] = self.original_url

if __name__ == "__main__":
    unittest.main(verbosity=2)
