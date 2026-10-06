import os
import requests
import streamlit as st
import pandas as pd
from datetime import datetime

# Importamos nuestras funciones modularizadas (incluyendo ambas variantes de deuda)
from funciones_datos import (
    consolidar_reportes,
    identificar_columnas,
    obtener_oportunidades_mkt,
    filtrar_por_busqueda,
    calcular_deuda_excel,
    calcular_deuda_api,
)
from funciones_graficos import (
    generar_grafico_top_productos,
    generar_grafico_geografia,
)

# CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(
    page_title="Dashboard de Ventas | Analytics",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ESTILOS CSS PERSONALIZADOS
st.markdown(
    """
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
""",
    unsafe_allow_html=True,
)

# BANNER SUPERIOR
st.markdown(
    """
    <div class="header-box">
        <div class="header-title">🛍️ Centro de Control de Ventas</div>
        <div class="header-subtitle">Consolida reportes (Excel/CSV or API), analiza zonas, controla costos y calcula deudas con proveedores.</div>
    </div>
""",
    unsafe_allow_html=True,
)

# CONSTANTES DE TU CUENTA Y APLICACIÓN DE MERCADO LIBRE
CLIENT_ID = "3911537812542782"
USER_ID = "190690333"

# BARRA LATERAL
with st.sidebar:
  st.header("⚙️ Configuración & Datos")

  modo_carga = st.radio(
      "Selecciona el origen de los datos:",
      ("📁 Archivo Excel / CSV (Manual)", "🌐 En vivo (API Mercado Libre)"),
  )
  st.divider()

df_ventas = None
duplicados = 0
archivos_subidos = None

# ==========================================
# OPCIÓN A: CARGA MEDIANTE EXCEL / CSV
# ==========================================
if modo_carga == "📁 Archivo Excel / CSV (Manual)":
  with st.sidebar:
    archivos_subidos = st.file_uploader(
        "1. Subir Reporte(s) (Excel o CSV):",
        type=["xlsx", "xls", "csv"],
        accept_multiple_files=True,
        help="Puedes seleccionar varios archivos de ventas o inventario a la vez.",
    )
    st.divider()

  if archivos_subidos:
    df_ventas, total_registros, duplicados = consolidar_reportes(
        archivos_subidos
    )

# ==========================================
# OPCIÓN B: SINCRONIZACIÓN EN VIVO (API M.L.)
# ==========================================
else:
  with st.sidebar:
    st.subheader("📡 Conexión API Mercado Libre")

    with st.expander("🔑 Generar o Canjear Access Token", expanded=True):
      st.caption(f"App Client ID detectado: `{CLIENT_ID}`")
      client_secret_input = st.text_input(
          "Client Secret:", type="password", key="sec_secret"
      )
      code_obtenido = st.text_input(
          "Código (code) NUEVO:",
          value="",
          placeholder="Pega tu código TG-... reciente",
          key="sec_code",
      )

      if st.button("🚀 Canjear por Access Token"):
        if not client_secret_input or not code_obtenido:
          st.warning("Faltan el Client Secret o el Código (code).")
        else:
          url_token = "https://api.mercadolibre.com/oauth/token"
          payload = {
              "grant_type": "authorization_code",
              "client_id": CLIENT_ID,
              "client_secret": client_secret_input,
              "code": code_obtenido,
              "redirect_uri": "https://www.google.com",
          }
          headers = {
              "accept": "application/json",
              "content-type": "application/x-www-form-urlencoded",
          }
          res_token = requests.post(url_token, data=payload, headers=headers)

          if res_token.status_code == 200:
            token_json = res_token.json()
            st.session_state["token_generado"] = token_json.get("access_token")
            st.success("¡Token obtenido con éxito!")
          else:
            st.error(f"Error: {res_token.text}")

    token_sugerido = st.session_state.get("token_generado", "")
    access_token_input = st.text_input(
        "Access Token:", value=token_sugerido, type="password"
    )

    if st.button("🔄 Sincronizar Ventas Ahora"):
      if not access_token_input:
        st.warning("Por favor ingresa o genera un Access Token válido.")
      else:
        with st.spinner("Descargando órdenes desde Mercado Libre..."):
          url = f"https://api.mercadolibre.com/orders/search?seller={USER_ID}&sort=date_desc&limit=50"
          headers = {"Authorization": f"Bearer {access_token_input}"}

          response = requests.get(url, headers=headers)

          if response.status_code == 200:
            datos = response.json()
            results = datos.get("results", [])

            if results:
              lista_ordenes = []
              for orden in results:
                order_id = str(orden.get("id"))
                fecha = orden.get("date_closed")
                total = orden.get("total_amount")

                items = orden.get("order_items", [])
                producto = (
                    items[0]["item"]["title"] if items else "Sin detalle"
                )
                cantidad = items[0].get("quantity", 1) if items else 1

                shipping = orden.get("shipping", {})
                receiver_address = shipping.get("receiver_address", {})
                state = (
                    receiver_address.get("state", {})
                    .get("name", "Desconocido")
                )

                lista_ordenes.append({
                    "ID_Orden": order_id,
                    "Fecha": fecha,
                    "Producto": producto,
                    "Cantidad": cantidad,
                    "Total": total,
                    "Estado": state,
                })

              df_ventas = pd.DataFrame(lista_ordenes)
              st.success(
                  f"¡Sincronización exitosa! {len(df_ventas)} ventas cargadas."
              )
              st.session_state["df_ventas_ml_cache"] = df_ventas
            else:
              st.info("No se encontraron órdenes recientes.")
          else:
            st.error(f"Error al conectar con la API: {response.text}")

    if "df_ventas_ml_cache" in st.session_state and df_ventas is None:
      df_ventas = st.session_state["df_ventas_ml_cache"]

    st.divider()

