# init_db.py
import os
import terracotta as tc
from config import GEOTIFF_DIR, DRIVER_PATH, DEM_KEYS, DEM_PARAMS, LULC_YEARS

driver = tc.get_driver(DRIVER_PATH)

# Створюємо SQLite файл, якщо ще немає
os.makedirs(os.path.dirname(DRIVER_PATH), exist_ok=True)
if not os.path.exists(DRIVER_PATH):
    driver.create(keys=["category", "name"])

with driver.connect():
    # DEM: проходимо по всіх DEM_PARAMS
    for category in DEM_PARAMS:
        folder_path = os.path.join(GEOTIFF_DIR, "dem", category)
        if not os.path.exists(folder_path):
            continue
        for fname in os.listdir(folder_path):
            if not fname.endswith(".tif"):
                continue
            path = os.path.join(folder_path, fname)
            name = fname.replace("_utm32635_cog.tif", "").replace(".tif", "")
            key_dict = {"category": category, "name": name}
            driver.insert(key_dict, path)

    # LULC: проходимо по роках
    lulc_folder = os.path.join(GEOTIFF_DIR, "lulc")
    for year in LULC_YEARS:
        filename = f"lulc_{year}_cog.tif"
        path = os.path.join(lulc_folder, filename)
        if os.path.exists(path):
            key_dict = {"category": "lulc", "name": str(year)}
            driver.insert(key_dict, path)
