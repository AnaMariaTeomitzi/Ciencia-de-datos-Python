from datetime import datetime
import numpy as np
import pandas as pd
import streamlit as st


def cargar_y_limpiar_excel(file):
    """Detecta el encabezado y carga el reporte de Mercado Libre."""
    preview = pd.read_excel(file, nrows=10, header=None)
    texto_inicio = " ".join(preview.iloc[:5, 0].dropna().astype(str).tolist())
    
    if "En este reporte" in texto_inicio or "Estado de tus ventas" in texto_inicio:
        df = pd.read_excel(file, skiprows=5)
    else:
        df = pd.read_excel(file)
    
    df.columns = df.columns.astype(str).str.strip()
    return df


def consolidar_reportes(archivos_subidos):
    """
    Consolida múltiples archivos subidos en Streamlit, soportando 
    tanto Excel (.xlsx, .xls) como archivos CSV (.csv).
    """
    lista_dfs = []
    total_registros_inicial = 0
    
    for archivo in archivos_subidos:
        nombre_archivo = archivo.name.lower()
        try:
            if nombre_archivo.endswith(('.xlsx', '.xls')):
                df_temp = pd.read_excel(archivo)
            elif nombre_archivo.endswith('.csv'):
                try:
                    df_temp = pd.read_csv(archivo, encoding='utf-8')
                except UnicodeDecodeError:
                    df_temp = pd.read_csv(archivo, encoding='latin-1')
            else:
                continue
            
            total_registros_inicial += len(df_temp)
            lista_dfs.append(df_temp)
        except Exception as e:
            print(f"Error al leer el archivo {archivo.name}: {e}")
            
    if not lista_dfs:
        return None, 0, 0
        
    df_consolidado = pd.concat(lista_dfs, ignore_index=True)
    
    filas_antes = len(df_consolidado)
    df_consolidado = df_consolidado.drop_duplicates()
    duplicados = filas_antes - len(df_consolidado)
    
    return df_consolidado, total_registros_inicial, duplicados


def identificar_columnas(df):
    """Detecta dinámicamente las columnas clave del reporte y ordena cronológicamente."""
    col_prod = [c for c in df.columns if ('Título' in c or 'Publicación' in c or 'Producto' in c) and 'estado' not in c.lower()]
    col_ing = [c for c in df.columns if 'Ingresos por productos' in c or 'Ingresos' in c or 'Monto' in c or 'Total' in c]
    col_cant = [c for c in df.columns if 'Unidades' in c or 'Cantidad' in c]
    col_fecha = [c for c in df.columns if 'Fecha' in c or 'fecha' in c]
    col_geo = [c for c in df.columns if c in ['Estado.1', 'Provincia'] or 'provincia' in c.lower() or 'destino' in c.lower()]

    col_producto = col_prod[0] if col_prod else df.columns[0]
    col_ingresos = col_ing[0] if col_ing else df.columns[1]
    col_unidades = col_cant[0] if col_cant else df.columns[2]
    
    if 'Estado.1' in df.columns:
        col_estado = 'Estado.1'
    elif col_geo:
        col_estado = col_geo[0]
    else:
        col_estado = 'Estado'

    col_f = col_fecha[0] if col_fecha else None

    if col_ingresos in df.columns:
        df[col_ingresos] = pd.to_numeric(
            df[col_ingresos].astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False).str.strip(),
            errors='coerce'
        ).fillna(0)

    if col_unidades in df.columns:
        df[col_unidades] = pd.to_numeric(
            df[col_unidades].astype(str).str.replace(',', '', regex=False).str.strip(),
            errors='coerce'
        ).fillna(0)

    if col_f and col_f in df.columns:
        df[col_f] = pd.to_datetime(df[col_f], errors='coerce')
        df = df.sort_values(by=col_f, ascending=True).reset_index(drop=True)

    return df, col_producto, col_ingresos, col_unidades, col_estado, col_f


