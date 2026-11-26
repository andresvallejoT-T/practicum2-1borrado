# practicum2-1borrado

Sistema ETL de CSV con normalización, validación, catálogo, persistencia con
SQLAlchemy, API FastAPI y tablero Streamlit. Integra dos fuentes CSV por código DPA y año según el diagrama entidad-relación.
Cada instalación tiene su propia base de datos local; clonar el repositorio no
copia los datos ni las contraseñas de otro compañero. No requiere Docker.

## Instalación desde cero para compañeros (Windows de 64 bits)

### Opción automática: carpeta scripts

Instala Git y Python (paso 1), clona el repositorio y entra en su carpeta. Luego:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\00_instalar_todo.ps1 -ConDemo
```

Prepara dependencias, PostgreSQL, base y tablas, instala/configura pgAdmin y carga
los ejemplos. Cierra pgAdmin antes de ejecutarlo. Omite `-ConDemo` si quieres la
base vacía. No cambia la política permanente de PowerShell ni requiere Docker.

La [guía de scripts](scripts/README.md) explica cada paso, requisitos y solución
de errores. Las consultas para abrir en Query Tool están en [scripts/sql](scripts/sql).
Para ejecutar las consultas desde PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\06_consultas.ps1
```

Los pasos manuales siguientes siguen disponibles como alternativa.

Esta ruta reproduce el entorno local probado. Los lanzadores `local.py` y
`abrir_pgadmin.pyw` están preparados para Windows, no para Linux o macOS.

### 1. Instalar Git y Python

