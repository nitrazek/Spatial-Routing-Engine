"""
Loads GTFS data from data/public_transport into PostGIS in a pgRouting-ready
shape, mirroring the road_nodes / road_edges layout used by insert_database.py.

Produced tables:
    transit_nodes(id, stop_code, name, x, y, geom)
    transit_edges(id, source, target, route_id, route_short_name, route_type,
                  trip_count, travel_time_s, cost, reverse_cost, length_m, geom)

Edges are deduplicated per (source, target, route_id) so a separate edge exists
for every line running between two adjacent stops. cost = avg travel time in
seconds; reverse_cost = -1 because GTFS trips are inherently directional.
"""

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString
from sqlalchemy import text

from scripts import DATA_DIR
from src.database import DatabaseManager


engine = DatabaseManager.engine

GTFS_DIR = DATA_DIR / "public_transport"

# safety floor for travel time between two stops (seconds)
MIN_TRAVEL_TIME_S = 20
# upper sanity bound (drops obvious data glitches, e.g. overnight wraps)
MAX_TRAVEL_TIME_S = 60 * 60 * 3


def parse_gtfs_time(series: pd.Series) -> pd.Series:
    """GTFS times can exceed 24:00:00, so parse manually to seconds."""
    parts = series.str.split(":", expand=True).astype("int32")
    return parts[0] * 3600 + parts[1] * 60 + parts[2]


print("Reading stops...")
stops = pd.read_csv(
    GTFS_DIR / "stops.txt",
    dtype={
        "stop_id": "int64",
        "stop_code": "string",
        "stop_name": "string",
        "stop_lat": "float64",
        "stop_lon": "float64",
    },
)

print(f"  stops: {len(stops)}")

print("Reading routes...")
routes = pd.read_csv(
    GTFS_DIR / "routes.txt",
    dtype={
        "route_id": "string",
        "route_short_name": "string",
        "route_type": "int16",
    },
    usecols=["route_id", "route_short_name", "route_type"],
)
print(f"  routes: {len(routes)}")

print("Reading trips...")
trips = pd.read_csv(
    GTFS_DIR / "trips.txt",
    dtype={"route_id": "string", "trip_id": "string"},
    usecols=["route_id", "trip_id"],
)
print(f"  trips: {len(trips)}")

print("Reading stop_times (large)...")
stop_times = pd.read_csv(
    GTFS_DIR / "stop_times.txt",
    dtype={
        "trip_id": "string",
        "arrival_time": "string",
        "departure_time": "string",
        "stop_id": "int64",
        "stop_sequence": "int32",
    },
    usecols=[
        "trip_id",
        "arrival_time",
        "departure_time",
        "stop_id",
        "stop_sequence",
    ],
)
print(f"  stop_times: {len(stop_times)}")

print("Parsing times...")
stop_times["arrival_s"] = parse_gtfs_time(stop_times["arrival_time"])
stop_times["departure_s"] = parse_gtfs_time(stop_times["departure_time"])
stop_times = stop_times.drop(columns=["arrival_time", "departure_time"])

print("Building consecutive stop pairs per trip...")
stop_times = stop_times.sort_values(["trip_id", "stop_sequence"], kind="stable")

# shift next-stop info inside each trip
grp = stop_times.groupby("trip_id", sort=False)
stop_times["next_stop_id"] = grp["stop_id"].shift(-1)
stop_times["next_arrival_s"] = grp["arrival_s"].shift(-1)

# drop last stop of each trip (no successor) and compute travel time
pairs = stop_times.dropna(subset=["next_stop_id"]).copy()
pairs["next_stop_id"] = pairs["next_stop_id"].astype("int64")
pairs["travel_time_s"] = pairs["next_arrival_s"] - pairs["departure_s"]

# filter implausible values
pairs = pairs[
    (pairs["travel_time_s"] > 0)
    & (pairs["travel_time_s"] <= MAX_TRAVEL_TIME_S)
]

# attach route_id via trips
pairs = pairs.merge(trips, on="trip_id", how="inner")

print(f"  stop-to-stop hops: {len(pairs)}")

