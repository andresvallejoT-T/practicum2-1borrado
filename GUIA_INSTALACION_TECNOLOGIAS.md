# Guía de instalación – Tecnologías sugeridas

**Tecnologías sugeridas:** Python, Pandas, Requests, PostgreSQL, SQLAlchemy, FastAPI, Streamlit, cron y GitHub.

Esta guía indica **en qué orden instalar** cada tecnología, **dónde descargar** los programas que no vienen con el sistema y **qué comandos copiar y pegar** para las librerías de Python.

---

## 1. Resumen: orden de instalación

| Orden | Tecnología | Tipo | ¿Se descarga aparte? |
|:---:|---|---|---|
| 1 | Git y cuenta de GitHub | Programa + servicio web | Sí |
| 2 | Python 3.12 | Programa | Sí |
| 3 | PostgreSQL | Programa (base de datos) | Sí |
| 4 | Entorno virtual de Python | Herramienta de Python | No (viene con Python) |
| 5 | Pandas | Librería de Python | No (se instala con `pip`) |
| 6 | Requests | Librería de Python | No (se instala con `pip`) |
| 7 | SQLAlchemy + driver de PostgreSQL | Librería de Python | No (se instala con `pip`) |
| 8 | FastAPI + Uvicorn | Librería de Python | No (se instala con `pip`) |
| 9 | Streamlit | Librería de Python | No (se instala con `pip`) |
| 10 | cron (programador de tareas) | Herramienta del sistema | No (ya viene en Linux y macOS) |

---

## 2. Programas que se descargan aparte

### 2.1 Git y GitHub

**Git** es el programa que controla las versiones del código. **GitHub** es el sitio web donde se guarda el repositorio.

| Qué | Enlace de descarga o registro |
|---|---|
| Git (Windows, macOS, Linux) | https://git-scm.com/downloads |
| Cuenta de GitHub (gratuita) | https://github.com/signup |
| GitHub Desktop (opcional, interfaz gráfica) | https://desktop.github.com/ |

En Windows, durante la instalación de Git deja las opciones por defecto.

Verificar la instalación:

```bash
git --version
```

Configurar tu identidad (una sola vez):

```bash
git config --global user.name "Tu Nombre"
git config --global user.email "tu_correo@ejemplo.com"
```

Clonar el repositorio del proyecto (cambia la URL por la de tu repositorio):

```bash
git clone https://github.com/USUARIO/NOMBRE-DEL-REPOSITORIO.git
cd NOMBRE-DEL-REPOSITORIO
```

---

### 2.2 Python 3.12

| Qué | Enlace de descarga |
|---|---|
| Python (todas las plataformas) | https://www.python.org/downloads/ |

**Importante en Windows:** en la primera pantalla del instalador marca la casilla **«Add python.exe to PATH»** antes de pulsar *Install Now*.

Verificar la instalación:

```bash
python --version
pip --version
```

En Linux o macOS, si `python` no funciona, usa `python3` y `pip3` en todos los comandos de esta guía.

---

### 2.3 PostgreSQL

PostgreSQL es la base de datos relacional del proyecto.

| Qué | Enlace de descarga |
|---|---|
| PostgreSQL (página oficial, todas las plataformas) | https://www.postgresql.org/download/ |
| Instalador para Windows (EDB) | https://www.enterprisedb.com/downloads/postgres-postgresql-downloads |

Durante la instalación en Windows:

1. Deja los componentes por defecto (PostgreSQL Server, pgAdmin 4, Command Line Tools).
2. Define una **contraseña** para el usuario `postgres` y **anótala**.
3. Deja el puerto por defecto: `5432`.

Verificar la instalación:

```bash
psql --version
```

Crear la base de datos del proyecto (te pedirá la contraseña de `postgres`):

```bash
psql -U postgres -c "CREATE DATABASE opendata;"
```

> **Nota:** el proyecto también funciona sin PostgreSQL. Si no se configura, usa SQLite automáticamente (archivo `opendata_etl.db`). PostgreSQL se usa cuando se define la variable `DATABASE_URL` (ver la sección 5).

---

## 3. Preparar el entorno de Python

Todos los comandos siguientes se ejecutan **dentro de la carpeta del proyecto**.

### Paso 1. Crear el entorno virtual

```bash
python -m venv .venv
```

### Paso 2. Activarlo

**Windows (PowerShell):**

```powershell
.venv\Scripts\Activate.ps1
```

**Windows (CMD):**

```cmd
.venv\Scripts\activate.bat
```

**Linux / macOS:**

```bash
source .venv/bin/activate
```

Si funciona, verás `(.venv)` al inicio de la línea de la terminal.

