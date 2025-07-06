import plotly.express as px
import plotly.graph_objs as go
from dash import Dash, dcc, html, Input, Output, dash_table

parquet_file = "data/icesat2_dem_filtered_fixed_1.parquet"
dem_list = [
    "alos_dem", "aster_dem", "copernicus_dem", "fab_dem",
    "nasa_dem", "srtm_dem", "tan_dem"
]
hand_column_map = {dem: f"{dem}_2000" for dem in dem_list}

def duckdb_query(sql):
    import duckdb
    con = duckdb.connect()
    try:
        return con.execute(sql).fetchdf()
    finally:
        con.close()

def get_unique_lulc_names(parquet_file, dem):
    sql = f"SELECT DISTINCT lulc_name FROM '{parquet_file}' WHERE delta_{dem} IS NOT NULL AND lulc_name IS NOT NULL ORDER BY lulc_name"
    try:
        df = duckdb_query(sql)
        return [{"label": x, "value": x} for x in df["lulc_name"].dropna().tolist()]
    except Exception:
        return []

def get_unique_landform(parquet_file, dem):
    sql = f"SELECT DISTINCT {dem}_landform FROM '{parquet_file}' WHERE {dem}_landform IS NOT NULL ORDER BY {dem}_landform"
    try:
        df = duckdb_query(sql)
        return [{"label": x, "value": x} for x in df[f"{dem}_landform"].dropna().tolist()]
    except Exception:
        return []

app = Dash(__name__)
app.layout = html.Div([
    html.H3("DEM error dashboard + Floodplain (HAND) analysis"),
    dcc.Dropdown(id="dem_select", options=[{'label': dem, 'value': dem} for dem in dem_list], value="alos_dem"),
    dcc.Dropdown(id="lulc_select", multi=True, placeholder="LULC class"),
    dcc.Dropdown(id="landform_select", multi=True, placeholder="Landform class"),
    html.Div([
        html.Label("Похил (Slope), градуси:"),
        dcc.RangeSlider(
            id="slope_slider", min=0, max=45, step=1, value=[0, 45],
            marks={i: str(i) for i in range(0, 46, 10)}
        ),
    ], style={"margin": "10px 0 2px 0"}),
    dcc.Checklist(
        id="hand_filter_toggle",
        options=[{"label": "Фільтрувати по HAND (floodplain)", "value": "on"}],
        value=["on"],
        style={"margin": "8px 0 4px 0"}
    ),
    dcc.RangeSlider(
        id="hand_slider", min=0, max=20, step=1, value=[0, 5],
        marks={i: str(i) for i in range(0, 21, 5)},
        tooltip={"placement": "bottom", "always_visible": True}
    ),
    # --- Два графіки поруч ---
    html.Div([
        dcc.Graph(id="error_plot", style={"height": "380px", "width": "48%"}),
        dcc.Graph(id="dem_stats_bar", style={"height": "380px", "width": "48%"}),
    ], style={
        "display": "flex", "flexDirection": "row",
        "justifyContent": "space-between",
        "alignItems": "flex-start",
        "gap": "16px",
        "marginTop": "12px"
    }),
    html.Div(id="stats_output"),
    # --- Дві таблиці поруч (HAND vs всі дані) ---
    html.Div([
        html.Div([
            html.H4("Таблиця статистики по всіх DEM у floodplain (HAND)"),
            dash_table.DataTable(
                id="dem_stats_table",
                style_table={"overflowX": "auto", "maxWidth": "540px", "minWidth": "340px"},
                style_cell={
                    "fontFamily": "Segoe UI, Verdana, Arial, sans-serif",
                    "fontSize": "15px",
                    "textAlign": "center",
                    "padding": "5px",
                },
                style_header={
                    "backgroundColor": "#e9ecef",
                    "fontWeight": "bold",
                    "fontSize": "16px"
                },
                style_data_conditional=[
                    {
                        "if": {"row_index": 0},
                        "backgroundColor": "#d1e7dd",
                        "fontWeight": "bold",
                    }
                ],
            ),
        ], style={"flex": "1", "marginRight": "20px"}),
        html.Div([
            html.H4("Таблиця по всій території"),
            dash_table.DataTable(
                id="dem_stats_table_all",
                style_table={"overflowX": "auto", "maxWidth": "540px", "minWidth": "340px"},
                style_cell={
                    "fontFamily": "Segoe UI, Verdana, Arial, sans-serif",
                    "fontSize": "15px",
                    "textAlign": "center",
                    "padding": "5px",
                },
                style_header={
                    "backgroundColor": "#e9ecef",
                    "fontWeight": "bold",
                    "fontSize": "16px"
                },
                style_data_conditional=[
                    {
                        "if": {"row_index": 0},
                        "backgroundColor": "#d1e7dd",
                        "fontWeight": "bold",
                    }
                ],
            ),
        ], style={"flex": "1"}),
    ], style={
        "display": "flex", "flexDirection": "row",
        "justifyContent": "center", "alignItems": "flex-start",
        "gap": "28px", "marginTop": "12px",
        "backgroundColor": "#f5f5f5",  # колір самої "картки"

    }),
], style={"maxWidth": "1200px",
          "margin": "auto",
          "backgroundColor": "#f1f3f4"
          })


