import dash
from dash import html, dcc
from utils.style import dark_card_style

# Не треба register_page тут, якщо це імпортується у головний layout — тільки для сторінок у Dash Pages.

profile_tab_layout = html.Div([
    html.H4("Профіль ICESat-2 треку", style={"color": "#EEEEEE"}),
    dcc.Graph(
        id="track_profile_graph",
        style={"height": "540px", "width": "100%", "minWidth": "650px"}
    ),
    html.Div(
        id="dem_stats",
        style={**dark_card_style, "marginTop": "20px", "width": "100%", "fontSize": "15px"}
    )
], style={
    "backgroundColor": "#181818",
    "color": "#EEEEEE",
    "minHeight": "480px",
    "padding": "18px 12px 32px 12px",
})
