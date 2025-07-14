import dash
from dash import html, dcc, Output, Input, callback, dash_table
import duckdb
import json
import geopandas as gpd
import plotly.graph_objs as go
import pandas as pd
import dash_leaflet as dl

dash.register_page(__name__, path="/tracks-map")

YEARS = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
DEM_LIST = [
    "alos_dem", "aster_dem", "copernicus_dem", "fab_dem",
    "nasa_dem", "srtm_dem", "tan_dem"
]
hand_column_map = {dem: f"{dem}_2000" for dem in DEM_LIST}
# -------- DARK THEME UTILS ----------

layout = html.Div([
    html.H3(
        "ICESat-2 Tracks Map & Time Series (Ground Only, with HAND filter)",
        style={"color": "#EEEEEE"}
    ),
    # --- Фільтри ---
    html.Div([
        dcc.Dropdown(
            id="year_dropdown",
            options=[{"label": str(y), "value": y} for y in YEARS],
            value=YEARS[-1], clearable=False,
            style={**dark_dropdown_style, "width": "100px", "display": "inline-block"}
        ),
        dcc.Dropdown(
            id="dem_dropdown",
            options=[{"label": d.upper(), "value": d} for d in DEM_LIST],
            value=DEM_LIST[0], clearable=False,
            style={**dark_dropdown_style, "width": "130px", "display": "inline-block", "marginLeft": "8px"}
        ),
        dcc.Dropdown(
            id="track_rgt_spot_dropdown",
            clearable=False,
            style={**dark_dropdown_style, "width": "350px", "display": "inline-block", "marginLeft": "8px"}
        ),
        dcc.Dropdown(
            id="date_dropdown",
            clearable=False,
            style={**dark_dropdown_style, "width": "160px", "display": "inline-block", "marginLeft": "8px"}
        ),
        html.Div([
            html.Label("HAND (Height Above Nearest Drainage), м:", style={"color": "#EEEEEE"}),
            dcc.Checklist(
                id="hand_filter_toggle",
                options=[{"label": "Фільтрувати по HAND (floodplain)", "value": "on"}],
                value=["on"],
                style={"margin": "8px 0 4px 0", "color": "#EEEEEE"}
            ),
            dcc.RangeSlider(
                id="hand_slider", min=0, max=20, step=1, value=[0, 5],
                marks={i: str(i) for i in range(0, 21, 5)},
                tooltip={"placement": "bottom", "always_visible": True}
            ),
        ], style={"width": "350px", "marginTop": "8px"}),
    ], style={"marginBottom": "12px", "width": "100%"}),

    html.Div([
        html.Span("Легенда: ", style={"fontWeight": "bold", "color": "#EEE"}),
        html.Span("• ", style={"color": "blue", "fontWeight": "bold"}),
        html.Span("Всі точки | "),
        html.Span("• ", style={"color": "lime", "fontWeight": "bold"}),
        html.Span("Min | "),
        html.Span("• ", style={"color": "red", "fontWeight": "bold"}),
        html.Span("Max", style={}),
    ], style={
        "marginBottom": "10px",
        "fontSize": "16px",
        "letterSpacing": "0.04em",
        "background": "#222",
        "padding": "8px 14px",
        "borderRadius": "10px",
        "display": "inline-block"
    }),

    # --- Головний flex ряд (side by side) ---
    html.Div([
        # --- Карта ---
        dl.Map(
            [
                dl.TileLayer(url="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
                             attribution="© OpenTopoMap contributors"),
                dl.LayerGroup(id="point_group"),
                dl.GeoJSON(data=basin, id="basin", options={"style": {"color": "blue", "weight": 2}})
            ],
            style={
                "height": "520px",
                "width": "100%",
                "minWidth": "350px",
                "flex": "0.6",
                "marginTop": "32px",
            },
            center=[47.8, 25.03], zoom=10, id="leaflet_map"
        ),

        # --- Графік + статистика ---
        html.Div([
            dcc.Graph(
                id="track_profile_graph",
                style={"height": "520px", "width": "100%", "minWidth": "650px", "flex": "2.4"}
            ),
            html.Div(
                id="dem_stats",
                style={**dark_card_style, "marginTop": "14px", "width": "98%", "fontSize": "15px"}
            ),
        ], style={
            "display": "flex",
            "flexDirection": "column",
            "alignItems": "center",
            "width": "100%",
            "flex": "1"
        }),
    ], style={
        "display": "flex",
        "flexDirection": "row",
        "alignItems": "flex-start",  # <-- важливо для вирівнювання по верхньому краю!
        "gap": "16px",
        "width": "100%",
        "justifyContent": "center"
    }),

    # --- Time series внизу ---
    html.Div([
        dcc.Graph(id="time_series_graph", style={"height": "220px", "width": "70vw"})
    ], style={
        "display": "flex",
        "justifyContent": "center",
        "marginTop": "24px",
        "width": "100%"
    })
], style={
    "backgroundColor": "#181818",
    "color": "#EEEEEE",
    "minHeight": "100vh",
    "paddingBottom": "20px",
    "width": "100vw",
    "boxSizing": "border-box"
})



