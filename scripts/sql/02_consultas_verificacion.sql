-- Compatible con psql y con Query Tool de pgAdmin.
BEGIN TRANSACTION READ ONLY;
SELECT version(), current_database(), current_user;
SELECT table_name FROM information_schema.tables
WHERE table_schema='public' AND table_name NOT LIKE 'etl_%' ORDER BY table_name;
SELECT f.nombre, v.id AS version_id, v.nombre_archivo, v.hash_sha256,
       v.filas_originales, count(o.id) AS observaciones
FROM fuente f JOIN version_fuente v ON v.fuente_id=f.id
LEFT JOIN observacion o ON o.version_fuente_id=v.id
GROUP BY f.nombre, v.id ORDER BY f.nombre, v.id;
SELECT t.codigo_dpa, t.nombre, i.codigo, o.anio, o.valor, o.version_fuente_id
FROM observacion o JOIN territorio t ON t.id=o.territorio_id
JOIN indicador i ON i.id=o.indicador_id ORDER BY i.codigo,t.codigo_dpa,o.version_fuente_id;
SELECT indicador_id, territorio_id, anio, version_fuente_id, count(*)
FROM observacion GROUP BY indicador_id,territorio_id,anio,version_fuente_id HAVING count(*)>1;
SELECT e.id,e.estado,e.filas_leidas,e.filas_cargadas,e.filas_rechazadas,e.mensaje
FROM ejecucion e ORDER BY e.id DESC LIMIT 10;
SELECT * FROM metrica_calidad ORDER BY id DESC LIMIT 12;
SELECT * FROM error_ejecucion ORDER BY id DESC LIMIT 5;
-- Debe devolver cero: indicador y versión de una observación pertenecen a la misma fuente.
SELECT count(*) AS referencias_fuente_inconsistentes
FROM observacion o JOIN indicador i ON i.id=o.indicador_id
JOIN version_fuente v ON v.id=o.version_fuente_id WHERE i.fuente_id<>v.fuente_id;
COMMIT;

