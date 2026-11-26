# Modelo relacional OpenData ETL

## Esquema implementado

La definición ejecutable está en `modelo.py`. `scripts/sql/01_esquema.sql` contiene el DDL
equivalente para PostgreSQL. Incluye las diez entidades del diagrama:

| Tabla | Finalidad y relaciones |
|---|---|
| fuente | Catálogo, publicador, procedencia, licencia, formato y estructura |
| version_fuente | Archivo y SHA-256 único; FK a fuente |
| indicador | Código único, nombre, unidad; FK a fuente |
| territorio | DPA único; FK a su territorio padre |
| observacion | Indicador, territorio, año, valor NUMERIC, versión y ejecución |
| ejecucion | Inicio, fin, estado, duración y contadores |
| ejecucion_version | PK compuesta ejecución/versión y contadores por archivo |
| regla | Catálogo de perfiles y validación |
| error_ejecucion | Ejecución, regla, versión opcional, fila, columna y detalle |
| metrica_calidad | Métrica por ejecución/versión, con restricción única |

Claves primarias BIGINT (BIGSERIAL en PostgreSQL), fechas con zona horaria,
año SMALLINT, valores NUMERIC. La observación es única por
(indicador, territorio, año, versión). Como restricciones adicionales al diagrama:
nombre de fuente único, dominios de estado/estructura/nivel, año entre 1900 y
2100 y contadores no negativos. SHA-256 se almacena como VARCHAR(64), de
longitud fija lógica, en vez de CHAR(64); el pipeline siempre genera 64 caracteres.

## Actualización desde el modelo anterior

`local.py iniciar` crea las tablas nuevas de forma aditiva e idempotente.
No elimina ni modifica `etl_fuentes`, `etl_registros` ni `etl_ejecuciones`.
Estas tablas quedan como histórico de la primera versión; el tablero y la API
nuevos ya no las usan. En este equipo se creó antes del cambio el respaldo
`.local/antes_modelo_relacional.dump`.

No se convierten automáticamente los JSON antiguos: faltan DPA, año e identidad
del indicador. Deben volver a cargarse desde un CSV enriquecido con información
verificada. No se inventan territorios ni periodos para completar campos.
En una instalación nueva solo se crean las diez tablas relacionales.

Antes de actualizar otro equipo con datos, hacer un respaldo con `pg_dump`.
Reiniciar el tablero/API después de actualizar. En pgAdmin refrescar
`Schemas > public > Tables` para ver las tablas nuevas.

## Contrato de entrada CSV

Cada carga integra exactamente dos fuentes y un indicador por fuente. Pueden
tener columnas diferentes: se cruzan por DPA y año, no por igualdad de encabezados.
Se exige al menos una coincidencia. Los territorios que solo existen en una
fuente se conservan y se contabilizan; no se fabrican observaciones de la otra.

Metadatos por fuente: nombre, publicador, URL/procedencia, licencia, fecha de
actualización ISO, estructura, código y nombre del indicador, unidad.
La versión se identifica por el SHA-256 del archivo original.

**Agregada**: `codigo_dpa,territorio,provincia,anio,valor`.
El valor se procesa como Decimal y se guarda en NUMERIC. Dos filas con el mismo
DPA/año e igual valor se deduplican; si difieren, se rechaza toda la carga.

**Registro**: `codigo_dpa,territorio,provincia,anio,ruc`.
Se cuentan RUC distintos por DPA/año. Un RUC repetido en ese grupo se cuenta una
vez. No es un conteo de establecimientos. El RUC se valida por formato (13
dígitos); no se comprueba su dígito verificador ni existencia en el SRI.

DPA se conserva como texto de 2, 4 o 6 dígitos, con ceros iniciales:
provincia, cantón, parroquia. Para cantones se exige `provincia`; para
parroquias se exigen `provincia` y `canton`. La columna `territorio`
es el nombre de la unidad observada. Los padres se construyen por prefijos y
sus nombres proceden del archivo. El catálogo rechaza contradicciones de nombre
normalizado, nivel o padre.

**Esto valida estructura y consistencia, no pertenencia al catálogo oficial DPA.**
Los datos INEC/SRI reales requieren verificar su diccionario y periodo, filtrar
el universo deseado y mapear encabezados. La interfaz permite un mapa JSON por
fuente; por ejemplo `{"poblacion": "valor", "nombre_canton": "territorio"}`.
No se infiere el año de publicación como año de observación. No hay descarga
automática de INEC/SRI ni lectura Excel.

## Transacciones, versiones y trazabilidad

