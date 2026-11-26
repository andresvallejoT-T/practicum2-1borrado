"""Inicia PostgreSQL y abre pgAdmin sin ventana de terminal en Windows."""
from pathlib import Path
import os
import subprocess
import tkinter as tk
from tkinter import messagebox

root = Path(__file__).resolve().parent
try:
    result = subprocess.run(
        [str(root / '.venv/Scripts/python.exe'), str(root / 'local.py'), 'iniciar'],
        cwd=root, capture_output=True, text=True, errors='replace',
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    candidates = [
        Path(os.environ['LOCALAPPDATA']) / 'Programs/pgAdmin 4/runtime/pgAdmin4.exe',
        Path(os.environ['ProgramFiles']) / 'pgAdmin 4/runtime/pgAdmin4.exe',
    ]
    executable = next((path for path in candidates if path.is_file()), None)
    if executable is None:
        raise RuntimeError('No se encuentra pgAdmin 4. Instálalo antes de abrir este acceso.')
    subprocess.Popen([str(executable)], cwd=executable.parent)
except Exception as error:
    window = tk.Tk()
    window.withdraw()
    messagebox.showerror('OpenData - pgAdmin', str(error))
    window.destroy()
