from dash import Dash, dcc, html, Input, Output, State
import pandas as pd
import plotly.express as px
import os


def load_data():
    try:
        cols = ["GESTION", "MES", "DESPAIS", "DESNAN", "DESGCE3",
                "DESCIIU3", "DESACT2", "DESDEP", "VALOR", "KILNET"]
        df_2023 = pd.read_excel("data/EXPORTACIONES_2023p.xlsx", usecols=cols)
        df_2024 = pd.read_excel("data/EXPORTACIONES_2024p.xlsx", usecols=cols)
        df = pd.concat([df_2023, df_2024], ignore_index=True)
    except FileNotFoundError:
        print("⚠️ Excel-Dateien nicht gefunden. Bitte prüfen.")
        return pd.DataFrame()

    df['VALOR'] = df['VALOR'].fillna(0).astype(int)
    df['KILNET'] = df['KILNET'].fillna(0).astype(int)

    for col in cols[:-2]:
        df[col] = df[col].fillna("Sin datos")

    return df


def chf_format(value):
    return f"{value:,.0f}".replace(",", "'")


def no_data_fig(message="⚠️ Keine Daten für die aktuelle Auswahl."):
    fig = px.scatter(title=message)
    return html.Div(message), fig, fig, fig, fig, fig


def apply_standard_layout(fig):
    fig.update_layout(
        font=dict(family="Arial", size=16),
        title_font_size=30,
        margin=dict(l=50, r=50, t=50, b=50),
        xaxis_title="Valor exportado (USD)",
        yaxis_title=""
    )
    return fig


def filter_df(df, anio, mes, pais, producto, categoria, industria, actividad, departamentos):
    dff = df.query("GESTION == @anio")

    if mes != "Todos":
        dff = dff.query("MES == @mes")
    if pais:
        dff = dff.query("DESPAIS in @pais")
    if producto:
        dff = dff.query("DESNAN in @producto")
    if categoria:
        dff = dff.query("DESGCE3 in @categoria")
    if industria:
        dff = dff.query("DESCIIU3 in @industria")
    if actividad:
        dff = dff.query("DESACT2 in @actividad")
    if departamentos:
        dff = dff.query("DESDEP in @departamentos")

    return dff.query("VALOR > 0")


def create_sankey(df_sankey):
    labels = pd.unique(df_sankey['DESDEP'].tolist() +
                       df_sankey['DESGCE3'].tolist() +
                       df_sankey['DESPAIS'].tolist()).tolist()
    label_index = {label: i for i, label in enumerate(labels)}

    sources, targets, values = [], [], []

    for _, row in df_sankey.iterrows():
        sources.append(label_index[row['DESDEP']])
        targets.append(label_index[row['DESGCE3']])
        values.append(row['VALOR'])

    for _, row in df_sankey.iterrows():
        sources.append(label_index[row['DESGCE3']])
        targets.append(label_index[row['DESPAIS']])
        values.append(row['VALOR'])

    customdata = [f"{labels[s]} → {labels[t]}: USD {v:,.0f}".replace(",", "'") for s, t, v in zip(sources, targets, values)]

    return {
        "data": [dict(
            type='sankey',
            node=dict(pad=15, thickness=20, line=dict(color="black", width=0.5), label=labels, color="lightblue"),
            link=dict(source=sources, target=targets, value=values, customdata=customdata, hovertemplate='%{customdata}<extra></extra>')
        )],
        "layout": dict(
            title="🔀 Flujo: Departamento → Producto → País de destino",
            font=dict(size=14),
            margin=dict(t=50, l=0, r=0, b=50)
        )
    }


# Start Dash App
app = Dash(__name__)
server = app.server

# Daten laden
df = load_data()