@app.callback(
    Output("hand_slider", "disabled"),
    Input("hand_filter_toggle", "value")
)
def toggle_hand_slider(hand_filter_toggle):
    return "on" not in hand_filter_toggle


@app.callback(
    Output("lulc_select", "options"),
    Output("landform_select", "options"),
    Input("dem_select", "value"),
)
def update_dropdowns(dem):
    lulc_options = get_unique_lulc_names(parquet_file, dem)
    landform_options = get_unique_landform(parquet_file, dem)
    return lulc_options, landform_options

@app.callback(
    Output("error_plot", "figure"),
    Output("stats_output", "children"),
    Output("dem_stats_table", "data"),
    Output("dem_stats_table", "columns"),
    Output("dem_stats_table_all", "data"),
    Output("dem_stats_table_all", "columns"),
    Output("dem_stats_bar", "figure"),
    Input("dem_select", "value"),
    Input("lulc_select", "value"),
    Input("landform_select", "value"),
    Input("slope_slider", "value"),
    Input("hand_slider", "value"),
    Input("hand_filter_toggle", "value")
)
def update_graph(dem, lulc, landform, slope_range, hand_range, hand_filter_toggle):
    hand_col = hand_column_map.get(dem)
    use_hand = "on" in hand_filter_toggle

    sql_all = f"SELECT delta_{dem}, {hand_col} FROM '{parquet_file}' WHERE delta_{dem} IS NOT NULL"
    if slope_range != [0, 45]:
        sql_all += f" AND {dem}_slope BETWEEN {slope_range[0]} AND {slope_range[1]}"
    if lulc:
        lulc_str = ','.join([f"'{x}'" for x in lulc])
        sql_all += f" AND lulc_name IN ({lulc_str})"
    if landform:
        landform_str = ','.join([f"'{x}'" for x in landform])
        sql_all += f" AND {dem}_landform IN ({landform_str})"
    if hand_col and use_hand:
        sql_all += f" AND {hand_col} BETWEEN {hand_range[0]} AND {hand_range[1]}"
    dff_all = duckdb_query(sql_all)
    N = len(dff_all)
    if N == 0:
        return {}, "<b>No data for selection</b>", [], [], go.Figure()
    base_delta = dff_all[f"delta_{dem}"]
    base_rms = (base_delta ** 2).mean() ** 0.5
    base_mae = base_delta.abs().mean()
    base_bias = base_delta.mean()
    base_stats = f"ALL: {N} точок | RMS: {base_rms:.2f} | MAE: {base_mae:.2f} | Bias: {base_bias:.2f}"
    dff_plot = dff_all if N <= 20000 else dff_all.sample(n=20000, random_state=42)
    fig = px.box(
        dff_plot,
        y=f"delta_{dem}",
        points="all",
        title=f"Error for {dem} (Sampled {len(dff_plot)} of {N})" +
              (f"<br>HAND: {hand_range[0]}–{hand_range[1]} м" if use_hand else " (всі точки)")
    )

    dem_stats_hand = []
    for d in dem_list:
        hand = hand_column_map[d]
        sql = f"SELECT delta_{d} FROM '{parquet_file}' WHERE delta_{d} IS NOT NULL AND {hand} BETWEEN {hand_range[0]} AND {hand_range[1]}"
        df = duckdb_query(sql)
        vals = df[f"delta_{d}"].dropna()
        if len(vals) == 0:
            continue
        dem_stats_hand.append({
            "DEM": d,
            "N_points": len(vals),
            "MAE": round(vals.abs().mean(), 3),
            "RMSE": round((vals ** 2).mean() ** 0.5, 3),
            "Bias": round(vals.mean(), 3),
        })

    # --- ВСІ дані ---
    dem_stats_all = []
    for d in dem_list:
        sql = f"SELECT delta_{d} FROM '{parquet_file}' WHERE delta_{d} IS NOT NULL"
        df = duckdb_query(sql)
        vals = df[f"delta_{d}"].dropna()
        if len(vals) == 0:
            continue
        dem_stats_all.append({
            "DEM": d,
            "N_points": len(vals),
            "MAE": round(vals.abs().mean(), 3),
            "RMSE": round((vals ** 2).mean() ** 0.5, 3),
            "Bias": round(vals.mean(), 3),
        })

    # Сортуємо щоб DEM, який зараз обраний був першим (для обох таблиць)
    dem_stats_hand = sorted(dem_stats_hand, key=lambda x: (x["DEM"] != dem, x["DEM"]))
    dem_stats_all = sorted(dem_stats_all, key=lambda x: (x["DEM"] != dem, x["DEM"]))

    columns = [{"name": k, "id": k} for k in ["DEM", "N_points", "MAE", "RMSE", "Bias"]]

    # Груповий barplot (MAE, RMSE, Bias)
    bar_fig = go.Figure()
    bar_fig.add_trace(go.Bar(
        x=[d["DEM"] for d in dem_stats_hand],
        y=[d["MAE"] for d in dem_stats_hand],
        name="MAE",
        marker_color="#2ca02c"
    ))
    bar_fig.add_trace(go.Bar(
        x=[d["DEM"] for d in dem_stats_hand],
        y=[d["RMSE"] for d in dem_stats_hand],
        name="RMSE",
        marker_color="#1f77b4"
    ))
    bar_fig.add_trace(go.Bar(
        x=[d["DEM"] for d in dem_stats_hand],
        y=[d["Bias"] for d in dem_stats_hand],
        name="Bias",
        marker_color="#ff7f0e"
    ))
    bar_fig.update_layout(
        barmode="group",
        title="Порівняння похибок DEM " +
              ("у floodplain (HAND)" if use_hand else " (всі точки)"),
        xaxis_title="DEM",
        yaxis_title="Error (м)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        bargap=0.18,
        plot_bgcolor="#f9f9f9"
    )

    return (
        fig,  # error_plot.figure
        base_stats,  # stats_output.children
        dem_stats_hand,  # dem_stats_table.data
        columns,  # dem_stats_table.columns
        dem_stats_all,  # dem_stats_table_all.data
        columns,  # dem_stats_table_all.columns
        bar_fig  # dem_stats_bar.figure
    )


