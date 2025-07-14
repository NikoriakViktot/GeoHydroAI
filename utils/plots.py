import plotly.graph_objs as go
import plotly.express as px
import numpy as np

def apply_dark_theme(fig):
    fig.update_layout(
        paper_bgcolor="#181818",
        plot_bgcolor="#181818",
        font_color="#EEEEEE",
        xaxis=dict(color="#EEEEEE", gridcolor="#333"),
        yaxis=dict(color="#EEEEEE", gridcolor="#333"),
        legend=dict(font_color="#EEEEEE", bgcolor="#181818"),
    )
    return fig


def build_error_hist(df, dem, bins=40, width=240, height=220):
    col = f"delta_{dem}"
    if df.empty or col not in df:
        fig = go.Figure()
        fig.add_annotation(
            text="No data for histogram",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=22, color="#aaa")
        )
        fig.update_layout(
            xaxis={"visible": False}, yaxis={"visible": False},
            paper_bgcolor="#23272b", plot_bgcolor="#23272b",
            height=height, width=width
        )
        return fig
    fig = go.Figure([go.Histogram(
        x=df[col].dropna(),
        nbinsx=bins,
        marker_color="royalblue",
        opacity=0.8,
        name="Error histogram"
    )])
    fig.update_layout(
        xaxis_title="Error (m)",
        yaxis_title="Count",
        height=height,
        width=width,
        margin=dict(l=15, r=15, t=40, b=15)
    )
    fig = apply_dark_theme(fig)
    return fig


def build_error_box(df, dem, show_points="all", width=180, height=220):
    col = f"delta_{dem}"
    if df.empty or col not in df:
        fig = go.Figure()
        fig.add_annotation(
            text="No data for boxplot",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=22, color="#aaa")
        )
        fig.update_layout(
            xaxis={"visible": False}, yaxis={"visible": False},
            paper_bgcolor="#23272b", plot_bgcolor="#23272b",
            height=height, width=width
        )
        return fig

    x = ["error"] * len(df[col])
    fig = go.Figure()
    fig.add_trace(go.Box(
        y=df[col].dropna(),
        x=x,
        boxpoints=show_points,
        marker_color="royalblue",
        line_color="#EEEEEE",
        name=dem.upper(),
        width=0.18,  # сам box вузький
        jitter=0.3
    ))
    fig.update_layout(
        yaxis_title="Error (m)",
        xaxis=dict(range=[-0.35, 0.35], visible=False),
        width=width,
        height=height,
        margin=dict(l=15, r=15, t=40, b=15)
    )
    fig = apply_dark_theme(fig)
    return fig

def build_dem_stats_bar(stats_list, width=280, height=220, sort_by="MAE"):
    if not stats_list:
        return go.Figure()
    # Сортуємо за MAE (від найменшого до найбільшого)
    stats_list_sorted = sorted(stats_list, key=lambda d: d[sort_by])
    dem_names = [(d["DEM"].upper()).replace('_', " ") for d in stats_list_sorted]
    mae = [d["MAE"] for d in stats_list_sorted]
    rmse = [d["RMSE"] for d in stats_list_sorted]
    bias = [d["Bias"] for d in stats_list_sorted]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=dem_names, y=mae, name="MAE", marker_color="#2ca02c"))
    fig.add_trace(go.Bar(x=dem_names, y=rmse, name="RMSE", marker_color="#1f77b4"))
    fig.add_trace(go.Bar(x=dem_names, y=bias, name="Bias", marker_color="#ff7f0e"))
    fig.update_layout(
        barmode="group",
        xaxis_title="DEM",
        yaxis_title="Error (м)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        bargap=0.18,
        width=width,
        height=height,
        margin=dict(l=15, r=15, t=40, b=15)
    )
    fig = apply_dark_theme(fig)
    return fig



def plot_cdf_nmad(cdf_df):
    fig = go.Figure()
    for dem in cdf_df["DEM"].unique():
        df_ = cdf_df[cdf_df["DEM"] == dem]
        fig.add_trace(go.Scatter(
            x=df_["threshold"],
            y=df_["cdf"],
            mode="lines+markers",
            name=dem,
            hovertemplate=
            f"<b>{dem.upper()}</b><br>" +
            "NMAD ≤ %{x:.2f} м<br>" +
            "Частка: %{y:.1%}<extra></extra>"
        ))

    fig.update_layout(
        xaxis_title="NMAD (м)",
        yaxis_title="Частка точок ≤ X",
        hovermode="x unified",
        template="plotly_dark",
        font=dict(size=13),
        margin=dict(t=40, b=40, l=60, r=30)
    )
    return fig



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