# Читання шару басейну (GeoJSON)
basin = gpd.read_file("data/basin_bil_cher_4326.gpkg", crs=4326)
basin = json.loads(basin.to_json())

def duckdb_query(sql):
    try:
        df = duckdb.query(sql).to_df()
        return df
    except Exception as e:
        return pd.DataFrame()

def clean_df_for_table(df):
    if df.empty:
        return df
    drop_cols = []
    for col in df.columns:
        if df[col].dtype == "object":
            s = df[col].dropna()
            if not s.empty:
                first_val = s.iloc[0]
                if isinstance(first_val, (dict, list, tuple, bytes)) or hasattr(first_val, "__array__"):
                    drop_cols.append(col)
            else:
                drop_cols.append(col)
    if "geometry_bbox" in df.columns:
        drop_cols.append("geometry_bbox")
    return df.drop(columns=list(set(drop_cols)), errors="ignore")

def get_unique_tracks(year):
    sql = f"""
        SELECT DISTINCT track, rgt, spot
        FROM 'data/tracks_3857_1.parquet'
        WHERE year = {year}
          AND atl03_cnf = 4 AND atl08_class = 1
        ORDER BY track, rgt, spot
    """
    return duckdb_query(sql)

def get_time_series(track, rgt, spot, dem):
    sql = f"""
        SELECT DATE(time) as date_only, AVG(abs_delta_{dem}) as mean_abs_error
        FROM 'data/tracks_3857_1.parquet'
        WHERE track={track} AND rgt={rgt} AND spot={spot}
          AND atl03_cnf = 4 AND atl08_class = 1
        GROUP BY date_only ORDER BY date_only
    """
    return duckdb_query(sql)

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
    return duckdb_query(sql)

def get_geojson_for_date(track, rgt, spot, dem, date, hand_range=None, step=10):
    hand_col = hand_column_map[dem]
    sql = f"""
        SELECT x, y, delta_{dem}, abs_delta_{dem}
        FROM 'data/tracks_3857_1.parquet'
        WHERE track={track} AND rgt={rgt} AND spot={spot}
            AND DATE(time) = '{date}'
            AND atl03_cnf = 4 AND atl08_class = 1
    """
    if hand_range and len(hand_range) == 2 and all(x is not None for x in hand_range):
        sql += f" AND {hand_col} IS NOT NULL AND {hand_col} BETWEEN {hand_range[0]} AND {hand_range[1]}"
    df = duckdb_query(sql)
    if df.empty:
        return {"type": "FeatureCollection", "features": []}
    # ↓↓↓ Візьми тільки кожну N-ту точку ↓↓↓
    df = df.iloc[::step]   # step=10 by default
    features = [
        {
            "type": "Feature",
            "properties": {
                "delta": float(r.get(f"delta_{dem}")),
                "abs_delta": float(r.get(f"abs_delta_{dem}"))
            },
            "geometry": {
                "type": "Point",
                "coordinates": [float(r.x), float(r.y)]  # [lon, lat]
            }
        }
        for _, r in df.iterrows()
    ]
    return {"type": "FeatureCollection", "features": features}



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
    # 1. Профіль DEM по всьому треку
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

    # 2. ICESat-2 ортометрична висота (всі точки, або floodplain, якщо вибрано HAND)
    # Якщо включено фільтр HAND — показати тільки floodplain
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

    # 3. Статистика DEM (по всіх точках — не тільки floodplain!)
    stats_text = ""
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
        # title="Профіль треку: все vs floodplain",
        xaxis=dict(
            title="Відстань/Longitude",
            gridcolor="#666",  # Сіра сітка
            gridwidth=0.6,  # Товщина ліній сітки
            griddash="dot",  # Пунктирна сітка
            zerolinecolor="#555",  # Колір осі X
        ),
        yaxis=dict(
            title="Ортометрична висота (м)",
            gridcolor="#666",  # Сіра сітка
            gridwidth=0.3,  # Товщина ліній сітки
            griddash="dot",  # Пунктирна сітка
            zerolinecolor="#555",  # Колір осі Y
        ),
        height=600,
        legend=dict(
            orientation="h",
            y=1.06,
            x=0.5,
            xanchor="center",
            font=dict(size=12),
            bgcolor='rgba(0,0,0,0)'
        ),
        plot_bgcolor="#20232A",
        paper_bgcolor="#181818",
        font_color="#EEE",
        margin=dict(l=70, r=30, t=10, b=50)
    )
    return fig


# CALLBACKS