Una ejecución comienza como `en_curso`. Fuentes, versiones, territorios,
indicadores, observaciones, relaciones y métricas se guardan en una sola
transacción. Si falla cualquier fuente se revierte esa transacción y se conserva
la ejecución `fallida` y un error con regla/fila/columna cuando están disponibles.
La versión del error puede ser nula porque la creación de la versión se revirtió.
Los archivos originales se conservan bajo `.local/archivos/<sha256>.csv`;
una carga revertida puede dejar un archivo sin referencia, pero no datos parciales
en las tablas del modelo.

Una recarga de los mismos bytes no crea versiones ni observaciones nuevas.
Si cambia el archivo, se crea otra versión y se preserva el histórico.
Reinterpretar una versión cargada con otro indicador o valores se rechaza;
cambiar su fuente o fecha de publicación también se rechaza. El esquema impone
SHA-256 globalmente único, como en el diagrama: los mismos bytes no pueden
registrarse bajo fuentes distintas.

En PostgreSQL las cargas de esta aplicación se serializan mediante un bloqueo
transaccional asesor, además de las restricciones únicas y FK. Las escrituras
externas directas deben respetar también las invariantes del servicio (jerarquía
por prefijos y coherencia de fuente entre indicador y versión).

Estados del diagrama: en_curso, exitosa, fallida, parcial. Este pipeline usa una
política atómica: no produce cargas parciales. Un cierre forzado del proceso puede
dejar una ejecución en_curso y requiere revisión; no se marca exitosa automáticamente.

Contadores: filas_leidas cuenta filas CSV extraídas antes del error; filas_cargadas
cuenta observaciones insertadas (un grupo de RUC puede producir una sola).
filas_rechazadas cuenta filas leídas revertidas en una ejecución fallida.
En recargas, duplicados cuenta filas de entrada omitidas; en cargas nuevas,
filas repetidas dentro del archivo. Las métricas se guardan por ejecución/versión:
completitud de campos requeridos (100 % para cargas exitosas), duplicados,
territorios_sin_cruce y observaciones_cargadas. No son una certificación de la
calidad de la fuente real.

## Consulta, API y tablero

`GET /api/v1/observaciones` consulta columnas relacionales; admite origen,
codigo_dpa, anio y limite. Los decimales se serializan como cadenas para conservar
su precisión. `/api/v1/registros` es un alias obsoleto y **cambia su respuesta**:
ya no devuelve datos JSON genéricos. La API ahora es versión 2.

`GET /api/v1/cruce?indicador_a=demo_poblacion&indicador_b=demo_ruc&anio=2026`
elige una versión por indicador/territorio/año, ordenando por fecha de publicación,
fecha de descarga e id. Así evita multiplicar filas por versiones históricas.
Usa intersección de DPA/año y conserva los ids de ambas versiones.

También hay endpoints de fuentes, versiones, indicadores, territorios,
ejecuciones, errores, métricas y reglas. `/health` consulta realmente la base.

El tablero permite subir archivos, mapear columnas, validar, integrar, consultar
catálogos/versiones/observaciones, descargar resultados, cruzar indicadores y
ver errores/métricas. Los ejemplos descargables son sintéticos.

## Verificación reproducible

```powershell
.\.venv\Scripts\python.exe local.py verificar
.\.venv\Scripts\python.exe local.py sql
.\.venv\Scripts\python.exe local.py pruebas
```

La demo conserva 2 fuentes, 2 versiones, 2 indicadores, 3 territorios
(Loja provincia y cantones Loja/Calvas) y 4 observaciones. El cruce esperado es:

| DPA | Territorio | Población ficticia | RUC distintos ficticios |
|---|---|---:|---:|
| 1101 | Loja | 200 | 2 |
| 1102 | Calvas | 100 | 1 |

La suite crea y elimina exclusivamente esquemas temporales `test_etl_<uuid>`
en PostgreSQL. Prueba recarga, versiones, preservación de ceros y jerarquía,
FK/unicidad, rollback, valores inválidos, ausencia de cruces, reinterpretaciones
y subida de dos archivos mediante AppTest y los botones del tablero.
Para SQLite aislado: `python -m unittest -v test_relacional` sin DATABASE_URL.

La prueba del tablero usa el runtime de Streamlit con archivos subidos simulados;
no sustituye una revisión visual de todos los navegadores. La API se prueba por
HTTP real con Uvicorn. Las pruebas no validan datasets oficiales INEC/SRI.

Validación realizada: 11 pruebas en PostgreSQL aprobadas, incluidas dos cargas
concurrentes; 10 en SQLite aprobadas (concurrencia PostgreSQL no aplica).
También se abrió el tablero real en el navegador y se comprobó la tabla de cruce
con Loja y Calvas. Fue necesario reiniciar Streamlit para descartar el gestor
anterior retenido en memoria. El histórico antiguo quedó intacto: 3 registros,
2 fuentes y 8 ejecuciones. No quedaron esquemas temporales de prueba.

