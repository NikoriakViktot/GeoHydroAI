import dash
from dash import html
from layout.sidebar import sidebar
from layout.tabs_content import content

external_stylesheets = [
    "https://cdn.jsdelivr.net/npm/bootswatch@5.1.3/dist/darkly/bootstrap.min.css"
]
from callbacks.main_callbacks import *

app = dash.Dash(__name__, external_stylesheets=external_stylesheets, use_pages=True)

app.title = "GeoHydroAI | DEM OLAP"
app.layout = html.Div([
    sidebar,       # ← ліворуч
    content        # ← праворуч (з вкладками)
],
dcc.Link("Dashboard", href="/"),
" | ",
dcc.Link("Карти ICESat-2", href="/tracks-map"),
dash.page_container
)
server = app.server  # для Render, Heroku тощо

if __name__ == "__main__":
    app.run(debug=True)