# Layout
app.layout = html.Div([
    html.H1("BO 📦 Exportaciones Bolivianas – Dashboard"),
    html.Div([
        html.Label("Gestión:"),
        dcc.Dropdown(id='anio', options=[{"label": str(a), "value": a} for a in sorted(df['GESTION'].unique())],
                     value=sorted(df['GESTION'].unique())[-1]),
        html.Label("Mes (opcional):"),
        dcc.Dropdown(id='mes', options=[{"label": "Todos", "value": "Todos"}] +
                     [{"label": str(m), "value": m} for m in sorted(df['MES'].unique())], value="Todos"),
        html.Label("País de destino:"),
        dcc.Dropdown(id='pais', options=[{"label": p, "value": p} for p in sorted(df['DESPAIS'].unique())], multi=True),
        html.Label("Producto NANDINA:"),
        dcc.Dropdown(id='producto', options=[{"label": p, "value": p} for p in sorted(df['DESNAN'].unique())], multi=True),
        html.Label("Categoría Económica:"),
        dcc.Dropdown(id='categoria', options=[{"label": c, "value": c} for c in sorted(df['DESGCE3'].unique())], multi=True),
        html.Label("Industria (CIIU):"),
        dcc.Dropdown(id='industria', options=[{"label": i, "value": i} for i in sorted(df['DESCIIU3'].unique())], multi=True),
        html.Label("Producto Económico:"),
        dcc.Dropdown(id='actividad', options=[{"label": a, "value": a} for a in sorted(df['DESACT2'].unique())], multi=True),
        html.Label("Departamento:"),
        dcc.Dropdown(id='departamento', options=[{"label": d, "value": d} for d in sorted(df['DESDEP'].unique())], multi=True)
    ]),
    html.Div([
        html.Div(id='kpis'),
        dcc.Graph(id='grafico-departamento'),
        dcc.Graph(id='grafico-pais'),
        dcc.Graph(id='grafico-producto'),
        dcc.Graph(id='grafico-sankey', style={"height": "150vh"}),
        dcc.Graph(id='grafico-treemap')
    ])
])


@app.callback(
    [Output('kpis', 'children'),
     Output('grafico-pais', 'figure'),
     Output('grafico-producto', 'figure'),
     Output('grafico-departamento', 'figure'),
     Output('grafico-treemap', 'figure'),
     Output('grafico-sankey', 'figure')],
    [Input('anio', 'value'), Input('mes', 'value'), Input('pais', 'value'),
     Input('producto', 'value'), Input('categoria', 'value'), Input('industria', 'value'),
     Input('actividad', 'value'), Input('departamento', 'value')]
)
def actualizar_dashboard(anio, mes, pais, producto, categoria, industria, actividad, departamentos):
    dff = filter_df(df, anio, mes, pais, producto, categoria, industria, actividad, departamentos)

    if dff.empty:
        return no_data_fig()

    total_valor = dff['VALOR'].sum()
    total_peso = dff['KILNET'].sum()

    kpi_html = html.Div([
        html.H4(f"Departamentos seleccionados: {', '.join(departamentos) if departamentos else 'Todos'}"),
        html.H4(f"Valor Total USD: {chf_format(total_valor)}"),
        html.H4(f"Peso Neto Total: {chf_format(total_peso)} kg")
    ])

    fig_pais = apply_standard_layout(
        px.bar(dff.groupby("DESPAIS")["VALOR"].sum().nlargest(15).sort_values().reset_index(),
               x="VALOR", y="DESPAIS", orientation='h', title="🌍 Top 15 Países de Destino", template="plotly_white")
    )

    fig_producto = apply_standard_layout(
        px.bar(dff.groupby("DESACT2")["VALOR"].sum().nlargest(15).sort_values().reset_index(),
               x="VALOR", y="DESACT2", orientation='h', title="📦 Top 15 Productos", template="plotly_white")
    )

    fig_departamento = apply_standard_layout(
        px.bar(dff.groupby("DESDEP")["VALOR"].sum().sort_values().reset_index(),
               x="VALOR", y="DESDEP", orientation='h', title="🗺️ Valor por Departamento", template="plotly_white")
    )

    df_treemap = dff.copy()
    df_treemap['VALOR_TXT'] = df_treemap['VALOR'].apply(lambda x: f"USD {x:,.0f}".replace(",", "'"))
    fig_treemap = px.treemap(df_treemap, path=['DESCIIU3', 'DESNAN', 'DESACT2'],
                             values='VALOR', custom_data=['VALOR_TXT'],
                             title="📂 Exportaciones", color_continuous_scale='YlGnBu')
    fig_treemap.update_layout(margin=dict(t=100, l=100, r=100, b=100), font=dict(size=16))

    df_sankey = dff.groupby(['DESDEP', 'DESGCE3', 'DESPAIS'])['VALOR'].sum().reset_index()
    fig_sankey = create_sankey(df_sankey)

    return kpi_html, fig_pais, fig_producto, fig_departamento, fig_treemap, fig_sankey


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8050))
    app.run(host='0.0.0.0', port=port, debug=False)