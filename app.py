import json
import pandas as pd
import streamlit as st
from sqlalchemy.exc import SQLAlchemyError
from GestorPersistencia import GestorPersistencia
from PipelineETL import PipelineETL


@st.cache_resource
def _obtener_persistencia_relacional_v2() -> GestorPersistencia:
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

import modelo as m
from pathlib import Path

try:
    persistencia = _obtener_persistencia_relacional_v2()
    catalogo = persistencia.obtener_fuentes()
except SQLAlchemyError:
    st.error("No se pudo conectar a la base. Inicia el proyecto con local.py web.")
    st.stop()

st.caption("Modelo relacional · fuentes, versiones, indicadores y territorios DPA")
if "resultado_relacional" in st.session_state:
    resultado = st.session_state.pop("resultado_relacional")
    st.success(f"Carga completa: {resultado['filas_insertadas']} observaciones nuevas; "
               f"{resultado['duplicados_omitidos']} duplicados omitidos. Ejecución {resultado['ejecucion_id']}.")

carga, catalogos, datos, cruce, monitoreo, api_tab = st.tabs(
    ["⬆️ Integrar fuentes", "📚 Catálogo", "🗂️ Datos", "📊 Cruce territorial", "🛰️ Monitoreo", "🔌 API"])
with carga:
    st.subheader("Integrar dos indicadores por territorio y año")
    st.info("CSV agregado: codigo_dpa, territorio, provincia, anio, valor. "
            "CSV de registros: reemplaza valor por ruc (se cuentan RUC distintos por DPA/año). "
            "Para parroquias incluye canton; para provincias no se exige provincia. "
            "Mantén DPA y RUC como texto, con sus ceros iniciales.")
    st.caption("Los nombres territoriales provienen de tus archivos; no se valida contra un catálogo oficial externo.")
    with st.expander("Descargar ejemplos sintéticos para probar"):
        for name in ("poblacion_demo.csv", "ruc_demo.csv"):
            path = Path(__file__).parent / "ejemplos" / name
            st.download_button(name, path.read_bytes(), file_name=name, mime="text/csv")
        st.write("Metadatos sugeridos: Demo INEC / demo_poblacion / personas; "
                 "Demo SRI / demo_ruc / contribuyentes. Fecha: 2026-11-26. Son datos ficticios.")
    fuentes, errores = [], []
    opciones = {f["nombre"]: f for f in catalogo}
    for idx, column in enumerate(st.columns(2)):
        with column:
            st.markdown(f"#### Fuente {idx + 1}")
            seleccion = st.selectbox("Fuente", ["Nueva fuente", *opciones], key=f"fuente_{idx}")
            existente = opciones.get(seleccion, {})
            nombre = st.text_input("Nombre", value=existente.get("nombre", ""), key=f"nombre_{idx}_{seleccion}")
            publicador = st.text_input("Publicador", value=existente.get("publicador", ""), key=f"publicador_{idx}_{seleccion}")
            url = st.text_input("URL o procedencia", value=existente.get("url_descarga", ""), key=f"url_{idx}_{seleccion}")
            licencia = st.text_input("Licencia", value=existente.get("licencia", ""), key=f"licencia_{idx}_{seleccion}")
            fecha = st.date_input("Fecha de actualización de la fuente", key=f"fecha_{idx}")
            estructura = st.selectbox("Estructura", ["agregada", "registro"],
                index=1 if existente.get("estructura") == "registro" else 0, key=f"estructura_{idx}_{seleccion}")
            codigo = st.text_input("Código único del indicador", key=f"indicador_{idx}",
                help="Ejemplo: inec_poblacion o sri_contribuyentes. No reutilices un código de otra fuente.")
            indicador_nombre = st.text_input("Nombre del indicador", key=f"indicador_nombre_{idx}")
            unidad = st.text_input("Unidad", key=f"unidad_{idx}",
                help="En estructura registro, el valor es el número de RUC distintos, no establecimientos.")
            archivo = st.file_uploader("Archivo CSV", type=["csv"], key=f"archivo_fuente_{idx}")
            renombres = st.text_area("Renombrar columnas (JSON)", value="{}", key=f"renombres_{idx}",
                help='Ejemplo: {"dpa_canton": "codigo_dpa", "poblacion": "valor", "nombre_canton": "territorio"}')
            try:
                mapa = json.loads(renombres)
                if not isinstance(mapa, dict):
                    raise ValueError("El mapa debe ser un objeto JSON")
            except (ValueError, json.JSONDecodeError):
                errores.append(f"Fuente {idx + 1}: revisa el mapa de columnas")
                mapa = {}
            meta = dict(nombre=nombre, publicador=publicador, url_descarga=url, licencia=licencia,
                fecha_actualizacion=fecha.isoformat(), estructura=estructura,
                indicador_codigo=codigo, indicador_nombre=indicador_nombre, unidad=unidad)
            if archivo is not None:
                fuentes.append(dict(nombre=nombre, archivo=archivo.name, contenido=archivo.getvalue(),
                                    metadatos=meta, reglas={"renombrar_columnas": mapa}))
    for error in errores:
        st.error(error)
    if st.button("Validar compatibilidad", disabled=len(fuentes) != 2 or bool(errores)):
        motor = PipelineETL(conexion_db=persistencia.db)
        try:
            resultado = motor.previsualizar(fuentes)
            st.success(f"Compatibles: {resultado['coincidencias_dpa_anio']} coincidencias por DPA y año.")
            st.json(resultado)
        except (ValueError, KeyError, TypeError) as exc:
            st.error(str(exc))
        finally:
            motor.persistencia.engine.dispose()
    if st.button("Integrar las dos fuentes", type="primary", disabled=len(fuentes) != 2 or bool(errores)):
        motor = PipelineETL(conexion_db=persistencia.db)
        try:
            with st.spinner("Validando y guardando ambas fuentes…"):
                st.session_state["resultado_relacional"] = motor.ejecutar_dos_fuentes_csv(fuentes)
            st.rerun()
        except (ValueError, KeyError, TypeError, SQLAlchemyError) as exc:
            st.error(f"No se cargaron datos parciales. Consulta Monitoreo. Detalle: {exc}")
        finally:
            motor.persistencia.engine.dispose()

