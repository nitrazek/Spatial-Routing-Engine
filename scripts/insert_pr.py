import geopandas as gpd
from sqlalchemy import text

from scripts import DATA_DIR
from src.database import DatabaseManager


engine = DatabaseManager.engine
DatabaseManager.create_db_and_tables()

GEOJSON_FILE = DATA_DIR / "pr" / "parkingi_pr.geojson"

if GEOJSON_FILE.is_file():
    print(f"Loading data from file: {GEOJSON_FILE}")
    gdf = gpd.read_file(GEOJSON_FILE)
else:
    raise FileNotFoundError(f"File not found: {GEOJSON_FILE}")

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

print("Saving files to database... (table: pr_nodes)...")

gdf_out.to_postgis(
    "pr_nodes_tmp",
    engine,
    if_exists="replace",
    index=False
)

with engine.begin() as conn:
    conn.execute(text("DROP TABLE IF EXISTS pr_nodes;"))
    conn.execute(text("""
        CREATE TABLE pr_nodes AS
        SELECT 
            p.*,
            (
                SELECT id FROM road_nodes r 
                ORDER BY r.geom <-> p.geom 
                LIMIT 1
            ) AS road_node,
            (
                SELECT id FROM transit_nodes t 
                ORDER BY t.geom <-> p.geom 
                LIMIT 1
            ) AS transit_node
        FROM pr_nodes_tmp p;
    """))

    conn.execute(text("DROP TABLE pr_nodes_tmp;"))

    print("Creating indexes...")

    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS pr_nodes_geom_idx
        ON pr_nodes
        USING GIST (geom);
    """))
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS pr_nodes_road_node_idx
        ON pr_nodes(road_node);
    """))
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS pr_nodes_transit_node_idx
        ON pr_nodes(transit_node);
    """))

print("Inserted successfully!")