import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# 1. Configuración de la página
st.set_page_config(
    page_title="Panel de Ventas - Mercado Libre / Tienda",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Panel Interactivo de Resumen de Ventas")
st.write("Sube tu reporte de ventas en Excel para generar las métricas y gráficas automáticamente.")

# 2. Selector de archivo Excel interactivo
archivo_subido = st.file_uploader(
    "Selecciona tu archivo de Excel de ventas (ej. ventasjulio2026.xlsx)", 
    type=["xlsx", "xls"]
)

if archivo_subido is not None:
    # Cargar el archivo
    df_mis_ventas = pd.read_excel(archivo_subido)
    
    # ---------------------------------------------------------
    # DETECCIÓN DINÁMICA DE COLUMNAS Y LIMPIEZA DE ESPACIOS
    # ---------------------------------------------------------
    df_mis_ventas.columns = df_mis_ventas.columns.str.strip()

    col_prod = [c for c in df_mis_ventas.columns if 'Título' in c or 'Publicación' in c or 'Producto' in c]
    col_ing = [c for c in df_mis_ventas.columns if 'Ingresos' in c or 'Monto' in c or 'Total' in c]
    col_cant = [c for c in df_mis_ventas.columns if 'Unidades' in c or 'Cantidad' in c]
    col_est = [c for c in df_mis_ventas.columns if 'Estado' in c or 'Ubicación' in c]

    col_producto = col_prod[0] if col_prod else df_mis_ventas.columns[0]
    col_ingresos = col_ing[0] if col_ing else df_mis_ventas.columns[1]
    col_unidades = col_cant[0] if col_cant else df_mis_ventas.columns[2]
    columna_estado = col_est[0] if col_est else 'Estado.1'

    # ---------------------------------------------------------
    # CONVERSIÓN DE TEXTO A NÚMERO (LIMPIEZA DE $ Y COMAS)
    # ---------------------------------------------------------
    if col_ingresos in df_mis_ventas.columns:
        df_mis_ventas[col_ingresos] = (
            df_mis_ventas[col_ingresos]
            .astype(str)
            .str.replace('$', '', regex=False)
            .str.replace(',', '', regex=False)
            .str.strip()
        )
        df_mis_ventas[col_ingresos] = pd.to_numeric(df_mis_ventas[col_ingresos], errors='coerce').fillna(0)

    if col_unidades in df_mis_ventas.columns:
        df_mis_ventas[col_unidades] = (
            df_mis_ventas[col_unidades]
            .astype(str)
            .str.replace(',', '', regex=False)
            .str.strip()
        )
        df_mis_ventas[col_unidades] = pd.to_numeric(df_mis_ventas[col_unidades], errors='coerce').fillna(0)
    
    st.success(f"¡Archivo cargado con éxito! Se registraron **{len(df_mis_ventas):,}** ventas.")
    
    # --- PESTAÑAS DE NAVEGACIÓN ---
    tab_resumen, tab_productos, tab_geografia, tab_datos = st.tabs([
        "📈 Resumen Ejecutivo", 
        "🏆 Top Productos", 
        "🗺️ Ubicación / Estados", 
        "📋 Vista Previa de Datos"
    ])
    
    # ---------------------------------------------------------
    # PESTAÑA 1: RESUMEN EJECUTIVO (MÉTRICAS CLAVE)
    # ---------------------------------------------------------
    with tab_resumen:
        st.subheader("Métricas Principales")
        
        total_ingresos = df_mis_ventas[col_ingresos].sum() if col_ingresos in df_mis_ventas.columns else 0
        total_unidades = df_mis_ventas[col_unidades].sum() if col_unidades in df_mis_ventas.columns else 0
        ticket_promedio = df_mis_ventas[col_ingresos].mean() if col_ingresos in df_mis_ventas.columns else 0
        
        # Tarjetas numéricas (KPIs)
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("Total Vendido", f"${total_ingresos:,.2f} MXN")
        kpi2.metric("Total Unidades Vendidas", f"{total_unidades:,.0f} piezas")
        kpi3.metric("Ticket Promedio / Transacción", f"${ticket_promedio:,.2f} MXN")

    # ---------------------------------------------------------
    # PESTAÑA 2: TOP PRODUCTOS (TABLAS Y GRÁFICO)
    # ---------------------------------------------------------
    with tab_productos:
        st.subheader("Análisis de Productos")
        
        col_prod1, col_prod2 = st.columns(2)
        
        with col_prod1:
            st.markdown("### Top 5 por Unidades Vendidas")
            top_unidades = (
                df_mis_ventas.groupby(col_producto)[col_unidades]
                .sum()
                .sort_values(ascending=False)
                .head(5)
                .reset_index()
            )
            st.dataframe(top_unidades, use_container_width=True)
            
        with col_prod2:
            st.markdown("### Top 5 por Ingresos Generados")
            top_ingresos = (
                df_mis_ventas.groupby(col_producto)[col_ingresos]
                .sum()
                .sort_values(ascending=False)
                .head(5)
                .reset_index()
            )
            st.dataframe(
                top_ingresos.style.format({col_ingresos: '${:,.2f}'}), 
                use_container_width=True
            )

        st.divider()
        st.markdown("### 📊 Gráfica: Top 10 Productos Más Vendidos (Unidades)")
        
        top_10_unidades = (
            df_mis_ventas.groupby(col_producto)[col_unidades]
            .sum()
            .sort_values(ascending=True)
            .tail(10)
        )

        fig1, ax1 = plt.subplots(figsize=(10, 5))
        bars = top_10_unidades.plot(kind='barh', color='#3498db', edgecolor='black', ax=ax1)
        ax1.set_title('Top 10 Productos Más Vendidos (Unidades)', fontsize=13, fontweight='bold')
        ax1.set_xlabel('Unidades Vendidas')
        ax1.set_ylabel('')
        ax1.bar_label(ax1.containers[0], fmt='%d', padding=5, fontweight='bold')
        plt.tight_layout()
        
        st.pyplot(fig1)

    # ---------------------------------------------------------
    # PESTAÑA 3: TOP ESTADOS / GEOGRAFÍA
    # ---------------------------------------------------------
    with tab_geografia:
        st.subheader("Distribución Geográfica de Envíos")
        
        if columna_estado in df_mis_ventas.columns:
            top_estados = df_mis_ventas[columna_estado].value_counts().head(10).sort_values(ascending=True)
            total_ventas_count = len(df_mis_ventas)

            fig2, ax2 = plt.subplots(figsize=(10, 5))
            top_estados.plot(kind='barh', color='#2ecc71', edgecolor='black', ax=ax2)
            
            ax2.set_title('Top 10 Estados / Zonas con Mayor Cantidad de Ventas', fontsize=13, fontweight='bold')
            ax2.set_xlabel('Número de Envíos / Ventas')
            ax2.set_ylabel('')

            for i, (valor, nombre) in enumerate(zip(top_estados, top_estados.index)):
                porcentaje = (valor / total_ventas_count) * 100
                ax2.text(valor + 0.5, i, f'{valor:,} ({porcentaje:.1f}%)', va='center', fontweight='bold')

            ax2.set_xlim(0, top_estados.max() * 1.25)
            plt.tight_layout()
            
            st.pyplot(fig2)
        else:
            st.warning("No se encontró la columna de ubicación en el archivo Excel cargado.")

    # ---------------------------------------------------------
    # PESTAÑA 4: EXPLORADOR DE DATOS Y DIAGNÓSTICO
    # ---------------------------------------------------------
    with tab_datos:
        st.subheader("Explorador de Datos Registrados")
        
        busqueda = st.text_input("🔍 Buscar por título de publicación:")
        if busqueda:
            df_filtrado = df_mis_ventas[df_mis_ventas[col_producto].astype(str).str.contains(busqueda, case=False, na=False)]
            st.dataframe(df_filtrado, use_container_width=True)
        else:
            st.dataframe(df_mis_ventas, use_container_width=True)

        st.divider()
        st.markdown("#### 🛠️ Diagnóstico de Calidad de Datos")
        col_diag1, col_diag2 = st.columns(2)
        
        with col_diag1:
            st.write("**Datos Faltantes por Columna:**")
            st.dataframe(df_mis_ventas.isnull().sum().rename("Nulos"), use_container_width=True)
            
        with col_diag2:
            st.write("**Estructura de Columnas y Tipos:**")
            buffer = df_mis_ventas.dtypes.astype(str).rename("Tipo de Dato")
            st.dataframe(buffer, use_container_width=True)

else:
    st.info("💡 Sube tu archivo `.xlsx` de reporte de ventas en el recuadro superior para desplegar el resumen.")