if __name__ == '__main__':
    app.run(debug=True)



# import plotly.express as px
# from dash import Dash, dcc, html, Input, Output, dash_table
#
# parquet_file = "data/icesat2_dem_filtered_fixed_1.parquet"
# dem_list = [
#     "alos_dem", "aster_dem", "copernicus_dem", "fab_dem",
#     "nasa_dem", "srtm_dem", "tan_dem"
# ]
# hand_column_map = {dem: f"{dem}_2000" for dem in dem_list}
#
# def duckdb_query(sql):
#     import duckdb
#     con = duckdb.connect()
#     try:
#         return con.execute(sql).fetchdf()
#     finally:
#         con.close()
#
# def get_unique_lulc_names(parquet_file, dem):
#     sql = f"SELECT DISTINCT lulc_name FROM '{parquet_file}' WHERE delta_{dem} IS NOT NULL AND lulc_name IS NOT NULL ORDER BY lulc_name"
#     try:
#         df = duckdb_query(sql)
#         return [{"label": x, "value": x} for x in df["lulc_name"].dropna().tolist()]
#     except Exception:
#         return []
#
# def get_unique_landform(parquet_file, dem):
#     sql = f"SELECT DISTINCT {dem}_landform FROM '{parquet_file}' WHERE {dem}_landform IS NOT NULL ORDER BY {dem}_landform"
#     try:
#         df = duckdb_query(sql)
#         return [{"label": x, "value": x} for x in df[f"{dem}_landform"].dropna().tolist()]
#     except Exception:
#         return []
#
# app = Dash(__name__)
#
# app.layout = html.Div([
#     html.H3("DEM error dashboard + Floodplain (HAND) analysis"),
#     dcc.Dropdown(id="dem_select", options=[{'label': dem, 'value': dem} for dem in dem_list], value="alos_dem"),
#     dcc.Dropdown(id="lulc_select", multi=True, placeholder="LULC class"),
#     dcc.Dropdown(id="landform_select", multi=True, placeholder="Landform class"),
#     dcc.RangeSlider(id="slope_slider", min=0, max=45, step=1, value=[0, 45],
#                     marks={i: str(i) for i in range(0, 46, 10)}),
#     dcc.RangeSlider(id="hand_slider", min=0, max=20, step=1, value=[0, 5],
#                     marks={i: str(i) for i in range(0, 21, 5)}, tooltip={"placement": "bottom", "always_visible": True}),
#     dcc.Graph(id="error_plot"),
#     html.Div(id="stats_output"),
#     html.H4("Таблиця статистики по всіх DEM у floodplain (HAND)"),
#     dash_table.DataTable(id="dem_stats_table", style_table={"overflowX": "auto"})
# ])
#
# @app.callback(
#     Output("lulc_select", "options"),
#     Output("landform_select", "options"),
#     Input("dem_select", "value"),
# )
# def update_dropdowns(dem):
#     lulc_options = get_unique_lulc_names(parquet_file, dem)
#     landform_options = get_unique_landform(parquet_file, dem)
#     return lulc_options, landform_options
#
# @app.callback(
#     Output("error_plot", "figure"),
#     Output("stats_output", "children"),
#     Output("dem_stats_table", "data"),
#     Output("dem_stats_table", "columns"),
#     Input("dem_select", "value"),
#     Input("lulc_select", "value"),
#     Input("landform_select", "value"),
#     Input("slope_slider", "value"),
#     Input("hand_slider", "value"),
# )
# def update_graph(dem, lulc, landform, slope_range, hand_range):
#     hand_col = hand_column_map.get(dem)
#     sql_all = f"SELECT delta_{dem}, {hand_col} FROM '{parquet_file}' WHERE delta_{dem} IS NOT NULL"
#     if slope_range != [0, 45]:
#         sql_all += f" AND {dem}_slope BETWEEN {slope_range[0]} AND {slope_range[1]}"
#     if lulc:
#         lulc_str = ','.join([f"'{x}'" for x in lulc])
#         sql_all += f" AND lulc_name IN ({lulc_str})"
#     if landform:
#         landform_str = ','.join([f"'{x}'" for x in landform])
#         sql_all += f" AND {dem}_landform IN ({landform_str})"
#     # HAND filter
#     if hand_col:
#         sql_all += f" AND {hand_col} BETWEEN {hand_range[0]} AND {hand_range[1]}"
#     dff_all = duckdb_query(sql_all)
#     N = len(dff_all)
#     if N == 0:
#         return {}, "<b>No data for selection</b>", [], []
#     base_delta = dff_all[f"delta_{dem}"]
#     base_rms = (base_delta ** 2).mean() ** 0.5
#     base_mae = base_delta.abs().mean()
#     base_bias = base_delta.mean()
#     base_stats = f"ALL: {N} точок | RMS: {base_rms:.2f} | MAE: {base_mae:.2f} | Bias: {base_bias:.2f}"
#     dff_plot = dff_all if N <= 20000 else dff_all.sample(n=20000, random_state=42)
#     fig = px.box(
#         dff_plot,
#         y=f"delta_{dem}",
#         points="all",
#         title=f"Error for {dem} (Sampled {len(dff_plot)} of {N})<br>HAND: {hand_range[0]}–{hand_range[1]} м"
#     )
#
#     # Таблиця для ВСІХ DEM у floodplain (HAND slider)
#     dem_stats = []
#     for d in dem_list:
#         hand = hand_column_map[d]
#         sql_stats = f"SELECT delta_{d} FROM '{parquet_file}' WHERE delta_{d} IS NOT NULL AND {hand} BETWEEN {hand_range[0]} AND {hand_range[1]}"
#         df = duckdb_query(sql_stats)
#         vals = df[f"delta_{d}"].dropna()
#         if len(vals) == 0:
#             continue
#         mae = vals.abs().mean()
#         rmse = (vals ** 2).mean() ** 0.5
#         bias = vals.mean()
#         n = len(vals)
#         dem_stats.append({
#             "DEM": d,
#             "N_points": n,
#             "MAE": round(mae, 3),
#             "RMSE": round(rmse, 3),
#             "Bias": round(bias, 3)
#         })
#
#     # === Сортуємо: вибраний DEM завжди перший ===
#     dem_stats = sorted(dem_stats, key=lambda x: (x["DEM"] != dem, x["DEM"]))
#
#     columns = [{"name": k, "id": k} for k in ["DEM", "N_points", "MAE", "RMSE", "Bias"]]
#
#     return fig, base_stats, dem_stats, columns
#
# if __name__ == '__main__':
#     app.run(debug=True)


