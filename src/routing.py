from dataclasses import dataclass

import pandas as pd
from shapely import wkb
from sqlalchemy import Engine
from sqlmodel import text

from src import database


@dataclass
class ShortestRoute:
    nodes: list[tuple[float, float]]
    cost: float


def get_nearest_node(x: float, y: float, engine: Engine, table_name: str) -> int:
    query = text(f"""
        SELECT id FROM {table_name}
        ORDER BY geom <-> ST_SetSRID(ST_MakePoint(:x, :y), 4326)
        LIMIT 1;
    """)
    with engine.connect() as conn:
        return conn.execute(query, {"x": x, "y": y}).scalar()


def calculate_shortest_route_road(source: tuple[float, float], target: tuple[float, float]) -> ShortestRoute:
    engine = database.DatabaseManager.engine
    
    source_id = get_nearest_node(
        x=source[0],
        y=source[1],
        engine=engine,
        table_name="road_nodes"
    )

    target_id = get_nearest_node(
        x=target[0],
        y=target[1],
        engine=engine,
        table_name="road_nodes"
    )
    
    sql = text("""
        WITH route AS (
            SELECT *
            FROM pgr_dijkstra(
                '
                SELECT
                    id,
                    source,
                    target,
                    cost,
                    reverse_cost
                FROM road_edges
                ',
                :start_node,
                :end_node,
                directed := true
            )
        )

        SELECT
            r.seq,
            r.path_seq,
            r.node,
            r.edge,
            r.cost,
            r.agg_cost,
            ST_AsBinary(n.geom) AS geom
        FROM route r
        JOIN road_nodes n
            ON r.node = n.id
        ORDER BY r.path_seq;
    """)

    with engine.connect() as conn:
        rows = conn.execute(sql, {
            "start_node": source_id,
            "end_node": target_id
        }).fetchall()

    if not rows:
        return {
            "cost": None,
            "coordinates": []
        }

    coordinates = []
    total_cost = 0.0

    for row in rows:
        geom = wkb.loads(bytes(row.geom))
        coordinates.append((
            geom.x,   # longitude
            geom.y    # latitude
        ))
        total_cost = float(row.agg_cost)

    return {
        "cost": total_cost,
        "coordinates": coordinates
    }


def calculate_shortest_route_transit():
    pass


def calculate_shortest_route_pr(source: tuple[float, float], target: tuple[float, float]) -> ShortestRoute:
    engine = database.DatabaseManager.engine

    source_id = get_nearest_node(
        x=source[0],
        y=source[1],
        engine=engine,
        table_name="road_nodes"
    )

    target_id = get_nearest_node(
        x=target[0],
        y=target[1],
        engine=engine,
        table_name="transit_nodes"
    )

    pr_nodes = pd.read_sql_query("""
        SELECT id, road_node, transit_node 
        FROM pr_nodes;
    """, engine)

    for _, pr in pr_nodes.iterrows():
        rode_route = f"""
            SELECT *
            FROM pgr_Dijkstra(
                'SELECT id, source, target, cost, reverse_cost FROM transit_edges',
                {source_id}, {pr['road_node']},
                directed => false
            );
        """


print(calculate_shortest_route_road(
    (21.0281023, 52.3644147),
    (21.0278057, 52.3625462)
))