def obtener_oportunidades_mkt(df, col_producto, col_estado, col_unidades):
    """Detecta concentraciones atípicas de ventas en ciertas regiones."""
    df_clean = df.dropna(subset=[col_estado, col_producto]).copy()
    df_clean[col_estado] = df_clean[col_estado].astype(str).str.strip()
    df_clean = df_clean[(df_clean[col_estado].str.lower() != 'nan') & (df_clean[col_estado] != '')]

    if df_clean.empty:
        return pd.DataFrame()

    df_patrones = (
        df_clean.groupby([col_producto, col_estado])[col_unidades]
        .sum()
        .reset_index()
        .sort_values(by=col_unidades, ascending=False)
    )
    
    totales_por_prod = df_clean.groupby(col_producto)[col_unidades].sum().to_dict()
    df_patrones['Total_Producto'] = df_patrones[col_producto].map(totales_por_prod)
    df_patrones['Porcentaje_Zona'] = (df_patrones[col_unidades] / df_patrones['Total_Producto']) * 100

    return df_patrones[(df_patrones['Porcentaje_Zona'] >= 20) & (df_patrones[col_unidades] >= 1)]


def filtrar_por_busqueda(df, texto_busqueda):
    """Filtra el DataFrame si el texto coincide con algún ID de venta o nombre de cliente."""
    if not texto_busqueda:
        return df
    
    cols_a_buscar = [c for c in df.columns if any(k in c.lower() for k in ['venta', 'id', 'comprador', 'cliente', 'apodo'])]
    if not cols_a_buscar:
        return df

    mask = False
    for col in cols_a_buscar:
        mask = mask | df[col].astype(str).str.contains(texto_busqueda, case=False, na=False)
        
    return df[mask]


def calcular_deuda_excel(df, col_prod, col_cant, costos_dict, punto_corte):
    """
    Calcula la deuda para Excel: desde la primera fila HASTA el folio indicado inclusive.
    """
    if df is None or df.empty:
        return 0.0, pd.DataFrame()

    df_calc = df.copy()
    df_calc["Costo_Unitario"] = df_calc[col_prod].map(costos_dict).fillna(0.0)
    df_calc["Subtotal_Deuda"] = df_calc[col_cant] * df_calc["Costo_Unitario"]

    if not punto_corte or not str(punto_corte).strip():
        return 0.0, pd.DataFrame()

    cols_id = [c for c in df_calc.columns if any(k in c.lower() for k in ['id', 'venta', 'orden', 'folio'])]
    col_id = cols_id[0] if cols_id else df_calc.columns[0]
    
    df_calc = df_calc.reset_index(drop=True)
    coincidencia = df_calc[df_calc[col_id].astype(str).str.strip() == str(punto_corte).strip()]

    if coincidencia.empty:
        return 0.0, pd.DataFrame()

    pos_corte = coincidencia.index[0]
    df_filtrado_deuda = df_calc.iloc[:pos_corte + 1]
    monto_total = df_filtrado_deuda["Subtotal_Deuda"].sum()
    
    return monto_total, df_filtrado_deuda


def calcular_deuda_api(df, col_prod, col_cant, costos_dict, punto_corte):
    """
    Calcula la deuda para API: ordena cronológicamente y calcula desde el folio indicado HASTA la última fila.
    """
    if df is None or df.empty:
        return 0.0, pd.DataFrame()

    df_calc = df.copy()
    df_calc["Costo_Unitario"] = df_calc[col_prod].map(costos_dict).fillna(0.0)
    df_calc["Subtotal_Deuda"] = df_calc[col_cant] * df_calc["Costo_Unitario"]

    if not punto_corte or not str(punto_corte).strip():
        return 0.0, pd.DataFrame()

    cols_id = [c for c in df_calc.columns if any(k in c.lower() for k in ['id', 'venta', 'orden', 'folio'])]
    col_id = cols_id[0] if cols_id else df_calc.columns[0]
    
    col_fecha = "Fecha" if "Fecha" in df_calc.columns else next((c for c in df_calc.columns if 'fecha' in c.lower()), None)

    if col_fecha and col_fecha in df_calc.columns:
        df_calc[col_fecha] = pd.to_datetime(df_calc[col_fecha], errors="coerce")
        df_calc = df_calc.sort_values(by=col_fecha, ascending=True).reset_index(drop=True)
    else:
        df_calc = df_calc.reset_index(drop=True)

    coincidencia = df_calc[df_calc[col_id].astype(str).str.strip() == str(punto_corte).strip()]

    if coincidencia.empty:
        return 0.0, pd.DataFrame()

    pos_corte = coincidencia.index[0]
    df_filtrado_deuda = df_calc.iloc[pos_corte:]
    monto_total = df_filtrado_deuda["Subtotal_Deuda"].sum()
    
    return monto_total, df_filtrado_deuda
