from dash import Dash, dcc, html, Input, Output, State
import pandas as pd
import plotly.express as px

# Daten laden und zusammenführen
df_2023 = pd.read_excel("EXPORTACIONES_2023p.xlsx")
df_2024 = pd.read_excel("EXPORTACIONES_2024p.xlsx")
df = pd.concat([df_2023, df_2024], ignore_index=True)

# Zahlenformat anpassen
df['VALOR'] = df['VALOR'].round(0)
df['KILNET'] = df['KILNET'].round(0)

# Dash App initialisieren
app = Dash(__name__)
server = app.server

# Layout definieren
app.layout = html.Div([
    html.H1("📦 Exportaciones Bolivianas – Dashboard", style={"textAlign": "center"}),

    html.Div([
        html.Label("Año:"),
        dcc.Dropdown(
            id='anio',
            options=[{"label": str(a), "value": a} for a in sorted(df['GESTION'].dropna().unique())],
            value=sorted(df['GESTION'].dropna().unique())[-1]
        ),
        html.Label("Mes (opcional):"),
        dcc.Dropdown(
            id='mes',
            options=[{"label": "Todos", "value": "Todos"}] +
                    [{"label": str(m), "value": m} for m in sorted(df['MES'].dropna().unique())],
            value="Todos"
        ),
        html.Label("País de destino:"),
        dcc.Dropdown(
            id='pais',
            options=[{"label": p, "value": p} for p in sorted(df['DESPAIS'].dropna().unique())],
            multi=True
        ),
        html.Label("Producto (DESNAN):"),
        dcc.Dropdown(
            id='producto',
            options=[{"label": p, "value": p} for p in sorted(df['DESNAN'].dropna().unique())],
            multi=True
        ),
        html.Label("Categoría económica (DESGCE3):"),
        dcc.Dropdown(
            id='categoria',
            options=[{"label": c, "value": c} for c in sorted(df['DESGCE3'].dropna().unique())],
            multi=True
        ),
        html.Label("Industria (DESCIIU3):"),
        dcc.Dropdown(
            id='industria',
            options=[{"label": i, "value": i} for i in sorted(df['DESCIIU3'].dropna().unique())],
            multi=True
        ),
        html.Label("Actividad (DESACT2):"),
        dcc.Dropdown(
            id='actividad',
            options=[{"label": a, "value": a} for a in sorted(df['DESACT2'].dropna().unique())],
            multi=True
        ),
        html.Label("Departamento de origen:"),
        dcc.Dropdown(
            id='departamento',
            options=[{"label": d, "value": d} for d in sorted(df['DESDEP'].dropna().unique())],
            multi=True
        )
    ], style={"width": "25%", "float": "left", "padding": "20px"}),

    html.Div([
        html.Div(id='kpis'),
        dcc.Graph(id='grafico-departamento', clear_on_unhover=True),
        dcc.Graph(id='grafico-pais', clear_on_unhover=True),
        dcc.Graph(id='grafico-producto', clear_on_unhover=True),
        dcc.Graph(id='grafico-treemap', clear_on_unhover=True)
    ], style={"width": "65%", "float": "right", "padding": "20px"})
])

# Callbacks zur Synchronisierung von Klicks mit Dropdowns
@app.callback(
    Output('departamento', 'value'),
    Input('grafico-departamento', 'clickData'),
    State('departamento', 'value')
)
def sync_departamento(clickData, current):
    if clickData and 'points' in clickData:
        val = clickData['points'][0]['y']
        return current + [val] if current and val not in current else current or [val]
    return current

@app.callback(
    Output('pais', 'value'),
    Input('grafico-pais', 'clickData'),
    State('pais', 'value')
)
def sync_pais(clickData, current):
    if clickData and 'points' in clickData:
        val = clickData['points'][0]['y']
        return current + [val] if current and val not in current else current or [val]
    return current

@app.callback(
    Output('producto', 'value'),
    Input('grafico-producto', 'clickData'),
    State('producto', 'value')
)
def sync_producto(clickData, current):
    if clickData and 'points' in clickData:
        val = clickData['points'][0]['y']
        return current + [val] if current and val not in current else current or [val]
    return current