with catalogos:
    st.subheader("Fuentes")
    st.dataframe(pd.DataFrame(catalogo), width="stretch")
    st.subheader("Versiones de archivos")
    st.dataframe(pd.DataFrame(persistencia.listar(m.version_fuente)), width="stretch")
    st.subheader("Indicadores")
    st.dataframe(pd.DataFrame(persistencia.listar(m.indicador)), width="stretch")
    st.subheader("Territorios y jerarquía")
    st.dataframe(pd.DataFrame(persistencia.listar(m.territorio)), width="stretch")

with datos:
    st.subheader("Observaciones")
    filtro_fuente = st.selectbox("Filtrar fuente", ["Todas", *opciones], key="datos_fuente")
    filtro_dpa = st.text_input("Código DPA (opcional)", key="datos_dpa")
    observaciones = persistencia.obtener_observaciones(
        origen=None if filtro_fuente == "Todas" else filtro_fuente, codigo_dpa=filtro_dpa or None)
    df = pd.DataFrame(observaciones)
    st.caption("Se muestran hasta 10 000 observaciones, incluidas versiones históricas.")
    st.dataframe(df, width="stretch")
    st.download_button("Descargar observaciones CSV", df.to_csv(index=False).encode("utf-8-sig"),
                       file_name="observaciones.csv", mime="text/csv")

with cruce:
    st.subheader("Cruzar indicadores por DPA y año")
    st.caption("Usa la última versión disponible por indicador, territorio y año, según fecha de publicación. "
               "Solo muestra territorios presentes en ambos indicadores.")
    codigos = [i["codigo"] for i in persistencia.listar(m.indicador)]
    if len(codigos) >= 2:
        a = st.selectbox("Indicador A", codigos, key="cruce_a")
        b = st.selectbox("Indicador B", codigos, index=1, key="cruce_b")
        anio = st.number_input("Año", min_value=1900, max_value=2100, value=2026, step=1)
        if a == b:
            st.warning("Selecciona indicadores diferentes")
        else:
            cruzados = pd.DataFrame(persistencia.cruzar_indicadores(a, b, int(anio)))
            st.dataframe(cruzados, width="stretch")
            if not cruzados.empty:
                grafica = cruzados.set_index("codigo_dpa")[["valor_a", "valor_b"]].astype(float)
                st.bar_chart(grafica)
                st.caption(f"valor_a = {a}; valor_b = {b}. Revisa las unidades antes de comparar magnitudes.")
    else:
        st.info("Carga dos indicadores para habilitar el cruce.")

with monitoreo:
    st.subheader("Ejecuciones")
    st.dataframe(pd.DataFrame(persistencia.obtener_ejecuciones()), width="stretch")
    st.subheader("Errores")
    st.dataframe(pd.DataFrame(persistencia.listar(m.error_ejecucion)), width="stretch")
    st.subheader("Métricas por ejecución y versión")
    st.dataframe(pd.DataFrame(persistencia.listar(m.metrica_calidad)), width="stretch")
    st.subheader("Reglas registradas")
    st.dataframe(pd.DataFrame(persistencia.listar(m.regla)), width="stretch")

with api_tab:
    st.code("GET /api/v1/fuentes\nGET /api/v1/observaciones?codigo_dpa=1101&anio=2026\n"
            "GET /api/v1/cruce?indicador_a=demo_poblacion&indicador_b=demo_ruc&anio=2026\n"
            "GET /api/v1/ejecuciones\nGET /api/v1/errores\nGET /api/v1/metricas")
    st.link_button("Abrir documentación de la API", "http://127.0.0.1:8000/docs")
