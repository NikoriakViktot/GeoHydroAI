import dash
from dash import html

dash.register_page(
    __name__,
    path="/tracks-map",
    name="Карти ICESat-2",
    title="GeoHydroAI | Карта ICESat-2",
    order=2
)

layout = html.Div([
    html.H2("Карта ICESat-2"),
    html.P("Тут буде інтерактивна карта."),
    # Інші компоненти...
])

