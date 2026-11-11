import csv
from io import StringIO
from pathlib import Path
from typing import Any


class Extractor:
    def __init__(self, fuente_datos: Any = None) -> None:
        self.fuente = fuente_datos

    def seleccionar_archivo(self) -> str | None:
        import tkinter as tk
        from tkinter import filedialog

        ventana = tk.Tk()
        ventana.withdraw()
        ventana.attributes("-topmost", True)
        try:
            ruta = filedialog.askopenfilename(
                title="Selecciona el archivo CSV",
                filetypes=[("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")],
            )
        finally:
            ventana.destroy()

        return ruta or None

    def leer_csv(self, ruta_archivo: str | Path) -> list[dict[str, str | None]]:
        ruta = Path(ruta_archivo).expanduser()
        if not ruta.is_file():
            raise FileNotFoundError(f"No existe el archivo CSV: {ruta}")
        if ruta.suffix.lower() != ".csv":
            raise ValueError(f"El archivo seleccionado no tiene extensión CSV: {ruta.name}")

        return self.leer_csv_contenido(ruta.read_bytes(), ruta.name)

    def leer_csv_contenido(
        self,
        contenido: bytes,
        nombre_archivo: str,
    ) -> list[dict[str, str | None]]:
        if Path(nombre_archivo).suffix.lower() != ".csv":
            raise ValueError(f"El archivo seleccionado no tiene extensión CSV: {nombre_archivo}")

        try:
            texto = contenido.decode("utf-8-sig")
        except UnicodeDecodeError:
            texto = contenido.decode("cp1252")

        archivo = StringIO(texto, newline="")
        muestra = texto[:8192]
        try:
            dialecto = csv.Sniffer().sniff(muestra, delimiters=",;\t|")
        except csv.Error:
            dialecto = csv.excel

        lector = csv.DictReader(archivo, dialect=dialecto)
        if lector.fieldnames is None:
            raise ValueError("El CSV está vacío o no contiene una fila de encabezados.")

        encabezados = [nombre.strip() for nombre in lector.fieldnames if nombre is not None]
        if len(encabezados) != len(lector.fieldnames) or any(
            not nombre for nombre in encabezados
        ):
            raise ValueError("El CSV contiene encabezados vacíos o inválidos.")
        if len(set(encabezados)) != len(encabezados):
            raise ValueError("El CSV contiene nombres de columna duplicados.")

        registros: list[dict[str, str | None]] = []
        for numero_fila, fila in enumerate(lector, start=2):
            if None in fila:
                raise ValueError(
                    f"La fila {numero_fila} tiene más valores que columnas en el encabezado."
                )
            registros.append(
                {
                    encabezados[indice]: valor
                    for indice, valor in enumerate(fila.values())
                }
            )

        return registros
