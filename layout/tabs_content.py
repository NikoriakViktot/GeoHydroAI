#layout/tabs_content.py

from dash import html, dcc, dash_table
from utils.style import tab_style, selected_tab_style, dark_table_style


content = html.Div([
    html.Div(
        children=[  # ОБОВ'ЯЗКОВО передаємо через список
            dcc.Tabs(
                id="tabs",
                value="tab-1",
                className="custom-tabs",
                children=[
                    dcc.Tab(label="📊 Порівняння DEM", value="tab-1",
                            style=tab_style, selected_style=selected_tab_style),
                    dcc.Tab(label="📈 Профіль треку", value="tab-2",
                            style=tab_style, selected_style=selected_tab_style),
                    dcc.Tab(label="🗺️ Карта", value="tab-3",
                            style=tab_style, selected_style=selected_tab_style),
                    dcc.Tab(label="📋 Таблиця", value="tab-4",
                            style=tab_style, selected_style=selected_tab_style),
                    dcc.Tab(label="CDF Accumulation", value="tab-5",
                    style = tab_style, selected_style = selected_tab_style),

]
            ),
            dcc.Store(id="cdf-store"),

            # ✅ Лише один tab-content
            dcc.Loading(
                id="main-loading",
                type="circle",
                color="#2d8cff",
                children=html.Div(id="tab-content", style={"marginTop": "20px"})
            )
        ],
        style={
            "maxWidth": "1180px",
            "margin": "0 auto 24px auto",
            "paddingTop": "16px",
            "zIndex": 10,
        }
    )
], style={
    "marginLeft": "300px",
    "padding": "0 30px 24px 30px",
    "backgroundColor": "#181818",
    "color": "#EEEEEE",
    "minHeight": "100vh"
})
