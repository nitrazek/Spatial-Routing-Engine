import math
from dataclasses import dataclass, field
from itertools import groupby
from textwrap import dedent

import pandas as pd
from shapely import wkb
from sqlalchemy import Engine
from sqlmodel import text

from src import database


@dataclass
class Route:
    nodes: list[tuple[float, float]]
    cost: float = 0.0


@dataclass
class TransitSegment(Route):
    line: str | None = None


@dataclass
class TransitRoute:
    segments: list[TransitSegment] = field(default_factory=list)
    cost: float = 0.0


@dataclass
class PrRoute:
    road_route: Route
    transit_route: TransitRoute
    pr_node: tuple[float, float]
    cost: float = 0.0


def get_nearest_node(x: float, y: float, engine: Engine, nodes_table_name: str) -> int:
    query = text(f"""
        SELECT id FROM {nodes_table_name}
        ORDER BY geom <-> ST_SetSRID(ST_MakePoint(:x, :y), 4326)
        LIMIT 1;
    """)
    with engine.connect() as conn:
        return conn.execute(query, {"x": x, "y": y}).scalar()


def run_dijkstra(source: int, target: int, engine: Engine, edges_table_name: str, nodes_table_name: str) -> pd.DataFrame:
    return pd.read_sql_query(f"""
        SELECT n.x, n.y, d.agg_cost
        FROM pgr_Dijkstra(
            'SELECT id, source, target, cost, reverse_cost FROM {edges_table_name}',
            {source}, {target},
            directed => false
        ) d
        JOIN {nodes_table_name} n ON d.node = n.id;
    """, engine)


def calculate_shortest_route_road(source: tuple[float, float], target: tuple[float, float]) -> Route:
    engine = database.DatabaseManager.engine
    
    source_id = get_nearest_node(
        x=source[0],
        y=source[1],
        engine=engine,
        nodes_table_name="road_nodes"
    )

    target_id = get_nearest_node(
        x=target[0],
        y=target[1],
        engine=engine,
        nodes_table_name="road_nodes"
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
        return Route(
            nodes=[],
            cost=None
        )

    coordinates = []
    total_cost = 0.0

    for row in rows:
        geom = wkb.loads(bytes(row.geom))
        coordinates.append((
            geom.x,
            geom.y
        ))
        total_cost = float(row.agg_cost)

    return Route(
        nodes=coordinates,
        cost=total_cost
    )


def calculate_shortest_route_transit(source: tuple[float, float], target: tuple[float, float]) -> TransitRoute | None:
    engine = database.DatabaseManager.engine

    source_id = get_nearest_node(
        x=source[0],
        y=source[1],
        engine=engine,
        nodes_table_name="transit_nodes"
    )

    target_id = get_nearest_node(
        x=target[0],
        y=target[1],
        engine=engine,
        nodes_table_name="transit_nodes"
    )

    query = dedent(f"""\
        SELECT p.seq, p.cost AS edge_cost, p.agg_cost,
               n.x AS lon, n.y AS lat,
               e.route_short_name AS line
        FROM pgr_Dijkstra(
            'SELECT id, source, target, cost, reverse_cost FROM transit_edges',
            {source_id}, {target_id},
            directed => true
        ) p
        LEFT JOIN transit_nodes n ON n.id = p.node
        LEFT JOIN transit_edges e ON e.id = p.edge
        ORDER BY p.seq;
    """)

    df = pd.read_sql_query(query, engine)
    if len(df) < 2:
        return None

    rows = list(df.itertuples(index=False))

    segments: list[TransitSegment] = []
    edges = list(zip(rows, rows[1:]))
    for line, group in groupby(edges, key=lambda fr_to: fr_to[0].line):
        if type(line) is not str and math.isnan(line):
            line = None
        group = list(group)
        nodes = [(group[0][0].lon, group[0][0].lat)] + [(t.lon, t.lat) for _, t in group]
        cost = sum(float(f.edge_cost) for f, _ in group)
        segments.append(TransitSegment(line=line, nodes=nodes, cost=cost))

    return TransitRoute(segments=segments, cost=float(df["agg_cost"].iloc[-1]))


def calculate_shortest_route_pr(source: tuple[float, float], target: tuple[float, float]) -> PrRoute:
    engine = database.DatabaseManager.engine

    pr_nodes = pd.read_sql_query("""
        SELECT
            p.id,
            p.x,
            p.y,
            r.x as road_node_x,
            r.y as road_node_y,
            t.x as transit_node_x,
            t.y as transit_node_y 
        FROM pr_nodes p
        JOIN road_nodes r ON p.road_node = r.id
        JOIN transit_nodes t ON p.transit_node = t.id;
    """, engine)

    routes: list[Route] = []
    for _, pr in pr_nodes.iterrows():
        road_route = calculate_shortest_route_road(
            source=source,
            target=(pr['road_node_x'], pr['road_node_y'])
        )
        transit_route = calculate_shortest_route_transit(
            source=(pr['transit_node_x'], pr['transit_node_y']),
            target=target
        )

        routes.append(PrRoute(
            road_route=road_route,
            transit_route=transit_route,
            pr_node=(pr['x'], pr['y']),
            cost=road_route.cost+transit_route.cost
        ))

    return min(routes, key=lambda x: x.cost)
