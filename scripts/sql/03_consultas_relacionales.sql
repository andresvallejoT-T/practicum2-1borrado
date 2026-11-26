-- Consultas de lectura para abrir también en Query Tool de pgAdmin.
BEGIN TRANSACTION READ ONLY;

-- 1. Base y usuario conectados.
SELECT current_database() AS base, current_user AS usuario, version();

-- 2. Conteos de las diez entidades.
SELECT 'fuente' AS tabla, count(*) AS filas FROM fuente
UNION ALL SELECT 'version_fuente', count(*) FROM version_fuente
UNION ALL SELECT 'indicador', count(*) FROM indicador
UNION ALL SELECT 'territorio', count(*) FROM territorio
UNION ALL SELECT 'observacion', count(*) FROM observacion
UNION ALL SELECT 'ejecucion', count(*) FROM ejecucion
UNION ALL SELECT 'ejecucion_version', count(*) FROM ejecucion_version
UNION ALL SELECT 'regla', count(*) FROM regla
UNION ALL SELECT 'error_ejecucion', count(*) FROM error_ejecucion
UNION ALL SELECT 'metrica_calidad', count(*) FROM metrica_calidad
ORDER BY tabla;

-- 3. Observaciones con su fuente, territorio, unidad y versión.
SELECT f.nombre AS fuente, i.codigo AS indicador, t.codigo_dpa,
       t.nombre AS territorio, o.anio, o.valor, i.unidad,
       o.version_fuente_id AS version, o.ejecucion_id AS ejecucion
FROM observacion o
JOIN indicador i ON i.id = o.indicador_id
JOIN fuente f ON f.id = i.fuente_id
JOIN territorio t ON t.id = o.territorio_id
ORDER BY i.codigo, t.codigo_dpa, o.anio, o.version_fuente_id;

-- 4. Cruce de los indicadores demo. Se usa una versión por territorio y año.
WITH ordenadas AS (
    SELECT o.*, i.codigo,
           row_number() OVER (
               PARTITION BY o.indicador_id, o.territorio_id, o.anio
               ORDER BY v.fecha_actualizacion_fuente DESC,
                        v.fecha_descarga DESC, v.id DESC
           ) AS posicion
    FROM observacion o
    JOIN indicador i ON i.id = o.indicador_id
    JOIN version_fuente v ON v.id = o.version_fuente_id
)
SELECT t.codigo_dpa, t.nombre AS territorio, a.anio,
       a.valor AS poblacion_demo, b.valor AS ruc_distintos_demo,
       a.version_fuente_id AS version_poblacion,
       b.version_fuente_id AS version_ruc
FROM ordenadas a
JOIN ordenadas b ON b.territorio_id = a.territorio_id AND b.anio = a.anio
JOIN territorio t ON t.id = a.territorio_id
WHERE a.codigo = 'demo_poblacion' AND b.codigo = 'demo_ruc'
  AND a.posicion = 1 AND b.posicion = 1
ORDER BY a.anio, t.codigo_dpa;

-- 5. Jerarquía territorial.
SELECT t.codigo_dpa, t.nombre, t.nivel,
       p.codigo_dpa AS dpa_padre, p.nombre AS nombre_padre
FROM territorio t LEFT JOIN territorio p ON p.id = t.territorio_padre_id
ORDER BY t.codigo_dpa;

-- 6. Histórico de ejecución.
SELECT id, estado, filas_leidas, filas_cargadas, filas_rechazadas,
       duracion_segundos, mensaje
FROM ejecucion ORDER BY id DESC LIMIT 10;

-- 7. Comprobaciones: todos los resultados deben ser cero.
SELECT 'grupos_duplicados' AS comprobacion, count(*) AS problemas
FROM (
    SELECT 1 FROM observacion
    GROUP BY indicador_id, territorio_id, anio, version_fuente_id HAVING count(*) > 1
) duplicados
UNION ALL
SELECT 'observaciones_huerfanas', count(*)
FROM observacion o
LEFT JOIN indicador i ON i.id=o.indicador_id
LEFT JOIN territorio t ON t.id=o.territorio_id
LEFT JOIN version_fuente v ON v.id=o.version_fuente_id
LEFT JOIN ejecucion e ON e.id=o.ejecucion_id
WHERE i.id IS NULL OR t.id IS NULL OR v.id IS NULL OR e.id IS NULL
UNION ALL
SELECT 'fuentes_inconsistentes', count(*)
FROM observacion o JOIN indicador i ON i.id=o.indicador_id
JOIN version_fuente v ON v.id=o.version_fuente_id
WHERE i.fuente_id <> v.fuente_id;

-- 8. Errores registrados.
SELECT id, ejecucion_id, fila_origen, columna, tipo_error, mensaje
FROM error_ejecucion ORDER BY id DESC LIMIT 10;

COMMIT;

