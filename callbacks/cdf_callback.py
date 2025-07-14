# cdf_callback.py
from dash import html, dcc
from utils.plots import plot_cdf_nmad
import dash
import pandas as pd



def get_cdf_tab(cdf_df_or_json):
    if isinstance(cdf_df_or_json, str):  # JSON case
        cdf_df = pd.read_json(cdf_df_or_json, orient="split")
    else:
        cdf_df = cdf_df_or_json
    fig = plot_cdf_nmad(cdf_df)
    return html.Div([
        html.H4("CDF Accumulation Curve"),
        dcc.Graph(figure=fig)
    ])
