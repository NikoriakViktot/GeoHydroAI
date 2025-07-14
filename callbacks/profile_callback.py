from dash import callback, Output, Input, State
import plotly.graph_objs as go
import dash_leaflet as dl
import pandas as pd
import duckdb

DEM_LIST = [
    "alos_dem", "aster_dem", "copernicus_dem", "fab_dem",
    "nasa_dem", "srtm_dem", "tan_dem"
]
YEARS = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
hand_column_map = {dem: f"{dem}_2000" for dem in DEM_LIST}


# --- Track/RGT/Spot Dropdown
@callback(
    Output("track_rgt_spot_dropdown", "options"),
    Output("track_rgt_spot_dropdown", "value"),
    Input("year_dropdown", "value"),
    State("selected_profile", "data"),
)
def update_tracks_dropdown(year, selected_profile):
    sql = f"""
        SELECT DISTINCT track, rgt, spot
        FROM 'data/tracks_3857_1.parquet'
        WHERE year = {year}
          AND atl03_cnf = 4 AND atl08_class = 1
        ORDER BY track, rgt, spot
    """
    try:
        df = duckdb.query(sql).to_df()
        options = [
            {"label": f"Track {row.track} / RGT {row.rgt} / Spot {row.spot}",
             "value": f"{row.track}_{row.rgt}_{row.spot}"}
            for _, row in df.iterrows()
        ]
        value = options[0]["value"] if options else None
        if selected_profile and selected_profile.get("track") in [o["value"] for o in options]:
            value = selected_profile["track"]
        return options, value
    except Exception:
        return [], None

# --- Date Dropdown
@callback(
    Output("date_dropdown", "options"),
    Output("date_dropdown", "value"),
    Input("track_rgt_spot_dropdown", "value"),
    State("selected_profile", "data"),
)
def update_dates_dropdown(track_rgt_spot, selected_profile):
    if not track_rgt_spot:
        return [], None
    track, rgt, spot = map(float, track_rgt_spot.split("_"))
    sql = f"""
        SELECT DISTINCT DATE(time) as date_only
        FROM 'data/tracks_3857_1.parquet'
        WHERE track={track} AND rgt={rgt} AND spot={spot}
            AND atl03_cnf = 4 AND atl08_class = 1
        ORDER BY date_only
    """
    try:
        df = duckdb.query(sql).to_df()
        options = [{
            "label": pd.to_datetime(row.date_only).strftime("%Y-%m-%d"),
            "value": pd.to_datetime(row.date_only).strftime("%Y-%m-%d")
        } for _, row in df.iterrows()]
        value = options[0]["value"] if options else None
        if selected_profile and selected_profile.get("date") in [o["value"] for o in options]:
            value = selected_profile["date"]
        return options, value
    except Exception:
        return [], None

# --- STORE: єдиний callback для синхронізації state/history
@callback(
    Output("selected_profile", "data"),
    Output("profile_history", "data"),
    Input("year_dropdown", "value"),
    Input("track_rgt_spot_dropdown", "value"),
    Input("dem_select", "value"),
    Input("date_dropdown", "value"),
    State("selected_profile", "data"),
    State("profile_history", "data"),
    prevent_initial_call=True
)
def sync_profile_to_store(year, track, dem, date, prev_profile, history):
    # Записуємо весь поточний профіль
    profile = {"year": year, "track": track, "dem": dem, "date": date}
    if not history:
        history = []
    if not prev_profile or prev_profile != profile:
        history.append(profile)
    return profile, history

