import duckdb
import pandas as pd
import numpy as np

class DuckDBData:
    def __init__(self, parquet_file):
        self.parquet_file = parquet_file

    def query(self, sql):
        try:
            con = duckdb.connect()
            df = con.execute(sql).fetchdf()
            con.close()
            return df
        except Exception as e:
            print(f"DuckDB query error: {e}")
            return pd.DataFrame()

    # --- 1. Стартові ключі профілю ---
    def get_default_profile_keys(self, dem="alos_dem"):
        sql = f"""
            SELECT track, rgt, spot, '{dem}' as dem, DATE(time) as date_only
            FROM '{self.parquet_file}'
            WHERE atl03_cnf = 4 AND atl08_class = 1 AND delta_{dem} IS NOT NULL
            LIMIT 1
        """
        df = self.query(sql)
        if not df.empty:
            return tuple(df.iloc[0])
        return (None, None, None, None, None)

    # --- 2. Всі унікальні треки для року ---
    def get_unique_tracks(self, year):
        sql = (
            f"SELECT DISTINCT track, rgt, spot FROM '{self.parquet_file}' "
            f"WHERE year = {year} AND atl03_cnf = 4 AND atl08_class = 1 "
            "ORDER BY track, rgt, spot"
        )
        return self.query(sql)

    # --- 3. Всі дати для треку ---
    def get_unique_dates(self, track, rgt, spot):
        sql = (
            f"SELECT DISTINCT DATE(time) as date_only FROM '{self.parquet_file}' "
            f"WHERE track={track} AND rgt={rgt} AND spot={spot} "
            "AND atl03_cnf = 4 AND atl08_class = 1 "
            "ORDER BY date_only"
        )
        return self.query(sql)

    # --- 4. Отримати профіль треку для дати/DEM ---
    def get_profile(self, track, rgt, spot, dem, date, hand_range=None):
        hand_col = f"{dem}_2000"
        sql = (
            f"SELECT * FROM '{self.parquet_file}' "
            f"WHERE track={track} AND rgt={rgt} AND spot={spot} "
            f"AND DATE(time) = '{date}' "
            f"AND delta_{dem} IS NOT NULL AND h_{dem} IS NOT NULL "
            "AND atl03_cnf = 4 AND atl08_class = 1"
        )
        if hand_range and len(hand_range) == 2 and all(x is not None for x in hand_range):
            sql += f" AND {hand_col} IS NOT NULL AND {hand_col} BETWEEN {hand_range[0]} AND {hand_range[1]}"
        sql += " ORDER BY x"
        return self.query(sql)

    # --- 5. Статистика для профілю (mean/min/max/count) ---
    def get_dem_stats(self, df, dem_key):
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

    # --- 6. Time Series для треку (по днях) ---
    def get_time_series(self, track, rgt, spot, dem):
        sql = (
            f"SELECT DATE(time) as date_only, AVG(abs_delta_{dem}) as mean_abs_error "
            f"FROM '{self.parquet_file}' "
            f"WHERE track={track} AND rgt={rgt} AND spot={spot} "
            "AND atl03_cnf = 4 AND atl08_class = 1 "
            f"AND abs_delta_{dem} IS NOT NULL "
            "GROUP BY date_only ORDER BY date_only"
        )
        return self.query(sql)

    # --- 7. GEOJSON для карти треку ---
    def get_geojson_for_date(self, track, rgt, spot, dem, date, hand_range=None, step=10):
        hand_col = f"{dem}_2000"
        sql = (
            f"SELECT x, y, delta_{dem}, abs_delta_{dem} FROM '{self.parquet_file}' "
            f"WHERE track={track} AND rgt={rgt} AND spot={spot} "
            f"AND DATE(time) = '{date}' "
            "AND atl03_cnf = 4 AND atl08_class = 1"
        )
        if hand_range and len(hand_range) == 2 and all(x is not None for x in hand_range):
            sql += f" AND {hand_col} IS NOT NULL AND {hand_col} BETWEEN {hand_range[0]} AND {hand_range[1]}"
        df = self.query(sql)
        if df.empty:
            return {"type": "FeatureCollection", "features": []}
        df = df.iloc[::step]
        features = [
            {
                "type": "Feature",
                "properties": {
                    "delta": float(r.get(f"delta_{dem}")),
                    "abs_delta": float(r.get(f"abs_delta_{dem}"))
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(r.x), float(r.y)]
                }
            }
            for _, r in df.iterrows()
        ]
        return {"type": "FeatureCollection", "features": features}

    # --- 8. LULC/landform для фільтрів ---
    def get_unique_lulc_names(self, dem):
        sql = f"""
            SELECT DISTINCT lulc_name
            FROM '{self.parquet_file}'
            WHERE delta_{dem} IS NOT NULL AND lulc_name IS NOT NULL
            AND atl03_cnf = 4 AND atl08_class = 1
            ORDER BY lulc_name
        """
        df = self.query(sql)
        return [{"label": x, "value": x} for x in df["lulc_name"].dropna().tolist()]

    def get_unique_landform(self, dem):
        landform_col = f"{dem}_landform"
        sql = f"""
            SELECT DISTINCT {landform_col}
            FROM '{self.parquet_file}'
            WHERE {landform_col} IS NOT NULL
            AND atl03_cnf = 4 AND atl08_class = 1
            ORDER BY {landform_col}
        """
        df = self.query(sql)
        return [{"label": x, "value": x} for x in df[landform_col].dropna().tolist()]

    # --- 9. Dropdowns ---
    def get_track_dropdown_options(self, year):
        df = self.get_unique_tracks(year)
        return [
            {"label": f"Track {row.track} / RGT {row.rgt} / Spot {row.spot}",
             "value": f"{row.track}_{row.rgt}_{row.spot}"}
            for _, row in df.iterrows()
        ]

    def get_date_dropdown_options(self, track, rgt, spot):
        df = self.get_unique_dates(track, rgt, spot)
        return [
            {
                "label": pd.to_datetime(row.date_only).strftime("%Y-%m-%d"),
                "value": pd.to_datetime(row.date_only).strftime("%Y-%m-%d")
            }
            for _, row in df.iterrows()
        ]

# Клас чистий, дублювання немає, всі профільні операції в одному місці!
