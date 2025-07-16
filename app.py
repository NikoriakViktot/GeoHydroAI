import dash
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from dash import html, dcc
from layout.sidebar import sidebar
from init_tc_server import tile_server
print(type(tile_server))

external_stylesheets = [
    "https://cdn.jsdelivr.net/npm/bootswatch@5.1.3/dist/darkly/bootstrap.min.css"
]

# 1. Створюємо app
app = dash.Dash(__name__,
                external_stylesheets=external_stylesheets,
                use_pages=True,
                suppress_callback_exceptions=True)

# 2. Після створення — підключаємо tile_server
app.title = "GeoHydroAI | DEM OLAP"
server = app.server
application = DispatcherMiddleware(server, {
    '/tc': tile_server
})

# 3. Зареєструвати Blueprint

app.layout = html.Div([
    sidebar,
    html.Div([
        html.Div([
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

# 4. Запуск
if __name__ == '__main__':
    from werkzeug.serving import run_simple
    run_simple('0.0.0.0', 8050, application, use_reloader=True, use_debugger=True)