# --- Побудова профілю (графік + stats)
def get_track_data_for_date(track, rgt, spot, dem, date, hand_range=None):
    hand_col = hand_column_map[dem]
    sql = f"""
        SELECT *
        FROM 'data/tracks_3857_1.parquet'
        WHERE track={track} AND rgt={rgt} AND spot={spot}
            AND DATE(time) = '{date}'
            AND delta_{dem} IS NOT NULL AND h_{dem} IS NOT NULL
            AND atl03_cnf = 4 AND atl08_class = 1
    """
    if hand_range and len(hand_range) == 2 and all(x is not None for x in hand_range):
        sql += f" AND {hand_col} IS NOT NULL AND {hand_col} BETWEEN {hand_range[0]} AND {hand_range[1]}"
    sql += " ORDER BY x"
    try:
        df = duckdb.query(sql).to_df()
        return df
    except Exception:
        return pd.DataFrame()

def get_dem_stats(df, dem_key):
    delta_col = f"delta_{dem_key}"
    if delta_col not in df:
        return None
    delta = df[delta_col].dropna()
    if delta.empty:
        return None
    return {
        "mean": delta.mean(),
        "min": delta.min(),
        "max": delta.max(),
        "count": len(delta)
    }

def build_profile_figure_with_hand(df_all, df_hand, dem_key, use_hand):
    fig = go.Figure()
    if not df_all.empty and f"h_{dem_key}" in df_all:
        x_axis_dem = df_all["distance_m"] if "distance_m" in df_all else df_all["x"]
        fig.add_trace(go.Scatter(
            x=x_axis_dem,
            y=df_all[f"h_{dem_key}"],
            mode="markers",
            marker=dict(size=2, color="lightgray"),
            name=f"{dem_key.upper()} DEM",
            opacity=0.9
        ))
    show_df = df_hand if (use_hand and not df_hand.empty) else df_all
    if not show_df.empty and "orthometric_height" in show_df:
        x_axis_ice = show_df["distance_m"] if "distance_m" in show_df else show_df["x"]
        fig.add_trace(go.Scatter(
            x=x_axis_ice,
            y=show_df["orthometric_height"],
            mode="markers",
            marker=dict(size=2, color="crimson"),
            name="ICESat-2 Orthometric Height",
            opacity=0.9
        ))
    if f"delta_{dem_key}" in df_all and not df_all[f"delta_{dem_key}"].dropna().empty:
        delta = df_all[f"delta_{dem_key}"].dropna()
        stats_text = (
            f"Похибка {dem_key.upper()}: "
            f"Сер: {delta.mean():.2f} м, "
            f"Мін: {delta.min():.2f} м, "
            f"Макс: {delta.max():.2f} м"
        )
        fig.add_annotation(
            text=stats_text,
            xref="paper", yref="paper",
            x=0.02, y=0.99,
            showarrow=False,
            font=dict(size=13, color="lightgray", family="monospace"),
            align="left",
            bordercolor="gray", borderwidth=1,
            xanchor="left"
        )
    fig.update_layout(
        xaxis=dict(title="Відстань/Longitude", gridcolor="#666", gridwidth=0.6, griddash="dot", zerolinecolor="#555"),
        yaxis=dict(title="Ортометрична висота (м)", gridcolor="#666", gridwidth=0.3, griddash="dot", zerolinecolor="#555"),
        height=600,
        legend=dict(orientation="h", y=1.06, x=0.5, xanchor="center", font=dict(size=12), bgcolor='rgba(0,0,0,0)'),
        plot_bgcolor="#20232A",
        paper_bgcolor="#181818",
        font_color="#EEE",
        margin=dict(l=70, r=50, t=40, b=40)
    )
    return fig

