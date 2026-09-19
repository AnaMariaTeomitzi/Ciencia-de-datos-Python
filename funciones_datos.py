import pandas as pd

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
    """Une múltiples reportes, limpia duplicados y formatea columnas clave."""
    lista_dfs = []
    for archivo in archivos_subidos:
        try:
            temp_df = cargar_y_limpiar_excel(archivo)
            lista_dfs.append(temp_df)
        except Exception:
            pass

    if not lista_dfs:
        return None, 0, 0

    df_consolidado = pd.concat(lista_dfs, ignore_index=True)
    filas_iniciales = len(df_consolidado)

    # Identificar ID de venta para quitar duplicados
    col_id_venta = [c for c in df_consolidado.columns if '# de venta' in c or 'N° de venta' in c or 'ID de venta' in c or 'ID' in c]
    
    if col_id_venta:
        col_id = col_id_venta[0]
        df_consolidado = df_consolidado.dropna(subset=[col_id])
        df_consolidado = df_consolidado[pd.to_numeric(df_consolidado[col_id], errors='coerce').notna()]
        df_consolidado = df_consolidado.drop_duplicates(subset=[col_id], keep='first')
    else:
        df_consolidado = df_consolidado.dropna(how='all')

    filas_finales = len(df_consolidado)
    duplicados = filas_iniciales - filas_finales

    return df_consolidado, filas_finales, duplicados


def identificar_columnas(df):
    """Detecta dinámicamente las columnas clave del reporte."""
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

    # Formato numérico y fechas
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
