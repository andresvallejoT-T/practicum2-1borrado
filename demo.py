"""Archivos ficticios: no representan cifras ni RUC reales."""
from pathlib import Path

def fuentes_demo():
    root = Path(__file__).resolve().parent / "ejemplos"
    fuentes = []
    for archivo, nombre, codigo, titulo, unidad, estructura in [
        ("poblacion_demo.csv", "Demo INEC", "demo_poblacion", "Poblacion ficticia", "personas", "agregada"),
        ("ruc_demo.csv", "Demo SRI", "demo_ruc", "Contribuyentes ficticios", "contribuyentes", "registro"),
    ]:
        fuentes.append({"nombre": nombre, "archivo": archivo, "contenido": (root / archivo).read_bytes(),
            "metadatos": {"nombre": nombre, "publicador": "Prueba local, no oficial",
                "url_descarga": "ejemplo local", "licencia": "CC0", "fecha_actualizacion": "2026-11-26",
                "estructura": estructura, "indicador_codigo": codigo,
                "indicador_nombre": titulo, "unidad": unidad}})
    return fuentes