# --- Графік профілю
@callback(
    Output("track_profile_graph", "figure"),
    Output("dem_stats", "children"),
    Input("track_rgt_spot_dropdown", "value"),
    Input("dem_select", "value"),
    Input("date_dropdown", "value"),
    Input("hand_slider", "value"),
    Input("hand_toggle", "value"),
)
def update_profile(track_rgt_spot, dem, date, hand_range, hand_toggle):
    if not (track_rgt_spot and date and dem):
        fig = go.Figure()
        fig.update_layout(plot_bgcolor="#20232A", paper_bgcolor="#181818", font_color="#EEE", height=600)
        return fig, ""
    try:
        track, rgt, spot = map(float, track_rgt_spot.split("_"))
    except Exception:
        fig = go.Figure()
        fig.update_layout(plot_bgcolor="#20232A", paper_bgcolor="#181818", font_color="#EEE", height=600)
        return fig, ""
    use_hand = "on" in hand_toggle
    hand_range_for_query = hand_range if (use_hand and hand_range and len(hand_range) == 2 and all(isinstance(x, (int, float)) for x in hand_range)) else None
    df_hand = get_track_data_for_date(track, rgt, spot, dem, date, hand_range_for_query)
    df_all = get_track_data_for_date(track, rgt, spot, dem, date, None)
    fig = build_profile_figure_with_hand(df_all, df_hand, dem, use_hand)
    stats = get_dem_stats(df_all, dem)
    stats_text = (
        f"Mean error: {stats['mean']:.2f} м, "
        f"Min: {stats['min']:.2f} м, Max: {stats['max']:.2f} м, "
        f"Points: {stats['count']}" if stats else "No error stats"
    )
    return fig, stats_text

# --- Карта
@callback(
    Output("point_group", "children"),
    Input("selected_profile", "data"),
    Input("hand_slider", "value"),
    Input("hand_toggle", "value"),
)
def update_map_points(selected_profile, hand_range, hand_toggle):
    if not selected_profile or not all(selected_profile.values()):
        return []
    track_str = selected_profile["track"]
    dem = selected_profile["dem"]
    date = selected_profile["date"]
    try:
        track, rgt, spot = map(float, track_str.split("_"))
    except Exception:
        return []
    use_hand = "on" in hand_toggle
    hand_range_for_query = (
        hand_range
        if (use_hand and hand_range and len(hand_range) == 2 and all(isinstance(x, (int, float)) for x in hand_range))
        else None
    )
    df = get_track_data_for_date(track, rgt, spot, dem, date, hand_range_for_query)
    if df is None or df.empty:
        return []
    lon_col = "x"
    lat_col = "y"
    delta_col = f"delta_{dem}"
    ortho_col = "orthometric_height"

    def tooltip_text(row):
        delta_val = row[delta_col] if pd.notna(row[delta_col]) else "NaN"
        ortho_val = row[ortho_col] if ortho_col in row and pd.notna(row[ortho_col]) else "NaN"
        return (
            # f"ΔDEM: {delta_val:.2f} м."
            f"ICESat-2 (Ortho): {ortho_val:.2f} м."
        )

    markers = [
        dl.CircleMarker(
            center=[row[lat_col], row[lon_col]],
            radius=3,
            color="blue",
            fillColor="blue",
            fillOpacity=0.9,
            children=[dl.Tooltip(tooltip_text(row))],
        )
        for _, row in df.iterrows() if pd.notna(row[delta_col]) and pd.notna(row[ortho_col])
    ]
    if not df[delta_col].dropna().empty:
        min_idx = df[delta_col].idxmin()
        max_idx = df[delta_col].idxmax()
        row_min = df.loc[min_idx]
        row_max = df.loc[max_idx]
        markers.append(
            dl.CircleMarker(
                center=[row_min[lat_col], row_min[lon_col]],
                radius=7, color="lime", fillColor="lime", fillOpacity=1,
                children=[dl.Tooltip(f"Min ΔDEM: {row_min[delta_col]:.2f} м. ICESat-2: {row_min[ortho_col]:.2f} м.")]
            )
        )
        if min_idx != max_idx:
            markers.append(
                dl.CircleMarker(
                    center=[row_max[lat_col], row_max[lon_col]],
                    radius=7, color="red", fillColor="red", fillOpacity=1,
                    children=[dl.Tooltip(f"Max ΔDEM: {row_max[delta_col]:.2f} м. ICESat-2: {row_max[ortho_col]:.2f} м.")]
                )
            )
    return markers
