from dash import Input, Output, State, callback_context
from utils.db import DuckDBData

db = DuckDBData("data/tracks_3857_1.parquet")

@callback(
    Output("tab-content", "children"),
    Input("apply_filters_btn", "n_clicks"),
    State("dem_select", "value"),
    State("lulc_select", "value"),
    State("landform_select", "value"),
    State("slope_slider", "value"),
    State("hand_toggle", "value"),
    State("hand_slider", "value"),
    # ... State для інших фільтрів
    State("tabs", "value")
)
def update_dashboard(n_clicks, dem, lulc, landform, slope, hand_toggle, hand_range, tab):
    if n_clicks is None:
        raise dash.exceptions.PreventUpdate

    # --- Формуємо параметри для класу ---
    hand_range_ = hand_range if "on" in hand_toggle else None

    # Тут збираємо ВСІ доступні зрізи (додаєш stream_range, twi_range, якщо треба)
    df = db.get_filtered_data(
        dem=dem,
        slope_range=slope,
        hand_range=hand_range_,
        lulc=lulc,
        landform=landform
    )
    # --- В залежності від вкладки повертаємо різний контент ---
    if tab == "tab-1":
        return build_dem_comparison_plot(df)
    elif tab == "tab-2":
        return build_profile(df)
    elif tab == "tab-3":
        return build_map(df)
    elif tab == "tab-4":
        return build_table(df)
    else:
        return html.Div("Невідома вкладка")