# import plotly.express as px
# from dash import Dash, dcc, html, Input, Output
#
# parquet_file = "data/icesat2_dem_filtered_fixed_1.parquet"
# dem_list = [
#     "alos_dem", "aster_dem", "copernicus_dem", "fab_dem",
#     "nasa_dem", "srtm_dem", "tan_dem"
# ]
#
# def duckdb_query(sql):
#     import duckdb
#     con = duckdb.connect()
#     try:
#         return con.execute(sql).fetchdf()
#     finally:
#         con.close()
#
# def get_unique_lulc_names(parquet_file, dem):
#     sql = f"SELECT DISTINCT lulc_name FROM '{parquet_file}' WHERE delta_{dem} IS NOT NULL AND lulc_name IS NOT NULL ORDER BY lulc_name"
#     print(f"[get_unique_lulc_names] SQL: {sql}")
#     try:
#         df = duckdb_query(sql)
#         lulc_list = df["lulc_name"].dropna().tolist()
#         print(f"[get_unique_lulc_names] Values for {dem}: {lulc_list}")
#         return [{"label": x, "value": x} for x in lulc_list]
#     except Exception as e:
#         print(f"[get_unique_lulc_names] ERROR: {e}")
#         return []
#
# def get_unique_landform(parquet_file, dem):
#     sql = f"SELECT DISTINCT {dem}_landform FROM '{parquet_file}' WHERE {dem}_landform IS NOT NULL ORDER BY {dem}_landform"
#     print(f"[get_unique_landform] SQL: {sql}")
#     try:
#         df = duckdb_query(sql)
#         landform_list = df[f"{dem}_landform"].dropna().tolist()
#         print(f"[get_unique_landform] Values for {dem}: {landform_list}")
#         return [{"label": x, "value": x} for x in landform_list]
#     except Exception as e:
#         print(f"[get_unique_landform] ERROR: {e}")
#         return []
#
# app = Dash(__name__)
#
# app.layout = html.Div([
#     html.H3("DEM error dashboard"),
#     dcc.Dropdown(id="dem_select", options=[{'label': dem, 'value': dem} for dem in dem_list], value="alos_dem"),
#     dcc.Dropdown(id="lulc_select", multi=True, placeholder="LULC class"),
#     dcc.Dropdown(id="landform_select", multi=True, placeholder="Landform class"),
#     dcc.RangeSlider(id="slope_slider", min=0, max=45, step=1, value=[0, 45]),
#     dcc.Graph(id="error_plot"),
#     html.Div(id="stats_output")
# ])
#
# @app.callback(
#     Output("lulc_select", "options"),
#     Output("landform_select", "options"),
#     Input("dem_select", "value"),
# )
# def update_dropdowns(dem):
#     print(f"\n[update_dropdowns] Selected DEM: {dem}")
#     lulc_options = get_unique_lulc_names(parquet_file, dem)
#     landform_options = get_unique_landform(parquet_file, dem)
#     print(f"[update_dropdowns] lulc_options: {lulc_options}")
#     print(f"[update_dropdowns] landform_options: {landform_options}")
#     return lulc_options, landform_options
#
# @app.callback(
#     Output("error_plot", "figure"),
#     Output("stats_output", "children"),
#     Input("dem_select", "value"),
#     Input("lulc_select", "value"),
#     Input("landform_select", "value"),
#     Input("slope_slider", "value"),
# )
# def update_graph(dem, lulc, landform, slope_range):
#     print(f"\n[update_graph] DEM: {dem}")
#     print(f"[update_graph] LULC filter: {lulc}")
#     print(f"[update_graph] Landform filter: {landform}")
#     print(f"[update_graph] Slope range: {slope_range}")
#
#     # 1. SQL — ВИБІРКА ДЛЯ ВСІХ (без LIMIT)
#     sql_all = f"SELECT delta_{dem} FROM '{parquet_file}' WHERE delta_{dem} IS NOT NULL"
#     if slope_range != [0, 45]:
#         sql_all += f" AND {dem}_slope BETWEEN {slope_range[0]} AND {slope_range[1]}"
#     if lulc:
#         lulc_str = ','.join([f"'{x}'" for x in lulc])
#         sql_all += f" AND lulc_name IN ({lulc_str})"
#     if landform:
#         landform_str = ','.join([f"'{x}'" for x in landform])
#         sql_all += f" AND {dem}_landform IN ({landform_str})"
#     print(f"[update_graph] SQL for STATS (ALL rows): {sql_all}")
#
#     try:
#         dff_all = duckdb_query(sql_all)
#     except Exception as e:
#         print(f"[update_graph] DuckDB SQL ERROR: {e}")
#         return {}, "<b>SQL error</b>"
#
#     N = len(dff_all)
#     print(f"[update_graph] ALL data rows: {N}")
#
#     if N == 0:
#         return {}, "<b>No data for selection</b>"
#
#     # 2. Статистика — всі точки
#     base_delta = dff_all[f"delta_{dem}"]
#     base_rms = (base_delta ** 2).mean() ** 0.5
#     base_mae = base_delta.abs().mean()
#     base_bias = base_delta.mean()
#     base_stats = f"ALL: {N} точок | RMS: {base_rms:.2f} | MAE: {base_mae:.2f} | Bias: {base_bias:.2f}"
#
#     # 3. Для plotly — тільки sample (до 20k)
#     if N > 20000:
#         print(f"[update_graph] Too many points: {N}, sampling 20k for plotly...")
#         dff_plot = dff_all.sample(n=20000, random_state=42)
#     else:
#         dff_plot = dff_all
#
#     print(f"[update_graph] Plotly rows: {len(dff_plot)}")
#
#     fig = px.box(dff_plot, y=f"delta_{dem}", points="all", title=f"Error for {dem} (Sampled {len(dff_plot)} of {N})")
#     return fig, base_stats
#
# if __name__ == '__main__':
#     app.run(debug=True)
