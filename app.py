import dash
from dash import html, dcc
from layout.sidebar import sidebar

external_stylesheets = [
    "https://cdn.jsdelivr.net/npm/bootswatch@5.1.3/dist/darkly/bootstrap.min.css"
]

app = dash.Dash(__name__,
                external_stylesheets=external_stylesheets,
                use_pages=True,
                suppress_callback_exceptions=True)
app.title = "GeoHydroAI | DEM OLAP"
server = app.server

app.layout = html.Div([
    sidebar,
    html.Div([
        html.Div([  # Навігація
            dcc.Link("Dashboard", href="/", style={"color": "#00bfff", "marginRight": "24px"}),
            dcc.Link("Карти ICESat-2", href="/tracks-map", style={"color": "#00bfff"}),
        ], style={"padding": "20px 0"}),

        dash.page_container,
    ],
    style={
        "marginLeft": "300px",
        "padding": "0 30px 24px 30px",
        "backgroundColor": "#181818",
        "minHeight": "100vh"
    })
])


if __name__ == "__main__":
    app.run(debug=True)
