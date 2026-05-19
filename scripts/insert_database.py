import re

import osmnx as ox
import geopandas as gpd

from sqlalchemy import text

from scripts import DATA_DIR
from src.database import DatabaseManager


PLACE = "Warsaw, Poland"

DEFAULT_SPEEDS = {
    "motorway": 140,
    "trunk": 100,
    "primary": 70,
    "secondary": 50,
    "tertiary": 50,
    "residential": 30,
    "service": 20,
    "living_street": 20,
    "unclassified": 40
}

DATA_DIR.mkdir(exist_ok=True)

GRAPH_FILE = DATA_DIR / "warsaw.graphml"

engine = DatabaseManager.engine

if GRAPH_FILE.is_file():
    print(f"Loading cached graph: {GRAPH_FILE}")
    G = ox.load_graphml(GRAPH_FILE)
else:
    print("Downloading graph from Overpass...")
    G = ox.graph_from_place(
        PLACE,
        network_type="drive",
        simplify=True
    )

    print(f"Saving graph cache: {GRAPH_FILE}")
    ox.save_graphml(G, GRAPH_FILE)

nodes, edges = ox.graph_to_gdfs(G)

print(f"nodes: {len(nodes)}")
print(f"edges: {len(edges)}")

edges = edges.explode(index_parts=False).reset_index()


def first(value):
    """
    OSMnx often stores attributes as lists.
    Convert list -> first scalar value.
    """
    if isinstance(value, list):
        if len(value) == 0:
            return None
        return value[0]

    return value


def clean_highway(value) -> str:
    value = first(value)

    if value is None:
        return "unclassified"

    return str(value)


def parse_speed(value, highway) -> int:
    highway = clean_highway(highway)

    value = first(value)

    if value is None:
        return DEFAULT_SPEEDS.get(highway, 50)

    match = re.search(r"\d+", str(value))

    if match:
        return int(match.group())

    return DEFAULT_SPEEDS.get(highway, 50)


def clean_oneway(value) -> bool:
    value = first(value)
    return value in [True, "yes", "1", 1]


def calculate_cost(length_m, speed_kmh) -> float:
    speed_mps = speed_kmh * 1000 / 3600
    return length_m / speed_mps


print("Preparing edges...")

required_cols = [
    "u",
    "v",
    "osmid",
    "name",
    "highway",
    "maxspeed",
    "oneway",
    "length",
    "geometry"
]

available_cols = [c for c in required_cols if c in edges.columns]

edges = edges[available_cols].copy()

edges["source"] = edges["u"].astype("int64")
edges["target"] = edges["v"].astype("int64")

edges["highway_clean"] = edges["highway"].apply(clean_highway)

edges["speed_kmh"] = edges.apply(
    lambda r: parse_speed(
        r.get("maxspeed"),
        r.get("highway_clean")
    ),
    axis=1
)

edges["oneway_clean"] = edges["oneway"].apply(clean_oneway)

# costs
edges["cost"] = edges.apply(
    lambda r: calculate_cost(
        r["length"],
        r["speed_kmh"]
    ),
    axis=1
)

edges["reverse_cost"] = edges.apply(
    lambda r: -1
    if r["oneway_clean"]
    else r["cost"],
    axis=1
)

edges["geom"] = edges["geometry"]

edges["id"] = range(1, len(edges) + 1)

# edge table
edges_out = edges[[
    "id",
    "osmid",
    "source",
    "target",
    "name",
    "highway_clean",
    "speed_kmh",
    "oneway_clean",
    "length",
    "cost",
    "reverse_cost",
    "geom"
]].copy()

edges_out = edges_out.rename(columns={
    "highway_clean": "highway",
    "oneway_clean": "oneway",
    "length": "length_m"
})

# geodataframe fix
edges_out = gpd.GeoDataFrame(
    edges_out,
    geometry="geom",
    crs="EPSG:4326"
)

# prepare nodes
nodes = nodes.reset_index()

nodes = nodes.rename(columns={
    "osmid": "id",
    "geometry": "geom"
})

nodes_out = nodes[[
    "id",
    "x",
    "y",
    "geom"
]].copy()

nodes_out = gpd.GeoDataFrame(
    nodes_out,
    geometry="geom",
    crs="EPSG:4326"
)

# remove dupliacte columns
edges_out = edges_out.loc[:, ~edges_out.columns.duplicated()]
nodes_out = nodes_out.loc[:, ~nodes_out.columns.duplicated()]

print("Saving nodes...")

nodes_out.to_postgis(
    "road_nodes",
    engine,
    if_exists="replace",
    index=False
)

print("Saving edges...")

edges_out.to_postgis(
    "road_edges",
    engine,
    if_exists="replace",
    index=False
)

print("Creating indexes...")

with engine.begin() as conn:

    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS road_nodes_geom_idx
        ON road_nodes
        USING GIST (geom);
    """))

    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS road_edges_geom_idx
        ON road_edges
        USING GIST (geom);
    """))

    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS road_edges_source_idx
        ON road_edges(source);
    """))

    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS road_edges_target_idx
        ON road_edges(target);
    """))
