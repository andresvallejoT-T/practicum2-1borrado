-- Esquema relacional generado desde modelo.py. No borra tablas existentes.

CREATE TABLE IF NOT EXISTS ejecucion (
	id BIGSERIAL NOT NULL, 
	inicio TIMESTAMP WITH TIME ZONE NOT NULL, 
	fin TIMESTAMP WITH TIME ZONE, 
	duracion_segundos NUMERIC NOT NULL, 
	estado VARCHAR(32) NOT NULL, 
	filas_leidas INTEGER NOT NULL, 
	filas_cargadas INTEGER NOT NULL, 
	filas_rechazadas INTEGER NOT NULL, 
	mensaje TEXT, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_ejecucion_estado CHECK (estado IN ('en_curso','exitosa','fallida','parcial')), 
	CONSTRAINT ck_ejecucion_contadores CHECK (filas_leidas >= 0 AND filas_cargadas >= 0 AND filas_rechazadas >= 0 AND duracion_segundos >= 0)
)

;

CREATE TABLE IF NOT EXISTS fuente (
	id BIGSERIAL NOT NULL, 
	nombre VARCHAR(255) NOT NULL, 
	publicador VARCHAR(255) NOT NULL, 
	url_descarga TEXT NOT NULL, 
	licencia VARCHAR(512) NOT NULL, 
	formato VARCHAR(32) NOT NULL, 
	estructura VARCHAR(32) NOT NULL, 
	descripcion TEXT, 
	activa BOOLEAN NOT NULL, 
	creado_en TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_fuente_estructura CHECK (estructura IN ('agregada','registro')), 
	UNIQUE (nombre)
)

;

CREATE TABLE IF NOT EXISTS regla (
	id BIGSERIAL NOT NULL, 
	codigo VARCHAR(128) NOT NULL, 
	nombre VARCHAR(255) NOT NULL, 
	tipo VARCHAR(32) NOT NULL, 
	descripcion TEXT NOT NULL, 
	activa BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_regla_tipo CHECK (tipo IN ('transformacion','validacion')), 
	UNIQUE (codigo)
)

;

CREATE TABLE IF NOT EXISTS territorio (
	id BIGSERIAL NOT NULL, 
	codigo_dpa VARCHAR(6) NOT NULL, 
	nombre VARCHAR(255) NOT NULL, 
	nombre_normalizado VARCHAR(255) NOT NULL, 
	nivel VARCHAR(32) NOT NULL, 
	territorio_padre_id BIGINT, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_territorio_nivel CHECK ((nivel = 'provincia' AND length(codigo_dpa) = 2 AND territorio_padre_id IS NULL) OR (nivel = 'canton' AND length(codigo_dpa) = 4 AND territorio_padre_id IS NOT NULL) OR (nivel = 'parroquia' AND length(codigo_dpa) = 6 AND territorio_padre_id IS NOT NULL)), 
	CONSTRAINT ck_territorio_no_ciclo CHECK (territorio_padre_id IS NULL OR territorio_padre_id <> id), 
	UNIQUE (codigo_dpa), 
	FOREIGN KEY(territorio_padre_id) REFERENCES territorio (id)
)

;

CREATE TABLE IF NOT EXISTS indicador (
	id BIGSERIAL NOT NULL, 
	codigo VARCHAR(128) NOT NULL, 
	nombre VARCHAR(255) NOT NULL, 
	unidad VARCHAR(128) NOT NULL, 
	descripcion TEXT, 
	fuente_id BIGINT NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (codigo), 
	FOREIGN KEY(fuente_id) REFERENCES fuente (id)
)

;

CREATE TABLE IF NOT EXISTS version_fuente (
	id BIGSERIAL NOT NULL, 
	fuente_id BIGINT NOT NULL, 
	fecha_actualizacion_fuente DATE NOT NULL, 
	fecha_descarga TIMESTAMP WITH TIME ZONE NOT NULL, 
	nombre_archivo VARCHAR(255) NOT NULL, 
	ruta_local TEXT, 
	hash_sha256 VARCHAR(64) NOT NULL, 
	tamano_bytes BIGINT NOT NULL, 
	filas_originales INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_version_tamanos CHECK (tamano_bytes >= 0 AND filas_originales >= 0), 
	FOREIGN KEY(fuente_id) REFERENCES fuente (id), 
	UNIQUE (hash_sha256)
)

;

CREATE TABLE IF NOT EXISTS ejecucion_version (
	ejecucion_id BIGINT NOT NULL, 
	version_fuente_id BIGINT NOT NULL, 
	filas_leidas INTEGER NOT NULL, 
	filas_cargadas INTEGER NOT NULL, 
	PRIMARY KEY (ejecucion_id, version_fuente_id), 
	CONSTRAINT ck_ev_contadores CHECK (filas_leidas >= 0 AND filas_cargadas >= 0), 
	FOREIGN KEY(ejecucion_id) REFERENCES ejecucion (id), 
	FOREIGN KEY(version_fuente_id) REFERENCES version_fuente (id)
)

;

CREATE TABLE IF NOT EXISTS error_ejecucion (
	id BIGSERIAL NOT NULL, 
	ejecucion_id BIGINT NOT NULL, 
	version_fuente_id BIGINT, 
	regla_id BIGINT, 
	fila_origen INTEGER, 
	columna VARCHAR(255), 
	valor_original TEXT, 
	tipo_error VARCHAR(128) NOT NULL, 
	mensaje TEXT NOT NULL, 
	registrado_en TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(ejecucion_id) REFERENCES ejecucion (id), 
	FOREIGN KEY(version_fuente_id) REFERENCES version_fuente (id), 
	FOREIGN KEY(regla_id) REFERENCES regla (id)
)

;

CREATE TABLE IF NOT EXISTS metrica_calidad (
	id BIGSERIAL NOT NULL, 
	ejecucion_id BIGINT NOT NULL, 
	version_fuente_id BIGINT NOT NULL, 
	metrica VARCHAR(128) NOT NULL, 
	valor NUMERIC NOT NULL, 
	unidad VARCHAR(64) NOT NULL, 
	registrado_en TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_metrica_ejecucion_version UNIQUE (ejecucion_id, version_fuente_id, metrica), 
	FOREIGN KEY(ejecucion_id) REFERENCES ejecucion (id), 
	FOREIGN KEY(version_fuente_id) REFERENCES version_fuente (id)
)

;

CREATE TABLE IF NOT EXISTS observacion (
	id BIGSERIAL NOT NULL, 
	indicador_id BIGINT NOT NULL, 
	territorio_id BIGINT NOT NULL, 
	anio SMALLINT NOT NULL, 
	valor NUMERIC NOT NULL, 
	version_fuente_id BIGINT NOT NULL, 
	ejecucion_id BIGINT NOT NULL, 
	creado_en TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_observacion_version UNIQUE (indicador_id, territorio_id, anio, version_fuente_id), 
	CONSTRAINT ck_observacion_anio CHECK (anio BETWEEN 1900 AND 2100), 
	FOREIGN KEY(indicador_id) REFERENCES indicador (id), 
	FOREIGN KEY(territorio_id) REFERENCES territorio (id), 
	FOREIGN KEY(version_fuente_id) REFERENCES version_fuente (id), 
	FOREIGN KEY(ejecucion_id) REFERENCES ejecucion (id)
)

;