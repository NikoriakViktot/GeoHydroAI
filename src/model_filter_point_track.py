# src/model_filter_point_track.py

import pandas as pd
from sklearn.cluster import DBSCAN
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures

def clean_ground_dbscan(df, eps=10, min_samples=5):
    X = df[["distance_m", "orthometric_height"]].values
    clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(X)
    df = df.copy()
    df["cluster"] = clustering.labels_
    df = df[df["cluster"] != -1]
    df_bottom = df.loc[df.groupby("cluster")["orthometric_height"].idxmin()]
    return df_bottom

def clean_ground_flexible(df, window=15, tolerance=0.8, group_width=10):
    df = df.sort_values("distance_m").copy()
    df["rolling_min"] = df["orthometric_height"].rolling(window=window, center=True).min()
    df["is_near_bottom"] = (df["orthometric_height"] - df["rolling_min"]).abs() < tolerance
    df["block"] = (df["distance_m"] / group_width).astype(int)
    kept_blocks = df[df["is_near_bottom"]].groupby("block").filter(lambda g: len(g) >= 2)["block"].unique()
    df_clean = df[df["block"].isin(kept_blocks) & df["is_near_bottom"]]
    return df_clean

def clean_ground_mnk_local(df, window_size=150, step=50, degree=2, residual_tol=0.2):
    df = df.sort_values("distance_m").copy()
    x = df["distance_m"].values
    result = []
    start = x.min()
    end = x.max()
    for x0 in np.arange(start, end, step):
        x_start = x0
        x_end = x0 + window_size
        df_window = df[(df["distance_m"] >= x_start) & (df["distance_m"] <= x_end)]
        if len(df_window) < degree + 1:
            continue
        X = df_window["distance_m"].values.reshape(-1, 1)
        y = df_window["orthometric_height"].values
        poly = PolynomialFeatures(degree)
        X_poly = poly.fit_transform(X)
        model = LinearRegression().fit(X_poly, y)
        y_pred = model.predict(X_poly)
        residuals = y - y_pred
        df_valid = df_window[residuals <= residual_tol]
        result.append(df_valid)
    if result:
        return pd.concat(result)
    else:
        return pd.DataFrame(columns=df.columns)

def clean_ground_mnk_local_enhanced(df, window_size=150, step=50, degree=2, lower_tol=-0.5, upper_tol=1.0, shift_down=0.3):
    df = df.sort_values("distance_m").copy()
    x = df["distance_m"].values
    result = []
    start = x.min()
    end = x.max()
    for x0 in np.arange(start, end, step):
        x_start = x0
        x_end = x0 + window_size
        df_window = df[(df["distance_m"] >= x_start) & (df["distance_m"] <= x_end)]
        if len(df_window) < degree + 1:
            continue
        X = df_window["distance_m"].values.reshape(-1, 1)
        y = df_window["orthometric_height"].values
        poly = PolynomialFeatures(degree)
        X_poly = poly.fit_transform(X)
        model = LinearRegression().fit(X_poly, y)
        y_pred = model.predict(X_poly) - shift_down
        residuals = y - y_pred
        mask = (residuals >= lower_tol) & (residuals <= upper_tol)
        df_valid = df_window[mask]
        result.append(df_valid)
    if result:
        return pd.concat(result)
    else:
        return pd.DataFrame(columns=df.columns)



