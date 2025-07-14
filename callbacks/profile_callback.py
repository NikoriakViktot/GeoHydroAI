#callbacks/profile_callback.py
# callbacks/profile_callback.py

import duckdb
from dash import Output, Input, callback
import plotly.graph_objs as go

from layout.tracks_map_tab import (
    get_track_data_for_date,
    build_profile_figure_with_hand,
    get_dem_stats,
)

@callback(
    Output("track_profile_graph", "figure"),
    Output("dem_stats", "children"),
    Input("track_rgt_spot_dropdown", "value"),
    Input("dem_dropdown", "value"),
    Input("date_dropdown", "value"),
    Input("hand_slider", "value"),
    Input("hand_filter_toggle", "value")
)
def update_profile_graph(track_rgt_spot, dem, date, hand_range, hand_filter_toggle):
    """
    Callback для окремого табу "Профіль" — тільки графік і статистика
    """
    # Якщо нічого не вибрано — повертаємо пусто
    if not (track_rgt_spot and date):
        return go.Figure(), ""

    # Розбиваємо трек на складові
    track, rgt, spot = map(float, track_rgt_spot.split("_"))
    use_hand = "on" in hand_filter_toggle
    hand_range_for_query = hand_range if (use_hand and hand_range and len(hand_range) == 2 and all(
        isinstance(x, (int, float)) for x in hand_range)) else None

    # Дані floodplain (HAND) і повний профіль для графіка
    df_hand = get_track_data_for_date(track, rgt, spot, dem, date, hand_range_for_query)
    df_all = get_track_data_for_date(track, rgt, spot, dem, date, None)
    fig = build_profile_figure_with_hand(df_all, df_hand, dem, use_hand)

    # Текст статистики (по всіх точках)
    stats = get_dem_stats(df_all, dem)
    stats_text = (
        f"Mean error: {stats['mean']:.2f} м, "
        f"Min: {stats['min']:.2f} м, Max: {stats['max']:.2f} м, "
        f"Points: {stats['count']}" if stats else "No error stats"
    )
    return fig, stats_text
