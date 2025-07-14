# db.py
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

    def get_filtered_sample(self, con, dem, slope_range=None, hand_range=None, lulc=None, landform=None,
                            sample_n=10000):
        filters = [
            f"delta_{dem} IS NOT NULL",
            "atl03_cnf = 4",
            "atl08_class = 1"
        ]
        if slope_range:
            filters.append(f"{dem}_slope BETWEEN {slope_range[0]} AND {slope_range[1]}")
        if hand_range:
            filters.append(f"{dem}_2000 BETWEEN {hand_range[0]} AND {hand_range[1]}")
        if lulc:
            lulc_str = ",".join([f"'{x}'" for x in lulc])
            filters.append(f"lulc_name IN ({lulc_str})")
        if landform:
            landform_str = ",".join([f"'{x}'" for x in landform])
            filters.append(f"{dem}_landform IN ({landform_str})")
        where = " AND ".join(filters)
        sql = f"""
              SELECT * FROM '{self.parquet_file}'
              WHERE {where}
              USING SAMPLE {sample_n} ROWS
          """
        return con.execute(sql).fetchdf()

    def get_filtered_data(self, con, dem, slope_range=None, hand_range=None, lulc=None, landform=None, cols=None):
        filters = [
            f"delta_{dem} IS NOT NULL",
            "atl03_cnf = 4",
            "atl08_class = 1"
        ]
        if slope_range:
            filters.append(f"{dem}_slope BETWEEN {slope_range[0]} AND {slope_range[1]}")
        if hand_range:
            filters.append(f"{dem}_2000 BETWEEN {hand_range[0]} AND {hand_range[1]}")
        if lulc:
            lulc_str = ",".join([f"'{x}'" for x in lulc])
            filters.append(f"lulc_name IN ({lulc_str})")
        if landform:
            landform_str = ",".join([f"'{x}'" for x in landform])
            filters.append(f"{dem}_landform IN ({landform_str})")
        where = " AND ".join(filters)
        if cols:
            col_str = ", ".join(cols)
        else:
            col_str = "*"
        sql = f"SELECT {col_str} FROM '{self.parquet_file}' WHERE {where}"
        return con.execute(sql).fetchdf()

    def get_unique_lulc_names(self, dem):
        # ПРАВИЛЬНО: це метод класу, має self, і використовує self.query()
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

    def get_filtered_stats(self, con, dem, slope_range=None, hand_range=None, lulc=None, landform=None):
        filters = [
            f"delta_{dem} IS NOT NULL",
            "atl03_cnf = 4",
            "atl08_class = 1"
        ]
        if slope_range:
            filters.append(f"{dem}_slope BETWEEN {slope_range[0]} AND {slope_range[1]}")
        if hand_range:
            filters.append(f"{dem}_2000 BETWEEN {hand_range[0]} AND {hand_range[1]}")
        if lulc:
            lulc_str = ",".join([f"'{x}'" for x in lulc])
            filters.append(f"lulc_name IN ({lulc_str})")
        if landform:
            landform_str = ",".join([f"'{x}'" for x in landform])
            filters.append(f"{dem}_landform IN ({landform_str})")
        where = " AND ".join(filters)
        sql = f"""
            SELECT 
                COUNT(*) as N_points,
                ROUND(AVG(ABS(delta_{dem})),2) as MAE,
                ROUND(SQRT(AVG(POWER(delta_{dem}, 2))), 2) as RMSE,
                ROUND(AVG(delta_{dem}), 2) as Bias
            FROM '{self.parquet_file}'
            WHERE {where}
        """
        df = con.execute(sql).fetchdf()
        return df.iloc[0].to_dict()

    # utils/db.py

    def get_dem_stats_sql(self, con, dem_key, hand_range=None):
        filters = [
            f"delta_{dem_key} IS NOT NULL",
            "atl03_cnf = 4",
            "atl08_class = 1"
        ]
        if hand_range:
            filters.append(f"{dem_key}_2000 BETWEEN {hand_range[0]} AND {hand_range[1]}")
        filter_str = " AND ".join(filters)
        sql = f"""
                   SELECT 
            COUNT(delta_{dem_key}) as N_points,
            ROUND(AVG(ABS(delta_{dem_key})), 3) as MAE,
            ROUND(SQRT(AVG(POWER(delta_{dem_key}, 2))), 3) as RMSE,
            ROUND(AVG(delta_{dem_key}), 3) as Bias
            FROM '{self.parquet_file}'
            WHERE {filter_str}
        """
        df = con.execute(sql).fetchdf()
        if not df.empty and df.iloc[0].N_points:
            res = df.iloc[0].to_dict()
            res["DEM"] = dem_key
            return res
        return None

    def get_unique_tracks(self, year):
        sql = (
            f"SELECT DISTINCT track, rgt, spot FROM '{self.parquet_file}' "
            f"WHERE year = {year} AND atl03_cnf = 4 AND atl08_class = 1 "
            "ORDER BY track, rgt, spot"
        )
        return self.query(sql)

    def get_time_series(self, track, rgt, spot, dem):
        sql = (
            f"SELECT DATE(time) as date_only, AVG(abs_delta_{dem}) as mean_abs_error "
            f"FROM '{self.parquet_file}' "
            f"WHERE track={track} AND rgt={rgt} AND spot={spot} "
            "AND atl03_cnf = 4 AND atl08_class = 1 "
            "GROUP BY date_only ORDER BY date_only"
        )
        return self.query(sql)

    def get_track_data_for_date(self, track, rgt, spot, dem, date, hand_range=None):
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

    def load_nmad_values(self):
        dem_list = [
            "alos", "aster", "cop", "fab",
            "nasa", "srtm", "tan"
        ]
        columns = ", ".join([f"nmad_{dem}" for dem in dem_list])
        query = f"""
            SELECT {columns}
            FROM '{self.parquet_file}'
            WHERE 
                nmad_alos IS NOT NULL AND nmad_alos < 40 AND
                nmad_aster IS NOT NULL AND nmad_aster < 40 AND
                nmad_cop IS NOT NULL AND nmad_cop < 40 AND
                nmad_fab IS NOT NULL AND nmad_fab < 40 AND
                nmad_nasa IS NOT NULL AND nmad_nasa < 40 AND
                nmad_srtm IS NOT NULL AND nmad_srtm < 40 AND
                nmad_tan IS NOT NULL AND nmad_tan < 40
        """
        return self.query(query)

    def get_cdf_from_duckdb(self, thresholds=np.arange(0, 41, 1)):
        import duckdb
        import pandas as pd

        con = duckdb.connect()
        dem_list = ["alos", "aster", "cop", "fab", "nasa", "srtm", "tan"]

        cdf_data = []

        for dem in dem_list:
            dem_col = f"nmad_{dem}"
            union_sql = "\nUNION ALL\n".join([
                f"""
                SELECT {t} AS threshold,
                       COUNT(*) FILTER (WHERE {dem_col} <= {t}) * 1.0 / COUNT(*) AS cdf
                FROM '{self.parquet_file}'
                WHERE {dem_col} IS NOT NULL
                """ for t in thresholds
            ])
            df = con.execute(union_sql).fetchdf()
            df["DEM"] = dem.upper()
            cdf_data.append(df)

        con.close()
        return pd.concat(cdf_data, ignore_index=True)

    def clean_df_for_table(self, df):
        # Видалити складні/сервісні колонки для таблиць Dash
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

    def get_dem_stats(self, df, dem_key):
        # Повертає mean, min, max, count по вибраному DEM
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