# #src/model_filter_point_track.py
#
# import pandas as pd
# from sklearn.cluster import DBSCAN
# import numpy as np
# from sklearn.linear_model import LinearRegression
# from sklearn.preprocessing import PolynomialFeatures
#
#
#
# def clean_ground_dbscan(df, eps=10, min_samples=5):
#     """
#     Кластеризація LiDAR-профілю методом DBSCAN та збереження мінімальної висоти у кожному кластері.
#
#     Параметри:
#     - df: DataFrame з колонками x_atc, height
#     - eps: радіус для DBSCAN (в метрах)
#     - min_samples: мінімальна кількість точок у кластері
#
#     Повертає:
#     - df_bottom: тільки найнижчі точки з кожного кластеру
#     """
#     X = df[["x_atc", "orthometric_height"]].values
#
#     # DBSCAN кластеризація
#     clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(X)
#     df = df.copy()
#     df["cluster"] = clustering.labels_
#
#     # Видалити шуми (label = -1)
#     df = df[df["cluster"] != -1]
#
#     # Залишаємо лише найнижчі точки в кожному кластері
#     df_bottom = df.loc[df.groupby("cluster")["orthometric_height"].idxmin()]
#
#     return df_bottom
#
# def clean_ground_flexible(df, window=15, tolerance=0.8, group_width=10):
#     """
#     Залишає всі точки у межах певного діапазону від rolling min, зберігаючи “дно” не як одну точку, а як групу.
#
#     - window: ширина rolling-вікна
#     - tolerance: висотне відхилення від локального мінімуму
#     - group_width: розмір блоку в метрах
#     """
#     df = df.sort_values("x_atc").copy()
#     df["rolling_min"] = df["orthometric_height"].rolling(window=window, center=True).min()
#
#     # Залишаємо точки в межах допуску від rolling min
#     df["is_near_bottom"] = (df["orthometric_height"] - df["rolling_min"]).abs() < tolerance
#
#     # Групування по x_atc — розбивка на блоки по group_width
#     df["block"] = (df["x_atc"] / group_width).astype(int)
#
#     # Зберігаємо лише блоки, де є достатньо точок рельєфу
#     kept_blocks = df[df["is_near_bottom"]].groupby("block").filter(lambda g: len(g) >= 2)["block"].unique()
#
#     df_clean = df[df["block"].isin(kept_blocks) & df["is_near_bottom"]]
#
#     return df_clean
#
#
# def clean_ground_mnk_local(df, window_size=150, step=50, degree=2, residual_tol=0.2):
#     """
#     Локальне очищення ґрунтових точок за допомогою рухомої MNK-регресії.
#
#     - window_size: ширина вікна по x_atc (у метрах)
#     - step: крок між вікнами
#     - degree: поліноміальний порядок регресії
#     - residual_tol: максимальна відстань над моделлю, щоб точку залишити
#
#     Повертає: DataFrame з відфільтрованими точками
#     """
#     df = df.sort_values("x_atc").copy()
#     x = df["x_atc"].values
#     result = []
#
#     start = x.min()
#     end = x.max()
#
#     for x0 in np.arange(start, end, step):
#         x_start = x0
#         x_end = x0 + window_size
#         df_window = df[(df["x_atc"] >= x_start) & (df["x_atc"] <= x_end)]
#
#         if len(df_window) < degree + 1:
#             continue
#
#         # МНК-регресія на локальному вікні
#         X = df_window["x_atc"].values.reshape(-1, 1)
#         y = df_window["orthometric_height"].values
#         poly = PolynomialFeatures(degree)
#         X_poly = poly.fit_transform(X)
#
#         model = LinearRegression().fit(X_poly, y)
#         y_pred = model.predict(X_poly)
#         residuals = y - y_pred
#
#         # Зберігаємо точки, що не перевищують профіль
#         df_valid = df_window[residuals <= residual_tol]
#         result.append(df_valid)
#
#     if result:
#         return pd.concat(result)
#     else:
#         return pd.DataFrame(columns=df.columns)
#
#
# def clean_ground_mnk_local_enhanced(df, window_size=150, step=50, degree=2, lower_tol=-0.5, upper_tol=1.0, shift_down=0.3):
#     """
#     Покращене локальне очищення ґрунтових точок за допомогою рухомої MNK-регресії.
#     Замість суворої обрізки, використовує верхню/нижню межу + зміщення вниз.
#
#     - window_size: ширина вікна по x_atc (у метрах)
#     - step: крок між вікнами
#     - degree: поліноміальний порядок регресії
#     - lower_tol: нижня межа залишення точки (відносно моделі)
#     - upper_tol: верхня межа залишення точки (відносно моделі)
#     - shift_down: вертикальне зміщення моделі вниз для нижнього контуру
#
#     Повертає: DataFrame з відфільтрованими точками
#     """
#     df = df.sort_values("x_atc").copy()
#     x = df["x_atc"].values
#     result = []
#
#     start = x.min()
#     end = x.max()
#
#     for x0 in np.arange(start, end, step):
#         x_start = x0
#         x_end = x0 + window_size
#         df_window = df[(df["x_atc"] >= x_start) & (df["x_atc"] <= x_end)]
#
#         if len(df_window) < degree + 1:
#             continue
#
#         X = df_window["x_atc"].values.reshape(-1, 1)
#         y = df_window["orthometric_height"].values
#         poly = PolynomialFeatures(degree)
#         X_poly = poly.fit_transform(X)
#
#         model = LinearRegression().fit(X_poly, y)
#         y_pred = model.predict(X_poly) - shift_down  # зсув моделі вниз
#         residuals = y - y_pred
#
#         mask = (residuals >= lower_tol) & (residuals <= upper_tol)
#         df_valid = df_window[mask]
#         result.append(df_valid)
#
#     if result:
#         return pd.concat(result)
#     else:
#         return pd.DataFrame(columns=df.columns)
#
#