print("Aggregating edges per (source, target, route_id)...")
edges = (
    pairs.groupby(
        ["stop_id", "next_stop_id", "route_id"],
        sort=False,
        as_index=False,
    )
    .agg(
        trip_count=("trip_id", "count"),
        travel_time_s=("travel_time_s", "mean"),
    )
    .rename(columns={"stop_id": "source", "next_stop_id": "target"})
)

edges["travel_time_s"] = (
    edges["travel_time_s"].round().clip(lower=MIN_TRAVEL_TIME_S).astype("int32")
)
edges["cost"] = edges["travel_time_s"].astype("float64")
edges["reverse_cost"] = -1.0

# enrich with route metadata
edges = edges.merge(routes, on="route_id", how="left")

print(f"  unique edges: {len(edges)}")

# only keep stops actually referenced by edges (drops orphan stops)
used_stop_ids = pd.Index(
    pd.concat([edges["source"], edges["target"]]).unique()
)
stops = stops[stops["stop_id"].isin(used_stop_ids)].copy()
print(f"  stops kept: {len(stops)}")

print("Building node geometries...")
stops_out = pd.DataFrame(
    {
        "id": stops["stop_id"].astype("int64").values,
        "stop_code": stops["stop_code"].values,
        "name": stops["stop_name"].values,
        "x": stops["stop_lon"].values,
        "y": stops["stop_lat"].values,
    }
)
stops_out["geom"] = [
    Point(lon, lat)
    for lon, lat in zip(stops["stop_lon"].values, stops["stop_lat"].values)
]
nodes_gdf = gpd.GeoDataFrame(stops_out, geometry="geom", crs="EPSG:4326")

print("Building edge geometries (straight lines between stops)...")
coords = stops.set_index("stop_id")[["stop_lon", "stop_lat"]]

src = coords.reindex(edges["source"].values).reset_index(drop=True)
dst = coords.reindex(edges["target"].values).reset_index(drop=True)

# drop edges where either endpoint is missing (shouldn't happen, but guard)
valid = src["stop_lon"].notna() & dst["stop_lon"].notna()
edges = edges[valid.values].reset_index(drop=True)
src = src[valid].reset_index(drop=True)
dst = dst[valid].reset_index(drop=True)

geoms = [
    LineString([(sx, sy), (tx, ty)])
    for sx, sy, tx, ty in zip(
        src["stop_lon"].values,
        src["stop_lat"].values,
        dst["stop_lon"].values,
        dst["stop_lat"].values,
    )
]

edges_out = pd.DataFrame(
    {
        "id": range(1, len(edges) + 1),
        "source": edges["source"].astype("int64").values,
        "target": edges["target"].astype("int64").values,
        "route_id": edges["route_id"].values,
        "route_short_name": edges["route_short_name"].values,
        "route_type": edges["route_type"].astype("int16").values,
        "trip_count": edges["trip_count"].astype("int32").values,
        "travel_time_s": edges["travel_time_s"].values,
        "cost": edges["cost"].values,
        "reverse_cost": edges["reverse_cost"].values,
    }
)
edges_out["geom"] = geoms
edges_gdf = gpd.GeoDataFrame(edges_out, geometry="geom", crs="EPSG:4326")

# length in meters via PL-1992 (EPSG:2180) - metric CRS for Poland
edges_gdf["length_m"] = (
    edges_gdf.to_crs(epsg=2180).length.round(2).astype("float64")
)

print("Saving transit_nodes...")
nodes_gdf.to_postgis(
    "transit_nodes",
    engine,
    if_exists="replace",
    index=False,
)

print("Saving transit_edges...")
edges_gdf.to_postgis(
    "transit_edges",
    engine,
    if_exists="replace",
    index=False,
)

print("Creating indexes...")
with engine.begin() as conn:
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS transit_nodes_geom_idx
        ON transit_nodes
        USING GIST (geom);
    """))
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS transit_edges_geom_idx
        ON transit_edges
        USING GIST (geom);
    """))
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS transit_edges_source_idx
        ON transit_edges(source);
    """))
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS transit_edges_target_idx
        ON transit_edges(target);
    """))
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS transit_edges_route_idx
        ON transit_edges(route_id);
    """))

print("Done.")
