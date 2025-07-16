# pages/tracks_map.py
import dash
from dash import html, dcc
from dash import callback

import dash_leaflet as dl
import json
import geopandas as gpd
from dash.dependencies import Input, Output


dash.register_page(
    __name__,
    path="/tracks-map",
    name="Карти ICESat-2",
    title="GeoHydroAI | Карта ICESat-2",
    order=2
)


# Читання шару басейну (GeoJSON)
basin = gpd.read_file("data/basin_bil_cher_4326.gpkg")
basin = basin.to_crs("EPSG:4326")
basin = json.loads(basin.to_json())
# Список colormap
colormaps = ["viridis", "terrain", "inferno", "jet", "spectral", "rainbow"]

layout = html.Div([
    dcc.Dropdown(
        id="colormap-dropdown",
        options=[{"label": c, "value": c} for c in colormaps],
        value="viridis"
    ),
    dl.Map([
        dl.TileLayer(),
        dl.GeoJSON(
            data=basin,
            id="basin",
            options={
                "style": {
                    "color": "blue",
                    "weight": 2,
                    "fill": False,

                    # "fillOpacity": 0        # Зробити заливку прозорою
                }
            }
        ),        dl.TileLayer(
            id="dem-tile",
            opacity=0.7
        )
    ], style={'width': '100%', 'height': '700px'}, center=[47.8, 25.03], zoom=10)
])

@callback(
    Output("dem-tile", "url"),
    Input("colormap-dropdown", "value")
)
def update_tile_url(colormap):
    # Тут можна підлаштувати stretch_range
    stretch = "[0,2200]"
    return  f"/tc/singleband/dem/fab_dem/{{z}}/{{x}}/{{y}}.png?colormap={colormap}&stretch_range={stretch}"