Instala [Git para Windows](https://git-scm.com/downloads/win) y
[Python](https://www.python.org/downloads/windows/) con soporte para `venv` y
`pip`. El entorno comprobado usa Python **3.11.9 de 64 bits**; Python 3.12 es
la versión sugerida en la guía original, pero no se ha probado aquí.
En el instalador de Python marca la opción para agregarlo al PATH.
Abre una terminal PowerShell nueva y comprueba:

```powershell
git --version
python --version
```

Si `python` no se reconoce pero `py` sí, usa `py -3.11` para crear el entorno
virtual en el paso siguiente. Si `python` abre la tienda, instala Python y
vuelve a abrir la terminal antes de continuar.

### 2. Clonar y preparar las dependencias

Ejecuta desde la carpeta donde quieras guardar el proyecto:

```powershell
git clone https://github.com/andresvallejoT-T/practicum2-1borrado.git
cd practicum2-1borrado
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
```

El último comando debe indicar `No broken requirements found`.
No es necesario activar el entorno ni cambiar la política de PowerShell.
Los siguientes pasos se ejecutan siempre dentro de `practicum2-1borrado`.
Las dependencias usan rangos de versiones; una instalación futura puede resolver
versiones distintas a las probadas. Ejecuta también las verificaciones del paso 4.

### 3. Descargar PostgreSQL local

Esta instalación usa binarios portables y no modifica otros servicios PostgreSQL.
Descarga la versión utilizada y verifica su integridad antes de extraerla:

```powershell
New-Item -ItemType Directory -Force .local | Out-Null
curl.exe -fL --retry 2 -o .local\postgresql.zip https://get.enterprisedb.com/postgresql/postgresql-17.12-2-windows-x64-binaries.zip
if ($LASTEXITCODE -ne 0) { throw 'No se pudo descargar PostgreSQL' }
$expected = '520c8c6f19abb3b31fa83ec5e486e2f769eedd7593d94e60a7cda8a5bfb4df91'
if ((Get-FileHash .local\postgresql.zip -Algorithm SHA256).Hash -ne $expected) {
    throw 'El archivo no coincide con el checksum verificado; no continuar'
}
tar.exe -xf .local\postgresql.zip -C .local pgsql/bin pgsql/lib pgsql/share
if ($LASTEXITCODE -ne 0) { throw 'No se pudo extraer PostgreSQL' }
Test-Path .local\pgsql\bin\pg_ctl.exe
```

El último comando debe devolver `True`. Si no dispones de `tar.exe`, extrae
el ZIP desde el Explorador y coloca la carpeta `pgsql` dentro de `.local`;
la ruta final debe ser `.local\pgsql\bin\pg_ctl.exe`, sin carpetas extra.
Si el enlace deja de estar disponible, consulta los
[binarios de EDB](https://www.enterprisedb.com/download-postgresql-binaries);
otra versión requiere su propio checksum, no omitas la comprobación.

### 4. Crear la base y ejecutar las pruebas

```powershell
.\.venv\Scripts\python.exe local.py iniciar
.\.venv\Scripts\python.exe local.py verificar
.\.venv\Scripts\python.exe local.py sql
```

`iniciar` crea un clúster local, contraseñas aleatorias, el usuario `opendata`,
su base y las diez tablas relacionales del proyecto. No tienes que crear la base manualmente.
El puerto `55432` debe estar libre antes del primer arranque.

La verificación debe terminar con `"resultado": "OK"`. En una instalación
nueva deja **4 observaciones, 2 fuentes, 2 versiones y 2 ejecuciones**. El cruce devuelve Loja (200 personas ficticias, 2 RUC distintos) y Calvas (100, 1).
Repetirla añade historial pero no duplica los registros. Son datos sintéticos.

### 5. Abrir el programa

```powershell
.\.venv\Scripts\python.exe local.py web
```

Abre [http://127.0.0.1:8501](http://127.0.0.1:8501) y deja la terminal abierta.
Para la API, abre otra terminal en esta carpeta y ejecuta:

```powershell
.\.venv\Scripts\python.exe local.py api
```

Documentación de la API: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).
Para cargar datos, usa la pestaña **Integrar fuentes**, elige dos CSV, completa
nombre, publicador, procedencia, licencia, fecha e indicador de cada fuente, revisa su
compatibilidad y ejecuta la integración. Consulta después **Datos**, **Cruce territorial** y **Monitoreo**.
Actualmente no se admite Excel. Se probó la carga de dos archivos y el botón de integración con AppTest de Streamlit, además de la API por HTTP real.

### 6. Ver las tablas con pgAdmin (opcional)

Instala [pgAdmin 4 para Windows](https://www.pgadmin.org/download/pgadmin-4-windows/).
También puedes instalarlo con:

```powershell
winget install --id PostgreSQL.pgAdmin --exact --source winget
```

Con PostgreSQL iniciado, abre pgAdmin. En **Servers**, clic derecho →
**Register → Server**. En **General**, escribe `OpenData local`.
En **Connection**, completa:

| Campo | Valor |
|---|---|
| Host name/address | `127.0.0.1` |
| Port | `55432` |
| Maintenance database | `opendata` |
| Username | `opendata` |
| Password | Campo `password` de tu archivo `.local/conexion.json` |

Abre ese archivo con un editor local. Usa `password`, no `admin_password`.
Cada compañero tiene una contraseña distinta. Guarda la conexión y despliega
**Databases → opendata → Schemas → public → Tables**. Clic derecho sobre una
tabla → **View/Edit Data → All Rows**.

Para crear en tu equipo el acceso que abre PostgreSQL y pgAdmin sin terminal:

```powershell
$project = (Get-Location).Path
$shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $project 'Abrir base de datos.lnk'))
$shortcut.TargetPath = Join-Path $project '.venv\Scripts\pythonw.exe'
$shortcut.Arguments = '"' + (Join-Path $project 'abrir_pgadmin.pyw') + '"'
$shortcut.WorkingDirectory = $project
$shortcut.Description = 'Inicia PostgreSQL y abre pgAdmin'
$shortcut.Save()
```

Después basta con hacer doble clic en **Abrir base de datos**. El lanzador
busca pgAdmin en las ubicaciones habituales de instalación por usuario o sistema.
No registra la conexión automáticamente en otro equipo: hazlo una vez como se
indica arriba. Si mueves el repositorio, vuelve a crear el acceso directo.

### 7. Uso diario y problemas frecuentes

- Tras reiniciar Windows, abre el acceso gráfico o ejecuta `local.py iniciar`.
  PostgreSQL no se instala como servicio de arranque automático.
- Si no abre el tablero, usa `127.0.0.1:8501`, comprueba la salida de la terminal
  y mantenla abierta. La API usa el puerto `8000`.
- Si hay error de conexión, ejecuta `local.py iniciar` y revisa
  `.local/postgres.log`. Comprueba que otro proceso no esté usando `55432`.
- Si aparece `ModuleNotFoundError`, repite la instalación de `requirements.txt`
  usando `.venv\Scripts\python.exe`, no el Python global.
- Si pgAdmin pide contraseña, usa la de tu `.local/conexion.json`.
- No borres `.local/pgdata`: contiene tus datos. Tampoco borres
  `.local/conexion.json`, que conserva las credenciales del clúster.
- `.venv`, `.local`, las contraseñas y los accesos `.lnk` no se suben a Git.
  Si quieren compartir datos reales entre equipos, necesitan una base compartida
  o una exportación/importación; esta guía configura bases independientes.

## Estado de publicación

Los pasos anteriores requieren publicar la versión actual completa del código,
incluidas las carpetas `scripts` y `ejemplos`, el modelo relacional y los lanzadores.
Al preparar esta guía, los cambios siguen locales y todavía no se han
subido a GitHub. Una clonación no recibe esos archivos hasta que se publiquen.

## Entorno local preparado (26 de noviembre de 2026)

- Python 3.11.9 y dependencias de `requirements.txt` instaladas en `.venv`.
- PostgreSQL 17.12 en `.local/pgsql`; datos persistentes en `.local/pgdata`.
- Servidor: `127.0.0.1`, puerto `55432`, base y usuario: `opendata`.
- Contraseñas generadas en `.local/conexion.json`, excluido de Git.
- El usuario de la aplicación no es superusuario; es propietario de su base.
- PostgreSQL queda iniciado, pero no se ha instalado como servicio de Windows.
  Después de reiniciar el equipo, usar `iniciar` o cualquiera de los comandos
  de aplicación, que arrancan PostgreSQL si hace falta.

Desde esta carpeta en PowerShell:

```powershell
# Iniciar PostgreSQL y crear las tablas si todavía no existen
.\.venv\Scripts\python.exe local.py iniciar

# Ejecutar consultas SQL de diagnóstico
.\.venv\Scripts\python.exe local.py sql

# Repetir integración ETL, deduplicación, rollback y pruebas HTTP
.\.venv\Scripts\python.exe local.py verificar

# API: http://127.0.0.1:8000/docs
.\.venv\Scripts\python.exe local.py api

# Tablero, en otra terminal: http://127.0.0.1:8501
.\.venv\Scripts\python.exe local.py web

# Detener PostgreSQL cuando se hayan cerrado API y tablero
.\.venv\Scripts\python.exe local.py detener
```

`local.py` configura `DATABASE_URL` para los procesos que lanza. Ejecutar
directamente `streamlit` o `uvicorn` sin esa variable usa SQLite, como en el
repositorio original. Para herramientas externas, la contraseña del usuario
`opendata` es el campo `password` de `.local/conexion.json`.

## Resultados comprobados

### Acceso gráfico con pgAdmin

En este equipo está instalado pgAdmin 4 y registrada la conexión
`Practicum > OpenData local`. Haz doble clic en `Abrir base de datos.lnk`
en esta carpeta para iniciar PostgreSQL y abrir pgAdmin sin terminal.
El acceso usa `abrir_pgadmin.pyw`; el `.lnk` es específico de este equipo.

Para explorar las tablas, despliega `Databases > opendata > Schemas > public > Tables`.
Haz clic derecho en una tabla y selecciona `View/Edit Data > All Rows`.
La conexión usa `.local/pgadmin.pgpass`, excluido de Git, con la contraseña
local. No publiques ese archivo. La configuración de pgAdmin y el acceso
directo deben prepararse por separado en los equipos de los compañeros.

El modelo actual y las pruebas están documentados en [MODELO_RELACIONAL.md](MODELO_RELACIONAL.md).
La definición de tablas está en `modelo.py` y el DDL PostgreSQL en `scripts/sql/01_esquema.sql`.

- Carga inicial: 4 observaciones de 2 indicadores, 2 fuentes y 2 versiones.
- Recarga: 0 observaciones nuevas; versiones e histórico conservados.
- Cruce por DPA/año: Loja (200, 2), Calvas (100, 1), con datos ficticios.
- Pruebas de FK, unicidad, rollback, errores, versiones y carga desde los controles del tablero.
- `/health` comprueba la conexión; los endpoints usan el modelo relacional.

Ejecuta `local.py pruebas` para la suite aislada y `local.py verificar` para la
carga demostrativa y las consultas HTTP. La evidencia de esta última queda en
`.local/verificacion.json`. Cada verificación añade dos ejecuciones al historial.

Las tablas antiguas `etl_*` se conservan sin modificar y ya no alimentan el
programa. No se migran automáticamente: sus datos no tienen DPA e indicador.
Antes de esta adaptación se creó `.local/antes_modelo_relacional.dump` en este equipo.
No se han probado archivos oficiales INEC/SRI ni se valida contra un catálogo DPA
oficial; el contrato de CSV y los límites están detallados en la documentación.

## Instalación de PostgreSQL utilizada

Docker Desktop estaba presente pero no arrancó por entradas de registro
faltantes. Se usaron los [binarios oficiales distribuidos por EDB](https://www.enterprisedb.com/download-postgresql-binaries)
(`postgresql-17.12-2-windows-x64-binaries.zip`), verificando SHA-256:
`520c8c6f19abb3b31fa83ec5e486e2f769eedd7593d94e60a7cda8a5bfb4df91`.

Para reproducir en otro equipo Windows, crear `.venv`, instalar
`requirements.txt` y extraer las carpetas `pgsql/bin`, `pgsql/lib` y
`pgsql/share` del ZIP en `.local`. Luego ejecutar `local.py iniciar`.
No copiar la configuración privada ni el directorio de datos entre equipos.
