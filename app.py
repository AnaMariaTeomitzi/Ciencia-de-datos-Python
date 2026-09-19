import streamlit as st
import pandas as pd

# Importamos nuestras propias funciones modularizadas
from funciones_datos import consolidar_reportes, identificar_columnas, obtener_oportunidades_mkt
from funciones_graficos import generar_grafico_top_productos, generar_grafico_geografia

# CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(
    page_title="Dashboard de Ventas | Analytics",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ESTILOS CSS PERSONALIZADOS
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .kpi-card {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        border-left: 5px solid #2e86de;
        text-align: center;
        margin-bottom: 10px;
    }
    .kpi-card-green { border-left-color: #10ac84; }
    .kpi-card-orange { border-left-color: #ff9f43; }
    .kpi-title { font-size: 0.90rem; color: #576574; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
    .kpi-value { font-size: 1.8rem; font-weight: 700; color: #222f3e; margin-top: 5px; }
    .header-box { background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); padding: 24px; border-radius: 12px; color: white; margin-bottom: 25px; }
    .header-title { font-size: 2rem; font-weight: 700; margin: 0; }
    .header-subtitle { font-size: 1rem; opacity: 0.85; margin-top: 5px; }
    </style>
""", unsafe_allow_html=True)

# BANNER SUPERIOR
st.markdown("""
    <div class="header-box">
        <div class="header-title">🛍️ Centro de Control de Ventas</div>
        <div class="header-subtitle">Consolida reportes de Excel, analízalos por zonas y descubre oportunidades comerciales al instante.</div>
    </div>
""", unsafe_allow_html=True)

# BARRA LATERAL
with st.sidebar:
    st.header("⚙️ Configuración & Datos")
    archivos_subidos = st.file_uploader(
        "1. Subir Reporte(s) de Excel:", 
        type=["xlsx", "xls"], 
        accept_multiple_files=True,
        help="Puedes seleccionar varios archivos de ventas a la vez."
    )
    st.divider()

if archivos_subidos:
    df_ventas, total_registros, duplicados = consolidar_reportes(archivos_subidos)

    if df_ventas is not None and not df_ventas.empty:
        df_ventas, col_prod, col_ing, col_cant, col_estado, col_fecha = identificar_columnas(df_ventas)

        with st.sidebar:
            st.header("🔍 Filtros de Visualización")
            df_filtrado = df_ventas.copy()

            if col_fecha and not df_ventas[col_fecha].dropna().empty:
                f_min, f_max = df_ventas[col_fecha].min().date(), df_ventas[col_fecha].max().date()
                rango = st.date_input("Rango de Fechas:", value=(f_min, f_max), min_value=f_min, max_value=f_max)
                if isinstance(rango, (tuple, list)) and len(rango) == 2:
                    df_filtrado = df_filtrado[(df_filtrado[col_fecha].dt.date >= rango[0]) & (df_filtrado[col_fecha].dt.date <= rango[1])]

            if col_estado in df_ventas.columns:
                estados = sorted([e for e in df_ventas[col_estado].dropna().astype(str).str.strip().unique() if e and e.lower() != 'nan'])
                est_sel = st.selectbox("Filtrar por Estado/Provincia:", ["Todos"] + estados)
                if est_sel != "Todos":
                    df_filtrado = df_filtrado[df_filtrado[col_estado].astype(str).str.strip() == est_sel]

            st.caption(f"📌 **Resumen de Carga:** {len(archivos_subidos)} archivo(s) procesado(s). {duplicados} duplicados eliminados.")

        # METRICAS CLAVE
        total_ingresos = df_filtrado[col_ing].sum()
        total_unidades = df_filtrado[col_cant].sum()
        ticket_promedio = df_filtrado[col_ing].mean() if len(df_filtrado) > 0 else 0

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f'<div class="kpi-card"><div class="kpi-title">💰 Total Facturado</div><div class="kpi-value">${total_ingresos:,.2f} <small style="font-size:1rem">MXN</small></div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="kpi-card kpi-card-green"><div class="kpi-title">📦 Piezas Vendidas</div><div class="kpi-value">{int(total_unidades):,} <small style="font-size:1rem">unids</small></div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="kpi-card kpi-card-orange"><div class="kpi-title">🏷️ Ticket Promedio</div><div class="kpi-value">${ticket_promedio:,.2f} <small style="font-size:1rem">MXN</small></div></div>', unsafe_allow_html=True)

        st.write("")

        # PESTAÑAS
        pestaña_prod, pestaña_geo, pestaña_rec, pestaña_datos = st.tabs([
            "🏆 Top Productos", "🗺️ Análisis Geográfico", "💡 Oportunidades Clave", "📄 Tabla General"
        ])

        with pestaña_prod:
            st.subheader("Productos de Mayor Demanda")
            fig_prod = generar_grafico_top_productos(df_filtrado, col_prod, col_cant)
            st.pyplot(fig_prod)

        with pestaña_geo:
            st.subheader("Distribución Geográfica de Envíos")
            fig_geo = generar_grafico_geografia(df_filtrado, col_estado)
            st.pyplot(fig_geo)

        with pestaña_rec:
            st.subheader("💡 Oportunidades Comercializables por Concentración")
            st.caption("Esta sección identifica productos donde más del 20% de las ventas totales se concentran en una sola región.")
            
            oportunidades = obtener_oportunidades_mkt(df_filtrado, col_prod, col_estado, col_cant)
            if not oportunidades.empty:
                for _, row in oportunidades.head(10).iterrows():
                    with st.expander(f"📍 **{row[col_prod]}** ➔ **{row[col_estado]}**"):
                        st.write(f"El **{row['Porcentaje_Zona']:.1f}%** de la demanda total de este artículo se concentra en **{row[col_estado]}** ({int(row[col_cant])} unidades).")
                        st.info(f"💡 **Recomendación:** Considera promocionar este producto enfocado a **{row[col_estado]}**.")
            else:
                st.info("No se encontraron concentraciones atípicas de ventas por zona con los filtros actuales.")

        with pestaña_datos:
            st.subheader("Vista Detallada de Datos")
            st.dataframe(df_filtrado, use_container_width=True)

else:
    st.info("👋 **¡Hola! Bienvenido al Dashboard.** Sube tus archivos de Excel desde el panel lateral para iniciar.")
    col_g1, col_g2, col_g3 = st.columns(3)
    with col_g1:
        st.markdown("### 1️⃣ Carga tus Archivos")
        st.caption("Sube uno o múltiples reportes de ventas descargados desde Mercado Libre en formato `.xlsx`.")
    with col_g2:
        st.markdown("### 2️⃣ Filtra la Información")
        st.caption("Selecciona rangos de fechas o estados específicos para acotar tus resultados rápidamente.")
    with col_g3:
        st.markdown("### 3️⃣ Obtén Insights")
        st.caption("Visualiza tus productos estrella, concentración de envíos por región y sugerencias comerciales.")
