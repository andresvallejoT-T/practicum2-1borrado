# Scripts de preparación y consultas (Windows 64 bits)

Requisitos previos: Git y Python 3.11 de 64 bits con pip/venv, conexión a Internet
y suficiente espacio para PostgreSQL y pgAdmin. Si usas otra versión compatible
de Python, puedes crear antes `.venv` manualmente. No requiere Docker.

Desde la raíz del repositorio, una vez clonado:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\00_instalar_todo.ps1 -ConDemo
```

`-ExecutionPolicy Bypass` se aplica solo a ese proceso; no cambia la política
permanente de Windows. Revisa los scripts antes de ejecutarlos.
El instalador puede pedir autorización de Windows. pgAdmin debe estar cerrado
para importar la conexión. Si falla un paso, corrige la causa y repítelo: los
pasos reutilizan las instalaciones y no borran bases existentes.

Sin `-ConDemo` se crean las tablas vacías. `-SinPgAdmin` omite pgAdmin.
No se instala Python automáticamente: evita cambiar el Python de otros proyectos.
Los scripts resuelven las rutas desde su propia ubicación, no desde tu usuario.

| Script | Acción |
|---|---|
| 00_instalar_todo.ps1 | Ejecuta preparación de Python, PostgreSQL, base, pgAdmin y demo opcional |
| 01_dependencias.ps1 | Crea .venv si falta, instala requirements.txt y ejecuta pip check |
| 02_postgres.ps1 | Descarga PostgreSQL 17.12 de EDB, verifica SHA-256 y extrae binarios locales |
| 03_pgadmin.ps1 | Instala pgAdmin con winget si falta, registra la conexión y crea el acceso gráfico |
| 04_crear_base.ps1 | Inicia el clúster, crea usuario, base opendata y las diez tablas |
| 05_datos_prueba.ps1 | Carga ejemplos ficticios y comprueba recarga, cruce y API por HTTP |
| 06_consultas.ps1 | Ejecuta consultas de lectura sobre la base local |
| 07_pruebas.ps1 | Ejecuta pruebas aisladas en esquemas temporales PostgreSQL |
| comun.ps1 | Funciones y rutas compartidas; no ejecutar directamente |

El orden individual es **01 → 02 → 04 → 03**, después 05, 06 y 07 según necesites.
Ejemplo para ejecutar solo las consultas:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\06_consultas.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\06_consultas.ps1 -Tipo diagnostico
```

## SQL para pgAdmin

| Archivo | Uso |
|---|---|
| sql/01_esquema.sql | DDL de las diez tablas, FK, claves únicas y CHECK |
| sql/02_consultas_verificacion.sql | Conexión, tablas, observaciones, versiones, historial, métricas y errores |
| sql/03_consultas_relacionales.sql | Conteos, cruce DPA/año con última versión, jerarquía e integridad |

En pgAdmin: conecta a **OpenData local**, selecciona **opendata**, abre
**Tools → Query Tool**, abre el SQL con el botón de carpeta y pulsa **F5**.
Los tres archivos son SQL compatible con pgAdmin; no contienen comandos privados
de psql. Los archivos 02 y 03 usan transacciones de solo lectura. Si interrumpes
un script o falla una consulta dentro de una transacción, ejecuta `ROLLBACK;`
antes de volver a intentarlo.

**01_esquema.sql no crea el usuario ni la base**: primero ejecuta 04, o crea y
selecciona una base por tus propios medios. El paso 04 crea las tablas directamente
desde `modelo.py`, que es la definición principal; el SQL es su equivalente
revisable para ejecución manual. No necesitas ejecutar ambos.
`IF NOT EXISTS` no modifica tablas existentes: futuras alteraciones de columnas
requerirán migraciones. Las tablas etl_* antiguas se conservan.

## Resultado de instalación

- PostgreSQL escucha únicamente en 127.0.0.1:55432.
- Usuario y base: opendata. Contraseñas distintas por equipo en .local/conexion.json.
- Los datos quedan en .local/pgdata; no se borran al repetir scripts.
- pgAdmin registra OpenData local y usa .local/pgadmin.pgpass.
- Si ya existe una conexión equivalente, se conserva y no se duplica ni reemplaza.
  Si esa conexión no tenía contraseña guardada, introdúcela una vez en pgAdmin.
- El acceso **Abrir base de datos.lnk** inicia PostgreSQL y abre pgAdmin sin terminal.
- PostgreSQL no se instala como servicio automático de Windows.
- .local, .venv y los accesos .lnk no se suben a Git. Nunca publiques credenciales.

Con demo: 4 observaciones, 2 indicadores, 2 versiones y 3 territorios.
Cruce esperado: Loja (200, 2), Calvas (100, 1). Son cifras y RUC ficticios.
Repetir 05 agrega historial pero no duplica observaciones.

## Si algo falla

- Python no encontrado: instala Python y abre otra terminal; también puedes crear
  .venv con `python -m venv .venv` antes de 01.
- Falta winget: instala pgAdmin desde https://www.pgadmin.org/download/pgadmin-4-windows/
  y repite 03. El script busca las rutas habituales por usuario y en Program Files.
- pgAdmin está abierto: ciérralo y repite 03; no se fuerza su cierre.
- Hash incorrecto: no se extrae el ZIP; revisa la descarga y el checksum oficial.
- Puerto ocupado: comprueba si pertenece al proyecto u otro servidor; no detengas
  procesos desconocidos ni borres pgdata.
- Hay datos pero falta conexion.json: restaura las credenciales originales.
- Un paso falla después de otros exitosos: los cambios completados permanecen;
  no se hace una desinstalación automática.
