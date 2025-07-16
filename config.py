# config.py

from pathlib import Path

# Головна папка з COG-файлами
GEOTIFF_DIR = "data/COG"
DRIVER_PATH = str(Path("tc_db/terracotta.sqlite"))  # ← тепер це рядок!
PROJECTION = "EPSG:3857"
TILE_PATH_TEMPLATE = "/tiles/{category}/{name}/{z}/{x}/{y}.png"

# Сервер Terracotta
TC_PORT = 5000
TC_HOST = "localhost"
TC_URL = f"http://{TC_HOST}:{TC_PORT}"

# DEM типи
DEM_KEYS = [
    "alos", "aster", "copernicus", "fab", "nasa", "srtm", "tan"
]

LULC_YEARS = list(range(2018, 2026))
