import matplotlib.pyplot as plt

def generar_grafico_top_productos(df, col_prod, col_cant):
    """Genera la gráfica horizontal del Top 10 productos."""
    top_10_prod = df.groupby(col_prod)[col_cant].sum().sort_values(ascending=True).tail(10)

    fig, ax = plt.subplots(figsize=(10, 4.5))
    top_10_prod.plot(kind='barh', color='#2e86de', edgecolor='none', ax=ax, width=0.7)
    ax.set_title('Top 10 Productos Más Vendidos (Unidades)', fontsize=12, fontweight='bold', pad=15)
    ax.set_xlabel('Unidades Vendidas')
    ax.set_ylabel('')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.bar_label(ax.containers[0], fmt='%d', padding=5, fontweight='bold')
    plt.tight_layout()
    return fig


def generar_grafico_geografia(df, col_estado):
    """Genera la gráfica horizontal del Top 10 estados."""
    df_geo_clean = df.dropna(subset=[col_estado])
    df_geo_clean = df_geo_clean[df_geo_clean[col_estado].astype(str).str.strip().str.lower() != 'nan']
    
    top_estados = df_geo_clean[col_estado].value_counts().head(10).sort_values(ascending=True)
    total_ventas_count = len(df_geo_clean)

    fig, ax = plt.subplots(figsize=(10, 4.5))
    top_estados.plot(kind='barh', color='#10ac84', edgecolor='none', ax=ax, width=0.7)
    ax.set_title('Top 10 Estados con Mayor Volumen de Pedidos', fontsize=12, fontweight='bold', pad=15)
    ax.set_xlabel('Número de Envíos')
    ax.set_ylabel('')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    for i, (valor, nombre) in enumerate(zip(top_estados, top_estados.index)):
        porcentaje = (valor / total_ventas_count) * 100 if total_ventas_count > 0 else 0
        ax.text(valor + 0.1, i, f' {valor:,} ({porcentaje:.1f}%)', va='center', fontweight='bold')

    ax.set_xlim(0, top_estados.max() * 1.25 if not top_estados.empty else 1)
    plt.tight_layout()
    return fig