# ==========================================
# PROCESAMIENTO GENERAL DEL DASHBOARD
# ==========================================
if df_ventas is not None and not df_ventas.empty:
  (
      df_ventas,
      col_prod,
      col_ing,
      col_cant,
      col_estado,
      col_fecha,
  ) = identificar_columnas(df_ventas)

  with st.sidebar:
    st.header("🔍 Filtros de Visualización")
    df_filtrado = df_ventas.copy()

    texto_busqueda = st.text_input(
        "🔎 Buscar Venta o Cliente:", placeholder="Ej. 2000 o nombre..."
    )
    if texto_busqueda:
      df_filtrado = filtrar_por_busqueda(df_filtrado, texto_busqueda)

    st.divider()

    if col_fecha and not df_ventas[col_fecha].dropna().empty:
      df_ventas[col_fecha] = pd.to_datetime(
          df_ventas[col_fecha], errors="coerce"
      )
      df_filtrado[col_fecha] = pd.to_datetime(
          df_filtrado[col_fecha], errors="coerce"
      )

      f_min, f_max = (
          df_ventas[col_fecha].min().date(),
          df_ventas[col_fecha].max().date(),
      )
      rango = st.date_input(
          "Rango de Fechas:", value=(f_min, f_max), min_value=f_min, max_value=f_max
      )
      if isinstance(rango, (tuple, list)) and len(rango) == 2:
        df_filtrado = df_filtrado[
            (df_filtrado[col_fecha].dt.date >= rango[0])
            & (df_filtrado[col_fecha].dt.date <= rango[1])
        ]

    if col_estado in df_ventas.columns:
      estados = sorted([
          e
          for e in df_ventas[col_estado]
          .dropna()
          .astype(str)
          .str.strip()
          .unique()
          if e and e.lower() != "nan"
      ])
      est_sel = st.selectbox("Filtrar por Estado/Provincia:", ["Todos"] + estados)
      if est_sel != "Todos":
        df_filtrado = df_filtrado[
            df_filtrado[col_estado].astype(str).str.strip() == est_sel
        ]

  # METRICAS CLAVE
  total_ingresos = df_filtrado[col_ing].sum()
  total_unidades = df_filtrado[col_cant].sum()
  ticket_promedio = df_filtrado[col_ing].mean() if len(df_filtrado) > 0 else 0

  c1, c2, c3 = st.columns(3)
  with c1:
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-title">💰 Total Facturado</div><div'
        f' class="kpi-value">${total_ingresos:,.2f} <small'
        ' style="font-size:1rem">MXN</small></div></div>',
        unsafe_allow_html=True,
    )
  with c2:
    st.markdown(
        f'<div class="kpi-card kpi-card-green"><div class="kpi-title">📦 Piezas'
        f' Vendidas</div><div class="kpi-value">{int(total_unidades):,} <small'
        ' style="font-size:1rem">unids</small></div></div>',
        unsafe_allow_html=True,
    )
  with c3:
    st.markdown(
        f'<div class="kpi-card kpi-card-orange"><div class="kpi-title">🏷️'
        f' Ticket Promedio</div><div class="kpi-value">${ticket_promedio:,.2f}'
        ' <small style="font-size:1rem">MXN</small></div></div>',
        unsafe_allow_html=True,
    )

  st.write("")

  pestaña_prod, pestaña_geo, pestaña_rec, pestaña_prov, pestaña_datos = (
      st.tabs([
          "🏆 Top Productos",
          "🗺️ Análisis Geográfico",
          "💡 Oportunidades Clave",
          "💸 Control de Proveedor",
          "📄 Tabla General",
      ])
  )

  with pestaña_prod:
    st.subheader("Productos de Mayor Demanda")
    if not df_filtrado.empty:
      fig_prod = generar_grafico_top_productos(df_filtrado, col_prod, col_cant)
      st.pyplot(fig_prod)
    else:
      st.warning("No hay datos para mostrar con los filtros seleccionados.")

  with pestaña_geo:
    st.subheader("Distribución Geográfica de Envíos")
    if not df_filtrado.empty:
      fig_geo = generar_grafico_geografia(df_filtrado, col_estado)
      st.pyplot(fig_geo)
    else:
      st.warning("No hay datos para mostrar con los filtros seleccionados.")

  with pestaña_rec:
    st.subheader("💡 Oportunidades Comercializables por Concentración")
    oportunidades = obtener_oportunidades_mkt(
        df_filtrado, col_prod, col_estado, col_cant
    )
    if not oportunidades.empty:
      for _, row in oportunidades.head(10).iterrows():
        with st.expander(
            f"📍 **{row[col_prod]}** ➔ **{row[col_estado]}**"
        ):
          st.write(
              f"El **{row['Porcentaje_Zona']:.1f}%** de la demanda total se"
              f" concentra en **{row[col_estado]}**"
              f" ({int(row[col_cant])} unidades)."
          )
    else:
      st.info(
          "No se encontraron concentraciones atípicas con los filtros"
          " actuales."
      )

  with pestaña_prov:
    st.subheader("💸 Control de Costos y Deuda con Proveedor")
    archivo_costos = "costos_proveedor.csv"
    productos_unicos = df_ventas[col_prod].dropna().unique()
    df_base_costos = pd.DataFrame(
        {"Producto": productos_unicos, "Costo de Compra (MXN)": 0.0}
    )

    if os.path.exists(archivo_costos):
      df_guardado = pd.read_csv(archivo_costos)
      df_base_costos = df_base_costos.merge(
          df_guardado[["Producto", "Costo de Compra (MXN)"]],
          on="Producto",
          how="left",
          suffixes=("", "_old"),
      )
      df_base_costos["Costo de Compra (MXN)"] = df_base_costos[
          "Costo de Compra (MXN)_old"
      ].fillna(df_base_costos["Costo de Compra (MXN)"])
      df_base_costos = df_base_costos[["Producto", "Costo de Compra (MXN)"]]

    df_costos_editado = st.data_editor(
        df_base_costos, num_rows="fixed", use_container_width=True
    )
    if st.button("💾 Guardar Precios"):
      df_costos_editado.to_csv(archivo_costos, index=False)
      st.success("¡Precios guardados con éxito!")

    costos_dict = dict(
        zip(
            df_costos_editado["Producto"],
            df_costos_editado["Costo de Compra (MXN)"],
        )
    )
    punto_corte = st.text_input("Antecedente / Último # de Venta Pagado:")
    
    # ==========================================
    # SELECCIÓN DINÁMICA DE CÁLCULO DE DEUDA
    # ==========================================
    if modo_carga == "📁 Archivo Excel / CSV (Manual)":
      # Caso Excel: Del inicio de la tabla hasta el folio seleccionado (casilla 1)
      monto_deuda, df_detalle_deuda = calcular_deuda_excel(
          df_filtrado, col_prod, col_cant, costos_dict, punto_corte
      )
    else:
      # Caso API: Del folio seleccionado hasta la última fila
      monto_deuda, df_detalle_deuda = calcular_deuda_api(
          df_filtrado, col_prod, col_cant, costos_dict, punto_corte
      )

    st.metric("Total a Pagar al Proveedor", f"${monto_deuda:,.2f} MXN")

    # MOSTRAR LISTADO DE PRODUCTOS CONSIDERADOS
    if not df_detalle_deuda.empty:
      st.markdown("#### 📋 Listado de Productos Considerados en este Cálculo")
      cols_a_mostrar = [
          c
          for c in [
              "Fecha",
              "ID_Orden",
              col_prod,
              col_cant,
              "Costo_Unitario",
              "Subtotal_Deuda",
          ]
          if c in df_detalle_deuda.columns
      ]
      st.dataframe(df_detalle_deuda[cols_a_mostrar], use_container_width=True)

      # GUARDAR AUTOMÁTICAMENTE EL ÚLTIMO FOLIO Y FECHA
      if punto_corte.strip():
        if "historial_consultas" not in st.session_state:
          st.session_state.historial_consultas = []

        fecha_consulta_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        nuevo_registro = {
            "Fecha_Consulta": fecha_consulta_actual,
            "Ultimo_Folio": punto_corte.strip(),
            "Total_Deuda": round(monto_deuda, 2),
        }

        if (
            not st.session_state.historial_consultas
            or st.session_state.historial_consultas[-1]["Ultimo_Folio"]
            != punto_corte.strip()
        ):
          st.session_state.historial_consultas.append(nuevo_registro)

    # MOSTRAR HISTORIAL DE CONSULTAS ANTERIORES
    if (
        "historial_consultas" in st.session_state
        and st.session_state.historial_consultas
    ):
      with st.expander("🕒 Ver Historial de Folios y Fechas Consultadas"):
        df_historial = pd.DataFrame(st.session_state.historial_consultas)
        st.dataframe(df_historial, use_container_width=True)

  with pestaña_datos:
    st.subheader("Vista Detallada de Datos")
    st.dataframe(df_filtrado, use_container_width=True)

else:
  if modo_carga == "📁 Archivo Excel / CSV (Manual)":
    st.info("👋 Sube tus archivos en la barra lateral para iniciar.")
  else:
    st.info(
        "👋 Genera tu Access Token con un código nuevo en la barra lateral para"
        " sincronizar tus ventas."
    )
