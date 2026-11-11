import json
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from GestorPersistencia import GestorPersistencia
from PipelineETL import PipelineETL


def _json_value(valor: Any) -> Any:
    if isinstance(valor, str):
        try:
            return json.loads(valor)
        except json.JSONDecodeError:
            return valor
    return valor


def _columnas_numericas(df: pd.DataFrame, columnas: list[str]) -> list[str]:
    return [
        columna
        for columna in columnas
        if pd.to_numeric(df[columna], errors="coerce").notna().any()
    ]


def _columnas_fecha(df: pd.DataFrame, columnas: list[str]) -> list[str]:
    candidatas = [
        columna
        for columna in columnas
        if any(termino in columna.lower() for termino in ("fecha", "date", "time"))
    ]
    return [
        columna
        for columna in candidatas
        if pd.to_datetime(df[columna], errors="coerce").notna().any()
    ]


def _columna_disponible(base: str, columnas: list[str]) -> str:
    nombre = base
    sufijo = 2
    while nombre in columnas:
        nombre = f"{base}_{sufijo}"
        sufijo += 1
    return nombre


def _leer_reglas() -> dict[str, Any]:
    renombres = json.loads(st.session_state.get("reglas_renombres", "{}") or "{}")
    tipos = json.loads(st.session_state.get("reglas_tipos", "{}") or "{}")
    if not isinstance(renombres, dict) or not isinstance(tipos, dict):
        raise ValueError("Los renombrados y tipos deben estar escritos como objetos JSON.")
    requeridas = [
        columna.strip()
        for columna in st.session_state.get("reglas_requeridas", "").split(",")
        if columna.strip()
    ]
    perfil = st.session_state.get("perfil_reglas", "Estándar: normalizar y quitar duplicados")
    if perfil == "Completo: quitar nulos y duplicados":
        eliminar_nulos, eliminar_duplicados = True, True
    elif perfil == "Conservar todas las filas":
        eliminar_nulos, eliminar_duplicados = False, False
    elif perfil == "Personalizado":
        eliminar_nulos = st.session_state.get("reglas_eliminar_nulos", False)
        eliminar_duplicados = st.session_state.get("reglas_eliminar_duplicados", True)
    else:
        eliminar_nulos, eliminar_duplicados = False, True
    return {
        "renombrar_columnas": renombres,
        "tipos": tipos,
        "columnas_requeridas": requeridas,
        "eliminar_nulos": eliminar_nulos,
        "eliminar_duplicados": eliminar_duplicados,
    }


def _validar_metadatos(metadatos: dict[str, Any]) -> list[str]:
    etiquetas = {
        "nombre": "nombre de la fuente",
        "procedencia": "procedencia o URL",
        "licencia": "licencia",
        "fecha_disponible": "fecha disponible",
        "version": "versión",
    }
    return [
        etiqueta
        for campo, etiqueta in etiquetas.items()
        if not str(metadatos.get(campo, "")).strip()
    ]


def _fecha_texto(valor: Any) -> str:
    if isinstance(valor, datetime):
        return valor.date().isoformat()
    return str(valor or "")


@st.cache_resource
def _obtener_persistencia() -> GestorPersistencia:
    return GestorPersistencia()


