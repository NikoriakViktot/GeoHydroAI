from dash import html, dcc
from utils.style import dark_card_style, dropdown_style

YEARS = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]

profile_tab_layout = html.Div([
    html.H4("Профіль ICESat-2 треку", style={"color": "#EEEEEE"}),

    # Фільтри профілю треку (Рік, трек, дата)
    html.Div([
        dcc.Dropdown(
            id="year_dropdown",
            options=[{"label": str(y), "value": y} for y in YEARS],
            value=YEARS[-1], clearable=False,
            style={**dropdown_style, "width": "110px", "display": "inline-block"}
        ),
        dcc.Dropdown(
            id="track_rgt_spot_dropdown",
            options=[],  # генерується callback-ом по року!
            style={**dropdown_style, "width": "300px", "display": "inline-block", "marginLeft": "8px"}
        ),
        dcc.Dropdown(
            id="date_dropdown",
            options=[],  # генерується callback-ом по треку!
            style={**dropdown_style, "width": "150px", "display": "inline-block", "marginLeft": "8px"}
        ),
    ], style={"marginBottom": "12px"}),

    # Графік профілю
    dcc.Graph(
        id="track_profile_graph",
        style={
            "height": "540px",
            "width": "100%",
            "minWidth": "650px",
            "marginBottom": "36px"
        }
    ),

    # Статистика DEM
    html.Div([
        html.Div(
            id="dem_stats",
            style={
                **dark_card_style,
                "marginTop": "40px",
                "fontSize": "15px",
                "display": "inline-flex",
                "width": "fit-content",
                "maxWidth": "600px",
            }
        )
    ], style={"display": "flex", "justifyContent": "center"}),



], style={
    "backgroundColor": "#181818",
    "color": "#EEEEEE",
    "minHeight": "480px",
    "padding": "18px 12px 32px 12px",
})

# # Кнопка "Перейти до карти"
# html.Div([
#     html.Button(
#         "🗺️ Перейти до карти",
#         id="go_to_map_btn",
#         n_clicks=0,
#         style={
#             "marginTop": "36px",
#             "fontSize": "17px",
#             "background": "#253152",
#             "color": "#B9E0FF",
#             "border": "none",
#             "borderRadius": "12px",
#             "padding": "12px 28px",
#             "fontWeight": "bold",
#             "cursor": "pointer",
#             "boxShadow": "0 2px 8px #10161a33"
#         }
#     )
# ], style={"display": "flex", "justifyContent": "center"}),