@callback(
    Output("track_rgt_spot_dropdown", "options"),
    Output("track_rgt_spot_dropdown", "value"),
    Input("year_dropdown", "value"),
)
def update_tracks_dropdown(year):
    tracks_df = get_unique_tracks(year)
    options = [
        {"label": f"Track {row.track} / RGT {row.rgt} / Spot {row.spot}", "value": f"{row.track}_{row.rgt}_{row.spot}"}
        for _, row in tracks_df.iterrows()
    ]
    value = options[0]["value"] if options else None
    return options, value


@callback(
    Output("time_series_graph", "figure"),
    Output("date_dropdown", "options"),
    Output("date_dropdown", "value"),
    Input("track_rgt_spot_dropdown", "value"),
    Input("dem_dropdown", "value")

)
def update_time_series(track_rgt_spot, dem):
    if not track_rgt_spot:
        return go.Figure(), [], None
    track, rgt, spot = map(float, track_rgt_spot.split("_"))
    ts_df = get_time_series(track, rgt, spot, dem)
    # Перетворюємо на строку формату "YYYY-MM-DD"
    date_options = [{"label": d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d),
                     "value": d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)}
                    for d in ts_df['date_only']]
    value = date_options[0]["value"] if date_options else None
    fig = go.Figure()
    if not ts_df.empty:
        fig.add_trace(go.Bar(
            x=[d["label"] for d in date_options],
            y=ts_df['mean_abs_error'],
            name=f"Mean Abs Error ({dem})",
            marker_color="cornflowerblue"
        ))
    fig.update_layout(
        # title="Time Series: Mean Abs Error per Date",
        xaxis_title="Date", yaxis_title="Mean Abs Error (m)"
    )
    fig = apply_dark_theme(fig)
    return fig, date_options, value


@callback(
    Output("point_group", "children"),
    Output("track_profile_graph", "figure"),
    Output("dem_stats", "children"),
    Input("track_rgt_spot_dropdown", "value"),
    Input("dem_dropdown", "value"),
    Input("date_dropdown", "value"),
    Input("hand_slider", "value"),
    Input("hand_filter_toggle", "value")
)
def update_map_and_table(track_rgt_spot, dem, date, hand_range, hand_filter_toggle):
    # Якщо нічого не вибрано — повертаємо пусті значення для всіх Output
    if not (track_rgt_spot and date):
        return [], go.Figure(), ""

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

    # Дані для карти (geojson)
    geojson = get_geojson_for_date(track, rgt, spot, dem, date, hand_range_for_query, step=50)
    features = geojson["features"]

    # Якщо точок немає — повертаємо пусто
    if not features:
        return [], fig, stats_text

    # Тільки валідні точки з delta
    valid_features = [(i, f) for i, f in enumerate(features) if f["properties"]["delta"] is not None]
    if not valid_features:
        return [], fig, stats_text

    deltas = [f["properties"]["delta"] for i, f in valid_features]
    min_val = min(deltas)
    max_val = max(deltas)
    min_idx = valid_features[deltas.index(min_val)][0]
    max_idx = valid_features[deltas.index(max_val)][0]

    # Малюємо всі CircleMarker окрім min/max окремо
    pts = [
        dl.CircleMarker(
            center=[feat["geometry"]["coordinates"][1], feat["geometry"]["coordinates"][0]],
            radius=2,
            color="blue", fillColor="blue", fillOpacity=0.8,
            children=[dl.Tooltip(f"{feat['properties']['delta']:.2f} м")]
        )
        for i, feat in enumerate(features) if i not in [min_idx, max_idx]
    ]
    feat_min = features[min_idx]
    feat_max = features[max_idx]
    if min_idx != max_idx:
        pts.append(
            dl.CircleMarker(
                center=[feat_min["geometry"]["coordinates"][1], feat_min["geometry"]["coordinates"][0]],
                radius=5, color="lime", fillColor="lime", fillOpacity=1,
                children=[dl.Tooltip(f"Min: {feat_min['properties']['delta']:.2f} м")]
            )
        )
        pts.append(
            dl.CircleMarker(
                center=[feat_max["geometry"]["coordinates"][1], feat_max["geometry"]["coordinates"][0]],
                radius=5, color="red", fillColor="red", fillOpacity=1,
                children=[dl.Tooltip(f"Max: {feat_max['properties']['delta']:.2f} м")]
            )
        )
    else:
        pts.append(
            dl.CircleMarker(
                center=[feat_min["geometry"]["coordinates"][1], feat_min["geometry"]["coordinates"][0]],
                radius=5, color="cyan", fillColor="cyan", fillOpacity=1,
                children=[dl.Tooltip(f"Point: {feat_min['properties']['delta']:.2f} м")]
            )
        )

    # Повертаємо три значення у правильному порядку!
    return pts, fig, stats_text