> Si PowerShell bloquea el script, ejecuta una sola vez:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```

### Paso 3. Actualizar pip

```bash
python -m pip install --upgrade pip
```

---

## 4. Instalar las librerías de Python

Con el entorno virtual **activado**, copia y pega cada bloque en orden.

### Opción A. Instalar todo de una vez (recomendada)

Si el proyecto trae el archivo `requirements.txt`:

```bash
pip install -r requirements.txt
```

### Opción B. Instalar una por una

#### 4.1 Pandas (análisis y tablas de datos)

```bash
pip install "pandas>=2.2,<4.0"
```

#### 4.2 Requests (descarga de datos desde URLs y APIs)

```bash
pip install requests
```

#### 4.3 SQLAlchemy (acceso a la base de datos)

```bash
pip install "SQLAlchemy>=2.0,<3.0"
```

#### 4.4 Driver de PostgreSQL (conecta SQLAlchemy con PostgreSQL)

```bash
pip install "psycopg[binary]>=3.1,<4.0"
```

#### 4.5 FastAPI y Uvicorn (API REST y servidor)

```bash
pip install "fastapi>=0.115,<1.0"
pip install "uvicorn[standard]>=0.30,<1.0"
```

#### 4.6 Streamlit (interfaz web)

```bash
pip install "streamlit>=1.40,<2.0"
```

### 4.7 Verificar que todo quedó instalado

```bash
pip list
```

Deben aparecer: `pandas`, `requests`, `SQLAlchemy`, `psycopg`, `fastapi`, `uvicorn` y `streamlit`.

Comprobación rápida desde Python:

```bash
python -c "import pandas, requests, sqlalchemy, psycopg, fastapi, uvicorn, streamlit; print('Todo instalado correctamente')"
```

### 4.8 Guardar las dependencias del proyecto

Para que otros puedan reproducir tu entorno:

```bash
pip freeze > requirements.txt
```

> `requests` no está en el `requirements.txt` original del proyecto. Si lo vas a usar, instálalo con el comando 4.2 y agrégalo al archivo.

---

## 5. Conectar el proyecto con PostgreSQL (opcional)

Define la variable de entorno `DATABASE_URL` **antes** de ejecutar el proyecto. Cambia `CLAVE` por la contraseña que elegiste al instalar PostgreSQL.

**Windows (PowerShell):**

```powershell
$env:DATABASE_URL = "postgresql+psycopg://postgres:CLAVE@localhost:5432/opendata"
```

**Linux / macOS:**

```bash
export DATABASE_URL="postgresql+psycopg://postgres:CLAVE@localhost:5432/opendata"
```

Para volver a SQLite, cierra la terminal o elimina la variable.

---

## 6. Ejecutar el proyecto

**Interfaz web (Streamlit):**

```bash
streamlit run app.py
```

Abre en: http://localhost:8501

**API REST (FastAPI), en otra terminal con el entorno activado:**

```bash
uvicorn api:app --reload
```

Documentación interactiva en: http://localhost:8000/docs

---

## 7. cron (ejecución programada)

**cron** programa tareas automáticas, por ejemplo extraer datos todos los días. **No se descarga:** ya viene instalado en Linux y macOS.

### Linux / macOS

Abrir el editor de tareas:

```bash
crontab -e
```

Ejemplo: ejecutar un script todos los días a las 02:00 (ajusta las rutas a las de tu equipo):

```cron
0 2 * * * /ruta/al/proyecto/.venv/bin/python /ruta/al/proyecto/ejecutar_etl.py >> /ruta/al/proyecto/etl.log 2>&1
```

Formato: `minuto hora día-del-mes mes día-de-la-semana comando`.

Ver las tareas programadas:

```bash
crontab -l
```

> `ejecutar_etl.py` es un nombre de ejemplo: es un script que tú debes crear y que llame al pipeline ETL.

### Windows

Windows no incluye cron. La alternativa equivalente es el **Programador de tareas** (*Task Scheduler*), que ya viene instalado. Ejemplo desde PowerShell para ejecutar un script todos los días a las 02:00 (ajusta las rutas):

```powershell
schtasks /Create /SC DAILY /ST 02:00 /TN "ETL_OpenData" /TR "C:\ruta\al\proyecto\.venv\Scripts\python.exe C:\ruta\al\proyecto\ejecutar_etl.py"
```

Opcionalmente, en Windows puedes usar cron dentro de **WSL** (Windows Subsystem for Linux): https://learn.microsoft.com/windows/wsl/install

---

## 8. Subir el proyecto a GitHub

Con Git instalado y tu cuenta creada, desde la carpeta del proyecto:

```bash
git init
git add .
git commit -m "Primer commit: proyecto ETL de datos abiertos"
git branch -M main
git remote add origin https://github.com/USUARIO/NOMBRE-DEL-REPOSITORIO.git
git push -u origin main
```

Antes, crea el repositorio vacío en https://github.com/new.

> **Recomendación:** no subas el entorno virtual ni la base local. Verifica que el archivo `.gitignore` incluya:
> ```
> .venv/
> __pycache__/
> *.db
> ```

---

## 9. Solución de problemas frecuentes

| Problema | Solución |
|---|---|
| `python` no se reconoce como comando | Reinstala Python marcando **Add python.exe to PATH**, o usa `py` en Windows |
| `ModuleNotFoundError` | Activa el entorno `.venv` y vuelve a ejecutar `pip install -r requirements.txt` |
| `pip` no se reconoce | Usa `python -m pip install ...` |
| Error al instalar `psycopg` | Usa la forma `psycopg[binary]` con comillas, como en el paso 4.4 |
| `psql` no se reconoce | Agrega la carpeta `bin` de PostgreSQL al PATH, o usa pgAdmin 4 |
| Error de autenticación en PostgreSQL | Revisa la contraseña en `DATABASE_URL` |
| Puerto 8501 ocupado | `streamlit run app.py --server.port 8502` |
| PowerShell no deja activar `.venv` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |

---

## 10. Lista de verificación final

- [ ] Git instalado (`git --version`) y cuenta de GitHub creada
- [ ] Python 3.12 instalado (`python --version`)
- [ ] PostgreSQL instalado y base `opendata` creada (opcional si se usa SQLite)
- [ ] Entorno virtual creado y activado
- [ ] Librerías instaladas (`pip list`)
- [ ] Proyecto ejecutándose con `streamlit run app.py`
- [ ] Repositorio subido a GitHub
