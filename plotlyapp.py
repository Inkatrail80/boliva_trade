from dash import Dash, dcc, html, Input, Output, State
import pandas as pd
import plotly.express as px
import os

# Daten laden
try:
    df_2023 = pd.read_excel("data/EXPORTACIONES_2023p.xlsx")
    df_2024 = pd.read_excel("data/EXPORTACIONES_2024p.xlsx")
except FileNotFoundError:
    df_2023 = df_2024 = pd.DataFrame()
    print("⚠️ Excel-Dateien nicht gefunden. Bitte prüfen.")

df = pd.concat([df_2023, df_2024], ignore_index=True)

# Spalten runden
for col in ['VALOR', 'KILNET']:
    if col in df.columns:
        df[col] = df[col].round(0)

def apply_standard_layout(fig):
    fig.update_layout(
        font=dict(family="Arial", size=16),
        title_font_size=30,
        margin=dict(l=50, r=50, t=50, b=50),
        xaxis_title="Valor exportado (USD)",
        yaxis_title=""
    )
    return fig

# Dash App initialisieren
app = Dash(__name__)
server = app.server

app.layout = html.Div([
    html.H1("BO 📦 Exportaciones Bolivianas – Dashboard"),

    html.Div([
        html.Label("Gestión:"),
        dcc.Dropdown(
            id='anio',
            options=[{"label": str(a), "value": a} for a in sorted(df['GESTION'].dropna().unique())],
            value=sorted(df['GESTION'].dropna().unique())[-1],
            optionHeight=50
        ),
        html.Label("Mes (opcional):"),
        dcc.Dropdown(
            id='mes',
            options=[{"label": "Todos", "value": "Todos"}] +
                    [{"label": str(m), "value": m} for m in sorted(df['MES'].dropna().unique())],
            value="Todos",
            optionHeight=50
        ),
        html.Label("País de destino:"),
        dcc.Dropdown(
            id='pais',
            options=[{"label": p, "value": p} for p in sorted(df['DESPAIS'].dropna().unique())],
            multi=True,
            optionHeight=50

        ),
        html.Label("DESCRIPCION CODIGO ARANCELARIO NANDINA:"),
        dcc.Dropdown(
            id='producto',
            options=[{"label": p, "value": p} for p in sorted(df['DESNAN'].dropna().unique())],
            multi=True,
            optionHeight=50
        ),
        html.Label("GRANDES CATEGORIAS ECONÓMICAS:"),
        dcc.Dropdown(
            id='categoria',
            options=[{"label": c, "value": c} for c in sorted(df['DESGCE3'].dropna().unique())],
            multi=True,
            optionHeight=50

        ),
        html.Label("CLASIFICACIÓN INDUSTRIAL INTERNACIONAL:"),
        dcc.Dropdown(
            id='industria',
            options=[{"label": i, "value": i} for i in sorted(df['DESCIIU3'].dropna().unique())],
            multi=True,
            optionHeight=50
        ),
        html.Label("PRODUCTO DE LA ACTIVIDAD ECONÓMICA:"),
        dcc.Dropdown(
            id='actividad',
            options=[{"label": a, "value": a} for a in sorted(df['DESACT2'].dropna().unique())],
            multi=True,
            optionHeight=50
        ),
        html.Label("Departamento de origen:"),
        dcc.Dropdown(
            id='departamento',
            options=[{"label": d, "value": d} for d in sorted(df['DESDEP'].dropna().unique())],
            multi=True,
            optionHeight=50
        )
    ], className="filter-panel"),

    html.Div([
        html.Div(id='kpis'),
        dcc.Graph(id='grafico-departamento', clear_on_unhover=True),
        dcc.Graph(id='grafico-pais', clear_on_unhover=True),
        dcc.Graph(id='grafico-producto', clear_on_unhover=True),
        dcc.Graph(id='grafico-treemap', clear_on_unhover=True)
    ], className="output-panel")
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
        return f"{value:,.0f}".replace(",", "'")

    kpi_html = html.Div([
        html.H4("Departamentos seleccionados: " + ", ".join(departamentos) if departamentos else "Todos los departamentos"),
        html.H4(f"Valor Total USD: {chf_format(total_valor)}"),
        html.H4(f"Peso Neto Total: {chf_format(total_peso)} kg")
    ])

    fig_pais = px.bar(
        dff.groupby("DESPAIS")["VALOR"].sum().reset_index().query("VALOR > 0").sort_values("VALOR", ascending=False).head(15).sort_values("VALOR", ascending=True),
        x="VALOR", y="DESPAIS", orientation='h', title="🌍 top 15 paises de destino", template="plotly_white"
    )
    apply_standard_layout(fig_pais)

    fig_producto = px.bar(
        dff.groupby("DESACT2")["VALOR"].sum().reset_index().query("VALOR > 0").sort_values("VALOR", ascending=False).head(15).sort_values("VALOR", ascending=True),
        x="VALOR", y="DESACT2", orientation='h', title="📦 Top 15 productos", template="plotly_white"
    )
    apply_standard_layout(fig_producto)

    fig_departamento = px.bar(
        dff.groupby("DESDEP")["VALOR"].sum().reset_index().query("VALOR > 0").sort_values("VALOR", ascending=True),
        x="VALOR", y="DESDEP", orientation='h', title="🗺️ Valor exportado por departamento de origen", template="plotly_white"
    )
    apply_standard_layout(fig_departamento)


    # Daten vorbereiten
    df_treemap = dff.copy()
    df_treemap = df_treemap[df_treemap['VALOR'] > 0]
    
    # Treemap erstellen mit 'VALOR_TXT' als customdata
    fig_treemap = px.treemap(
        df_treemap,
        path=['DESCIIU3', 'DESNAN', 'DESACT2'],
        values='VALOR',
        title="📂 Exportaciones",
        custom_data=['VALOR_TXT']
    )

    return kpi_html, fig_pais, fig_producto, fig_departamento, fig_treemap

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8050))
    app.run(host='0.0.0.0', port=port, debug=False)