st.set_page_config(
    page_title="Observatorio | Datos abiertos",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root {
        --verde-900: #123d32;
        --verde-700: #17624d;
        --verde-100: #e7f2ec;
        --oro: #e9b949;
        --tinta: #1d2b26;
        --muted: #64746d;
    }
    .stApp { background: #f4f7f5; color: var(--tinta); }
    [data-testid="stHeader"] { background: rgba(244,247,245,.94); }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #edf3ef 0%, #f7f9f7 100%);
        border-right: 1px solid #dfe9e3;
        color: #1d2b26;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] li,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h4,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        color: #344a40 !important;
    }
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        color: #60736a !important;
    }
    button[role="tab"] {
        color: #52665c;
        font-weight: 600;
    }
    button[role="tab"][aria-selected="true"] {
        color: #17624d;
    }
    [data-testid="stFileUploader"] {
        background: #fff;
        border: 1px dashed #a9c5b5;
        border-radius: 12px;
        padding: 8px;
    }
    [data-testid="stMetric"] {
        background: #fff;
        border: 1px solid #e1e9e4;
        border-radius: 14px;
        padding: 18px 20px;
        box-shadow: 0 5px 16px rgba(18,61,50,.045);
    }
    [data-testid="stMetricLabel"] { color: var(--muted); }
    .portal-marca {
        display:flex; align-items:center; gap:13px;
        padding:4px 0 18px; border-bottom:1px solid #dce7e0;
        margin-bottom:18px;
    }
    .portal-sello {
        width:48px; height:48px; display:grid; place-items:center;
        background:var(--verde-900); color:#fff; border-radius:15px;
        font-size:23px; box-shadow:0 6px 14px rgba(18,61,50,.16);
    }
    .portal-eyebrow {
        color:var(--verde-700); font-size:10px; font-weight:800;
        letter-spacing:.14em; text-transform:uppercase;
    }
    .portal-nombre { color:var(--tinta); font-size:17px; font-weight:800; }
    .portal-hero {
        position:relative; overflow:hidden;
        background:linear-gradient(112deg,#123d32 0%,#17624d 65%,#258060 100%);
        border-radius:20px; color:white; padding:32px 36px; margin:4px 0 24px;
        box-shadow:0 12px 30px rgba(18,61,50,.14);
    }
    .portal-hero:after {
        content:""; position:absolute; width:240px; height:240px; right:6%;
        top:-120px; border:1px solid rgba(255,255,255,.16); border-radius:50%;
        box-shadow:0 0 0 30px rgba(255,255,255,.035),0 0 0 60px rgba(255,255,255,.025);
    }
    .portal-kicker {
        color:#c6e1d3; font-size:11px; font-weight:800;
        letter-spacing:.16em; text-transform:uppercase;
    }
    .portal-hero h1 {
        color:#fff; font-size:clamp(28px,3.3vw,42px); margin:10px 0;
        line-height:1.12; max-width:750px;
    }
    .portal-hero p { color:#e1eee7; max-width:760px; margin:0; font-size:15px; }
    .portal-hero .hero-sello { color:var(--oro); }
    .portal-footer {
        color:#73827b; font-size:12px; border-top:1px solid #e0e8e3;
        padding:14px 0 4px; margin-top:26px;
    }
    div.stButton > button[kind="primary"] {
        background:var(--verde-700); border-color:var(--verde-700);
        border-radius:9px; font-weight:700;
    }
    div.stButton > button[kind="primary"]:hover {
        background:var(--verde-900); border-color:var(--verde-900);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown(
        """
        <div class="portal-marca">
            <div class="portal-sello">⌂</div>
            <div><div class="portal-eyebrow">Portal institucional</div>
            <div class="portal-nombre">Datos abiertos</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("#### Centro de información")
    st.caption("Transparencia, análisis y reutilización de datos públicos.")
    st.markdown("---")
    st.caption("**Flujo de trabajo**")
    st.markdown(
        "1. Registra o selecciona dos fuentes.\n"
        "2. Revisa metadatos y reglas.\n"
        "3. Comprueba compatibilidad.\n"
        "4. Integra y consulta resultados."
    )
    st.markdown("---")
    st.caption("Servicio local · Procesamiento reproducible")

st.markdown(
    """
    <div class="portal-hero">
        <div class="portal-kicker"><span class="hero-sello">✦</span> Transparencia · Territorio · Comunidad</div>
        <h1>Observatorio de datos abiertos</h1>
        <p>Datos públicos que cuentan historias. Explora indicadores, compara fuentes
        y encuentra evidencia para comprender mejor el territorio.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    persistencia = _obtener_persistencia()
    catalogo = persistencia.obtener_fuentes()
    ejecuciones = persistencia.obtener_ejecuciones()
    registros = persistencia.obtener_registros(limite=10000)
except SQLAlchemyError as error:
    st.error(f"No se pudo consultar la base de datos: {error}")
    st.info("Configura `DATABASE_URL` para PostgreSQL o utiliza la base SQLite local.")
    st.stop()

df_ejecuciones = pd.DataFrame(ejecuciones)
df_registros = pd.DataFrame(registros)
columna_fuente: str | None = None
if not df_registros.empty:
    datos_normalizados = pd.json_normalize(df_registros["datos"].map(_json_value))
    datos_normalizados.columns = [str(columna) for columna in datos_normalizados.columns]
    columna_fuente = _columna_disponible(
        "__opendata_fuente_origen__",
        list(datos_normalizados.columns),
    )
    df_registros = datos_normalizados.reset_index(drop=True)
    df_registros.insert(
        0,
        columna_fuente,
        pd.Series(registros).map(lambda registro: registro["origen"]).reset_index(drop=True),
    )

if "fuentes_guardadas" in st.session_state:
    st.session_state.pop("fuentes_guardadas")
    st.success("Las fuentes quedaron registradas en el catálogo.")
if "ultima_integracion" in st.session_state:
    resultado_integracion = st.session_state.pop("ultima_integracion")
    st.success(
        "Integración completada: "
        f"{resultado_integracion['filas_insertadas']:,} registros nuevos, "
        f"{resultado_integracion['duplicados_omitidos']:,} duplicados omitidos."
    )

tab_flujo, tab_catalogo, tab_datos, tab_analisis, tab_monitoreo, tab_api = st.tabs(
    [
        "⬆️ Integrar fuentes",
        "📚 Catálogo",
        "🗂️ Datos",
        "📊 Analítica",
        "🛰️ Monitoreo",
        "🔌 API",
    ]
)

with tab_flujo:
    st.subheader("Integrar dos fuentes públicas")
    st.caption(
        "Selecciona un CSV para cada fuente. El sistema compara los esquemas "
        "normalizados y no permite integrar archivos incompatibles."
    )
    nombres_catalogo = [fuente["nombre"] for fuente in catalogo]
    catalogo_por_nombre = {fuente["nombre"]: fuente for fuente in catalogo}
    opcion_nueva = "＋ Registrar una fuente nueva"
    fuentes_seleccionadas: list[dict[str, Any]] = []
    columnas_fuentes = st.columns(2, gap="large")

    for indice, contenedor in enumerate(columnas_fuentes):
        sufijo = "a" if indice == 0 else "b"
        titulo = "Fuente 01" if indice == 0 else "Fuente 02"
        with contenedor:
            st.markdown(f"#### {titulo}")
            seleccion = st.selectbox(
                "Fuente del catálogo",
                [opcion_nueva, *nombres_catalogo],
                key=f"fuente_catalogo_{sufijo}",
            )
            archivo = st.file_uploader(
                "Archivo de datos (.csv)",
                type=["csv"],
                key=f"archivo_fuente_{sufijo}",
            )
            if seleccion == opcion_nueva:
                nombre = st.text_input("Nombre público de la fuente", key=f"nombre_fuente_{sufijo}")
                procedencia = st.text_input(
                    "Institución o URL de procedencia", key=f"procedencia_{sufijo}"
                )
                licencia = st.text_input(
                    "Licencia de uso", key=f"licencia_{sufijo}", placeholder="CC BY 4.0, uso público…"
                )
                fecha_disponible = st.text_input(
                    "Fecha de publicación o actualización", key=f"fecha_{sufijo}"
                )
                version = st.text_input(
                    "Versión del conjunto", key=f"version_{sufijo}", placeholder="2026, v1…"
                )
                metadatos_fuente = {
                    "nombre": nombre.strip(),
                    "procedencia": procedencia.strip(),
                    "licencia": licencia.strip(),
                    "fecha_disponible": fecha_disponible.strip(),
                    "version": version.strip(),
                }
            else:
                metadatos_guardados = catalogo_por_nombre[seleccion]
                metadatos_fuente = {
                    "nombre": metadatos_guardados["nombre"],
                    "procedencia": metadatos_guardados["procedencia"],
                    "licencia": metadatos_guardados["licencia"],
                    "fecha_disponible": _fecha_texto(metadatos_guardados["fecha_disponible"]),
                    "version": metadatos_guardados["version"],
                }
                st.info(
                    f"**Procedencia:** {metadatos_fuente['procedencia']}\n\n"
                    f"**Licencia:** {metadatos_fuente['licencia']} · "
                    f"**Versión:** {metadatos_fuente['version']}"
                )

            if archivo is not None:
                st.caption(f"Seleccionado: **{archivo.name}** · {archivo.size / 1024:,.1f} KB")
            fuentes_seleccionadas.append(
                {
                    "archivo": archivo,
                    "metadatos": metadatos_fuente,
                    "nombre_archivo": archivo.name if archivo else "",
                }
            )

    st.markdown("---")
    st.markdown("#### Reglas de transformación y validación")
    with st.expander("Configura cómo se armonizan los datos", expanded=False):
        st.caption(
            "Los nombres se normalizan automáticamente. Usa los campos siguientes "
            "para alinear nombres o convertir tipos antes de comparar."
        )
        st.selectbox(
            "Perfil de reglas preconfigurado",
            [
                "Estándar: normalizar y quitar duplicados",
                "Completo: quitar nulos y duplicados",
                "Conservar todas las filas",
                "Personalizado",
            ],
            key="perfil_reglas",
            help="Selecciona una política habitual o usa Personalizado para controlar las reglas manualmente.",
        )
        col_regla_a, col_regla_b = st.columns(2)
        with col_regla_a:
            st.text_area(
                "Renombrar columnas (JSON)",
                value="{}",
                key="reglas_renombres",
                help='Ejemplo: {"codigo_postal": "codigo"}',
            )
            st.text_input(
                "Columnas requeridas (separadas por coma)",
                key="reglas_requeridas",
                placeholder="provincia, anio",
            )
        with col_regla_b:
            st.text_area(
                "Convertir tipos (JSON)",
                value="{}",
                key="reglas_tipos",
                help='Ejemplo: {"poblacion": "int", "indice": "float", "fecha": "date"}',
            )
            st.checkbox(
                "Eliminar filas con valores vacíos (personalizado)",
                key="reglas_eliminar_nulos",
            )
            st.checkbox(
                "Eliminar filas duplicadas (personalizado)",
                value=True,
                key="reglas_eliminar_duplicados",
            )

    reglas: dict[str, Any] | None = None
    error_reglas: str | None = None
    try:
        reglas = _leer_reglas()
    except (json.JSONDecodeError, ValueError) as error:
        error_reglas = str(error)
        st.error(f"Revisa la configuración de reglas: {error}")

    metadatos_incompletos = [
        (indice + 1, _validar_metadatos(fuente["metadatos"]))
        for indice, fuente in enumerate(fuentes_seleccionadas)
    ]
    errores_metadatos = [
        f"Fuente {indice}: faltan " + ", ".join(campos)
        for indice, campos in metadatos_incompletos
        if campos
    ]
    if errores_metadatos:
        st.warning("Completa la procedencia, licencia, fecha y versión de ambas fuentes.")

    comparacion: dict[str, Any] | None = None
    error_comparacion: str | None = None
    if all(fuente["archivo"] for fuente in fuentes_seleccionadas) and reglas is not None:
        motor_revision = PipelineETL(
            reglas_transformacion=reglas,
            conexion_db=persistencia.db,
        )
        try:
            comparacion = motor_revision.comparar_fuentes_csv(
                fuentes_seleccionadas[0]["archivo"].getvalue(),
                fuentes_seleccionadas[0]["nombre_archivo"],
                fuentes_seleccionadas[1]["archivo"].getvalue(),
                fuentes_seleccionadas[1]["nombre_archivo"],
            )
        except (ValueError, TypeError, UnicodeError) as error:
            error_comparacion = str(error)
        finally:
            motor_revision.persistencia.engine.dispose()

    if comparacion and comparacion["compatible"]:
        st.success(
            "Esquemas compatibles. "
            f"{len(comparacion['columnas_comunes'])} columnas armonizadas: "
            + ", ".join(comparacion["columnas_comunes"])
        )
    elif comparacion:
        st.error("Las fuentes no son compatibles todavía. Revisa los nombres y las reglas.")
        if comparacion["solo_fuente_a"]:
            st.write("Solo en Fuente 01:", ", ".join(comparacion["solo_fuente_a"]))
        if comparacion["solo_fuente_b"]:
            st.write("Solo en Fuente 02:", ", ".join(comparacion["solo_fuente_b"]))
    elif error_comparacion:
        st.error(f"No se pudo comparar el contenido: {error_comparacion}")
    else:
        st.info("Selecciona dos archivos y completa sus metadatos para verificar compatibilidad.")

    botones_flujo = st.columns([1, 1, 2])
    puede_guardar = not errores_metadatos and reglas is not None
    if botones_flujo[0].button(
        "Guardar en catálogo",
        disabled=not puede_guardar,
        use_container_width=True,
    ):
        for fuente in fuentes_seleccionadas:
            persistencia.registrar_fuente(
                {
                    **fuente["metadatos"],
                    "formato": "CSV",
                    "fecha_registro": datetime.now(timezone.utc),
                    "columnas": [],
                    "filas_disponibles": 0,
                }
            )
        st.session_state["fuentes_guardadas"] = True
        st.rerun()

    puede_integrar = (
        not errores_metadatos
        and reglas is not None
        and comparacion is not None
        and comparacion["compatible"]
    )
    if botones_flujo[1].button(
        "Integrar las dos fuentes",
        type="primary",
        disabled=not puede_integrar,
        use_container_width=True,
    ):
        motor_etl = PipelineETL(
            reglas_transformacion=reglas,
            conexion_db=persistencia.db,
        )
        try:
            with st.spinner("Validando y procesando ambas fuentes…"):
                resultado = motor_etl.ejecutar_dos_fuentes_csv(
                    [
                        {
                            "contenido": fuente["archivo"].getvalue(),
                            "archivo": fuente["nombre_archivo"],
                            "nombre": fuente["metadatos"]["nombre"],
                            "metadatos": fuente["metadatos"],
                        }
                        for fuente in fuentes_seleccionadas
                    ]
                )
            st.session_state["ultima_integracion"] = resultado
            st.rerun()
        except Exception as error:
            st.error(f"La integración falló y quedó registrada en el monitoreo: {error}")
        finally:
            motor_etl.persistencia.engine.dispose()

with tab_catalogo:
    st.subheader("Catálogo de fuentes públicas")
    st.caption("Consulta procedencia, licencia, formato, actualización y esquema conocido.")
    if catalogo:
        catalogo_df = pd.DataFrame(catalogo)
        columnas_catalogo = [
            "nombre",
            "procedencia",
            "licencia",
            "formato",
            "fecha_disponible",
            "version",
            "columnas",
            "filas_disponibles",
        ]
        columnas_catalogo = [col for col in columnas_catalogo if col in catalogo_df]
        st.dataframe(
            catalogo_df[columnas_catalogo],
            width="stretch",
            hide_index=True,
        )
        nombres_disponibles = [fuente["nombre"] for fuente in catalogo]
        fuente_detalle = st.selectbox(
            "Revisar ficha de fuente",
            nombres_disponibles,
            key="detalle_catalogo",
        )
        ficha = next(fuente for fuente in catalogo if fuente["nombre"] == fuente_detalle)
        with st.container(border=True):
            detalle_a, detalle_b = st.columns(2)
            detalle_a.markdown(f"**Procedencia**  \n{ficha['procedencia']}")
            detalle_a.markdown(f"**Licencia**  \n{ficha['licencia']}")
            detalle_b.markdown(f"**Formato / versión**  \n{ficha['formato']} · {ficha['version']}")
            detalle_b.markdown(
                f"**Disponibilidad**  \n{ficha['fecha_disponible']} · "
                f"{ficha['filas_disponibles']:,} filas registradas"
            )
    else:
        st.info("El catálogo está vacío. Registra tus primeras fuentes desde «Integrar fuentes».")

with tab_datos:
    st.subheader("Datos integrados")
    if df_registros.empty:
        st.info("Todavía no hay registros almacenados.")
    else:
        assert columna_fuente is not None
        fuentes_registros = sorted(df_registros[columna_fuente].dropna().unique().tolist())
        filtro_fuente = st.selectbox("Fuente", ["Todas", *fuentes_registros], key="filtro_fuente")
        df_visibles = df_registros
        if filtro_fuente != "Todas":
            df_visibles = df_registros[df_registros[columna_fuente] == filtro_fuente]
        columnas_datos = [
            columna for columna in df_visibles.columns if columna != columna_fuente
        ]
        consulta = st.text_input("Buscar en los registros", placeholder="Escribe un valor para filtrar…")
        if consulta:
            coincide = df_visibles[columnas_datos].astype(str).apply(
                lambda columna: columna.str.contains(consulta, case=False, na=False)
            ).any(axis=1)
            df_visibles = df_visibles[coincide]
        columnas_mostrar = st.multiselect(
            "Campos visibles",
            columnas_datos,
            default=columnas_datos,
        )
        etiqueta_fuente = _columna_disponible("Fuente de procedencia", columnas_mostrar)
        tabla = df_visibles[[columna_fuente, *columnas_mostrar]].rename(
            columns={columna_fuente: etiqueta_fuente}
        )
        st.dataframe(tabla, width="stretch", hide_index=True)
        st.download_button(
            "Descargar resultado como CSV",
            data=tabla.to_csv(index=False).encode("utf-8-sig"),
            file_name="datos_abiertos.csv",
            mime="text/csv",
        )
        st.caption(f"{len(df_visibles):,} filas en el resultado · máximo 10 000 registros recientes.")

with tab_analisis:
    st.subheader("Explora los indicadores")
    if df_registros.empty:
        st.info("Importa fuentes compatibles para habilitar las visualizaciones.")
    else:
        assert columna_fuente is not None
        columnas_datos = [
            columna for columna in df_registros.columns if columna != columna_fuente
        ]
        numericas = _columnas_numericas(df_registros, columnas_datos)
        categoricas = [
            columna for columna in columnas_datos
            if 1 < df_registros[columna].nunique(dropna=True) <= 100
        ]
        fechas = _columnas_fecha(df_registros, columnas_datos)
        tipo_grafica = st.radio(
            "Vista",
            ["Indicador", "Distribución", "Comparar categorías", "Evolución temporal"],
            horizontal=True,
            key="tipo_analisis",
        )
        if tipo_grafica == "Indicador" and numericas:
            columna = st.selectbox("Indicador", numericas, key="indicador_principal")
            valores = pd.to_numeric(df_registros[columna], errors="coerce").dropna()
            met_a, met_b, met_c = st.columns(3)
            met_a.metric("Promedio", f"{valores.mean():,.2f}")
            met_b.metric("Máximo registrado", f"{valores.max():,.2f}")
            met_c.metric("Observaciones válidas", f"{len(valores):,}")
            st.bar_chart(valores.reset_index(drop=True), color="#17624d")
        elif tipo_grafica == "Distribución" and numericas:
            columna = st.selectbox("Campo numérico", numericas, key="campo_distribucion")
            valores = pd.to_numeric(df_registros[columna], errors="coerce").dropna()
            if not valores.empty:
                bins = min(20, max(1, valores.nunique()))
                frecuencias = pd.cut(valores, bins=bins, duplicates="drop").value_counts().sort_index()
                frecuencias.index = frecuencias.index.astype(str)
                st.bar_chart(frecuencias, color="#17624d")
        elif tipo_grafica == "Comparar categorías" and categoricas:
            columna = st.selectbox("Agrupar por", categoricas, key="campo_categoria")
            resumen = (
                df_registros[columna].fillna("(sin dato)").astype(str)
                .value_counts().head(20)
            )
            st.bar_chart(resumen, color="#d39a2c")
            st.caption("Se muestran hasta 20 categorías por número de registros.")
        elif tipo_grafica == "Evolución temporal" and fechas and numericas:
            col_fecha, col_valor = st.columns(2)
            fecha = col_fecha.selectbox("Fecha", fechas, key="campo_fecha")
            valor = col_valor.selectbox("Indicador", numericas, key="campo_temporal")
            serie = pd.DataFrame(
                {
                    "fecha": pd.to_datetime(df_registros[fecha], errors="coerce"),
                    "valor": pd.to_numeric(df_registros[valor], errors="coerce"),
                }
            ).dropna()
            if not serie.empty:
                mensual = serie.set_index("fecha")["valor"].resample("ME").mean().dropna()
                st.line_chart(mensual, color="#17624d")
        else:
            st.info("No hay suficientes columnas compatibles para construir esta visualización.")

with tab_monitoreo:
    st.subheader("Trazabilidad del procesamiento")
    if df_ejecuciones.empty:
        st.info("Las ejecuciones ETL aparecerán aquí con su estado y métricas de calidad.")
    else:
        ultima = ejecuciones[0]
        estado = str(ultima.get("estado", "desconocido")).upper()
        col_estado, col_filas, col_duracion, col_fuentes = st.columns(4)
        col_estado.metric("Último estado", estado)
        col_filas.metric("Filas procesadas", f"{ultima.get('filas_procesadas', 0):,}")
        col_duracion.metric("Duración", f"{ultima.get('duracion_segundos', 0):.2f} s")
        col_fuentes.metric("Fuentes", str(ultima.get("origen") or "—"))

        indicadores = ultima.get("indicadores_calidad") or {}
        if isinstance(indicadores, str):
            indicadores = _json_value(indicadores)
        if indicadores:
            st.markdown("#### Indicadores de calidad")
            st.json(indicadores, expanded=True)
        errores = ultima.get("errores") or []
        if isinstance(errores, str):
            errores = _json_value(errores)
        if errores:
            st.error("La ejecución más reciente registró errores.")
            for error in errores:
                st.write(f"- {error}")
        else:
            st.success("La última ejecución finalizó sin errores.")

        historial = df_ejecuciones.copy()
        for columna in ("indicadores_calidad", "errores"):
            if columna in historial:
                historial[columna] = historial[columna].map(
                    lambda valor: json.dumps(_json_value(valor), ensure_ascii=False, default=str)
                )
        columnas_historial = [
            columna for columna in (
                "id", "inicio", "estado", "origen", "duracion_segundos",
                "filas_procesadas", "indicadores_calidad", "errores",
            ) if columna in historial
        ]
        st.markdown("#### Historial de ejecuciones")
        st.dataframe(historial[columnas_historial], width="stretch", hide_index=True)

with tab_api:
    st.subheader("API REST de consulta")
    st.caption("Accede a las fuentes, registros y ejecuciones desde otras herramientas.")
    st.code(
        "GET http://127.0.0.1:8000/api/v1/fuentes\n"
        "GET http://127.0.0.1:8000/api/v1/registros?limite=1000\n"
        "GET http://127.0.0.1:8000/api/v1/registros?origen=FUENTE&limite=1000\n"
        "GET http://127.0.0.1:8000/api/v1/ejecuciones?limite=100\n"
        "GET http://127.0.0.1:8000/health",
        language="http",
    )
    st.link_button("Abrir documentación interactiva Swagger", "http://127.0.0.1:8000/docs")
    st.info(
        "Inicia la API en otra terminal con: "
        "`.venv\\Scripts\\python.exe -m uvicorn api:app --reload --port 8000`"
    )
    st.caption("La API y el tablero utilizan la misma variable `DATABASE_URL`.")

st.markdown(
    '<div class="portal-footer">Observatorio de datos abiertos · Información pública para una gestión basada en evidencia</div>',
    unsafe_allow_html=True,
)
