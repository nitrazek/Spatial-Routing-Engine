from pathlib import Path

import geopandas as gpd
import pandas as pd

from src import database


def prepare_data() -> gpd.GeoDataFrame:
    car_data_path = Path("local", "export.geojson")
    public_data_path = Path("local", "gtfs")
    pr_data_path = Path("local", "parkingi_pr.geojson")
    
    car_gdf = gpd.read_file(car_data_path)
    car_gdf['maxspeed'] = pd.to_numeric(car_gdf['maxspeed'], errors='coerce')
    car_gdf['maxspeed'] = car_gdf['maxspeed'].fillna(50).astype(int)

    return car_gdf


def insert_database():
    database.DatabaseManager.create_db_and_tables()

    car_gdf = prepare_data()
    car_gdf.to_postgis(
        name="ways",
        con=database.DatabaseManager.engine,
        if_exists="replace",
        index=False,
        chunksize=10000
    )

   
if __name__ == "__main__":
    insert_database()