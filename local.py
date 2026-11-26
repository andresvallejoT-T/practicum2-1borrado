"""PostgreSQL local: python local.py iniciar|detener|verificar|api|web|sql."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
LOCAL = ROOT / ".local"
BIN = LOCAL / "pgsql" / "bin"
DATA = LOCAL / "pgdata"
CONFIG = LOCAL / "conexion.json"


def run(*args, foreground=False, **kwargs):
    command = [str(a) for a in args]
    if foreground:
        return subprocess.run(command, check=True, **kwargs)
    # Windows console handles may stop working with CREATE_NO_WINDOW.
    # Capture finite commands through pipes, then print in the parent console.
    child_env = os.environ.copy()
    child_env.update(PYTHONIOENCODING="utf-8", PGCLIENTENCODING="UTF8")
    result = subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=child_env,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        **kwargs,
    )
    if result.stdout:
        print(result.stdout, end="", flush=True)
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr, flush=True)
    result.check_returncode()
    return result


def iniciar():
    LOCAL.mkdir(exist_ok=True)
    if not CONFIG.exists():
        if (DATA / "PG_VERSION").exists():
            raise RuntimeError("Existe pgdata pero falta conexion.json. Restaura las credenciales originales; no se regeneran.")
        CONFIG.write_text(json.dumps({"port": 55432, "password": secrets.token_hex(24),
                                     "admin_password": secrets.token_hex(24)}), encoding="utf-8")
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    if not (DATA / "PG_VERSION").exists():
        password_file = LOCAL / "init-password.txt"
        password_file.write_text(config["admin_password"], encoding="utf-8")
        try:
            run(BIN / "initdb.exe", "-D", DATA, "-U", "postgres", "-E", "UTF8",
                "--locale=C", "--auth=scram-sha-256", "--pwfile", password_file)
        finally:
            password_file.unlink(missing_ok=True)
        with (DATA / "postgresql.conf").open("a", encoding="utf-8") as file:
            file.write(f"\nlisten_addresses = '127.0.0.1'\nport = {config['port']}\n")
    status = subprocess.run([str(BIN / "pg_ctl.exe"), "-D", str(DATA), "status"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    if status.returncode:
        # El servidor permanece vivo: no heredar pipes de captura del lanzador.
        # En Windows estos handles pueden impedir que communicate() termine.
        subprocess.run([str(BIN / "pg_ctl.exe"), "-D", str(DATA), "-l",
                        str(LOCAL / "postgres.log"), "-w", "start"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    import psycopg
    from psycopg import sql
    with psycopg.connect(host="127.0.0.1", port=config["port"], user="postgres",
                         password=config["admin_password"], dbname="postgres", autocommit=True) as conn:
        if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname = 'opendata'").fetchone():
            conn.execute(sql.SQL("CREATE ROLE opendata LOGIN PASSWORD {}").format(sql.Literal(config["password"])))
        if not conn.execute("SELECT 1 FROM pg_database WHERE datname = 'opendata'").fetchone():
            conn.execute("CREATE DATABASE opendata OWNER opendata")
    os.environ["DATABASE_URL"] = f"postgresql+psycopg://opendata:{config['password']}@127.0.0.1:{config['port']}/opendata"
    from GestorPersistencia import GestorPersistencia
    gestor = GestorPersistencia()
    gestor.engine.dispose()
    print(f"PostgreSQL disponible: 127.0.0.1:{config['port']}/opendata (usuario opendata)", flush=True)
    return config


if __name__ == "__main__":
    os.chdir(ROOT)
    action = sys.argv[1] if len(sys.argv) > 1 else "iniciar"
    if action == "detener":
        run(BIN / "pg_ctl.exe", "-D", DATA, "-m", "fast", "-w", "stop")
    elif action in {"iniciar", "verificar", "pruebas", "api", "web", "sql"}:
        config = iniciar()
        if action == "verificar":
            run(sys.executable, ROOT / "verificar_postgres.py")
        elif action == "pruebas":
            run(sys.executable, "-m", "unittest", "-v", "test_relacional")
        elif action == "api":
            run(sys.executable, "-m", "uvicorn", "api:app", "--host", "127.0.0.1", "--port", "8000", foreground=True)
        elif action == "web":
            print("Abre http://127.0.0.1:8501 y deja esta terminal abierta.", flush=True)
            run(sys.executable, "-m", "streamlit", "run", "app.py", "--server.address", "127.0.0.1",
                "--server.port", "8501", "--server.headless", "true",
                "--browser.gatherUsageStats", "false", foreground=True)
        elif action == "sql":
            os.environ["PGPASSWORD"] = config["password"]
            run(BIN / "psql.exe", "-X", "-v", "ON_ERROR_STOP=1", "-P", "pager=off",
                "-h", "127.0.0.1", "-p", config["port"], "-U", "opendata", "-d", "opendata",
                "-f", ROOT / "scripts" / "sql" / "02_consultas_verificacion.sql")
    else:
        raise SystemExit("Acciones: iniciar, detener, verificar, pruebas, api, web, sql")