# Dashboard-Callback inkl. Treemap
@app.callback(
    [Output('kpis', 'children'),
     Output('grafico-pais', 'figure'),
     Output('grafico-producto', 'figure'),
     Output('grafico-departamento', 'figure'),
     Output('grafico-treemap', 'figure')],
    [Input('anio', 'value'),
     Input('mes', 'value'),
     Input('pais', 'value'),
     Input('producto', 'value'),
     Input('categoria', 'value'),
     Input('industria', 'value'),
     Input('actividad', 'value'),
     Input('departamento', 'value')]
)
def actualizar_dashboard(anio, mes, pais, producto, categoria, industria, actividad, departamentos):
    dff = df[df['GESTION'] == anio]
    if mes != "Todos":
        dff = dff[dff['MES'] == mes]
    if pais:
        dff = dff[dff['DESPAIS'].isin(pais)]
    if producto:
        dff = dff[dff['DESNAN'].isin(producto)]
    if categoria:
        dff = dff[dff['DESGCE3'].isin(categoria)]
    if industria:
        dff = dff[dff['DESCIIU3'].isin(industria)]
    if actividad:
        dff = dff[dff['DESACT2'].isin(actividad)]
    if departamentos:
        dff = dff[dff['DESDEP'].isin(departamentos)]

    dff = dff[dff['VALOR'] > 0]

    total_valor = dff['VALOR'].sum()
    total_peso = dff['KILNET'].sum()

    def chf_format(value):
        return f"USD {value:,.0f}".replace(",", "'")

    kpi_html = html.Div([
        html.H4("Departamentos seleccionados: " + ", ".join(departamentos) if departamentos else "Todos los departamentos"),
        html.H4(f"Valor Total: {chf_format(total_valor)}"),
        html.H4(f"Peso Neto Total: {chf_format(total_peso)} kg")
    ])

    fig_pais = px.bar(
        dff.groupby("DESPAIS")["VALOR"].sum().reset_index().query("VALOR > 100000").sort_values("VALOR", ascending=True),
        x="VALOR", y="DESPAIS", orientation='h', title="🌍 Valor exportado por país de destino", template="plotly_white"
    )
    fig_producto = px.bar(
        dff.groupby("DESNAN")["VALOR"].sum().reset_index().query("VALOR > 10000").sort_values("VALOR", ascending=True).head(10),
        x="VALOR", y="DESNAN", orientation='h', title="📦 Top 10 productos", template="plotly_white"
    )
    fig_departamento = px.bar(
        dff.groupby("DESDEP")["VALOR"].sum().reset_index().query("VALOR > 100000").sort_values("VALOR", ascending=True),
        x="VALOR", y="DESDEP", orientation='h', title="🗺️ Valor exportado por departamento de origen", template="plotly_white"
    )

    # Daten vorbereiten
    df_treemap = dff.copy()
    df_treemap = df_treemap[df_treemap['VALOR'] > 0]

    # Schweizer Format als Textspalte
    df_treemap['VALOR_TXT'] = df_treemap['VALOR'].apply(lambda x: f"USD {x:,.0f}".replace(",", "'"))

    # Treemap erstellen mit 'VALOR_TXT' als customdata
    fig_treemap = px.treemap(
        df_treemap,
        path=['DESCIIU3', 'DESACT2', 'DESNAN'],
        values='VALOR',
        title="📂 Exportaciones por industria > actividad > producto",
        template="plotly_white",
        custom_data=['VALOR_TXT']
    )

    # Tooltip mit selbst formatierter Zahl (aus customdata[0])
    fig_treemap.update_traces(
        hovertemplate="<b>%{label}</b><br>%{customdata[0]}<extra></extra>"
    )



    for fig in [fig_pais, fig_producto, fig_departamento]:
        valores = [trace.x for trace in fig.data][0]
        labels = [f"{int(v):,}".replace(",", "'") for v in valores]
        fig.update_traces(customdata=labels)
        fig.update_traces(hovertemplate="%{y}<br>USD %{customdata}")

    return kpi_html, fig_pais, fig_producto, fig_departamento, fig_treemap


app = Dash(__name__)
server = app.server  # <- wichtig

if __name__ == '__main__':
    app.run(debug=True)

