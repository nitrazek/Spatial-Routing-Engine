import geopandas as gpd
from sqlalchemy import text
from pathlib import Path

from scripts import DATA_DIR
from src.database import DatabaseManager


engine = DatabaseManager.engine
DatabaseManager.create_db_and_tables()

GEOJSON_FILE = DATA_DIR / "pr" / "parkingi_pr.geojson"

if GEOJSON_FILE.is_file():
    print(f"Wczytywanie danych z pliku: {GEOJSON_FILE}")
    gdf = gpd.read_file(GEOJSON_FILE)
else:
    raise FileNotFoundError(f"Nie znaleziono pliku: {GEOJSON_FILE}")

print(f"Wczytano obiektów: {len(gdf)}")

gdf["x"] = round(gdf.geometry.x, 6)
gdf["y"] = round(gdf.geometry.y, 6)
if "id" not in gdf.columns:
    gdf["id"] = range(1, len(gdf) + 1)

if "public_transport" in gdf.columns:
    gdf["public_transport"] = gdf["public_transport"].apply(
        lambda v: ", ".join(v) if isinstance(v, list) else v
    )

gdf = gdf.rename_geometry("geom")

if gdf.crs is None:
    gdf.set_crs("EPSG:4326", inplace=True)
else:
    gdf = gdf.to_crs("EPSG:4326")

base_cols = ["id", "x", "y", "geom"]
gdf_out = gdf[base_cols].copy()

gdf_out = gdf_out.loc[:, ~gdf_out.columns.duplicated()]

print("Zapisywanie danych do bazy danych (tabela: parkingi_pr)...")

gdf_out.to_postgis(
    "pr_nodes",
    engine,
    if_exists="replace",
    index=False
)

print("Tworzenie indeksów...")

with engine.begin() as conn:
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS parkingi_pr_geom_idx
        ON pr_nodes
        USING GIST (geom);
    """))

print("Zakończono pomyślnie!")