from dataclasses import dataclass

import pandas as pd
from sqlalchemy import Engine
from sqlmodel import text

from src import database


@dataclass
class ShortestRoute:
    nodes: list[tuple[float, float]]
    cost: float


@dataclass
class PrShortestRoute(ShortestRoute):
    pr_node: tuple[float, float]


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


def calculate_shortest_route_road():
    pass


def calculate_shortest_route_transit():
    pass


def calculate_shortest_route_pr(source: tuple[float, float], target: tuple[float, float]) -> ShortestRoute:
    engine = database.DatabaseManager.engine

    source_id = get_nearest_node(
        x=source[1],
        y=source[0],
        engine=engine,
        nodes_table_name="road_nodes"
    )
    target_id = get_nearest_node(
        x=target[1],
        y=target[0],
        engine=engine,
        nodes_table_name="transit_nodes"
    )

    pr_nodes = pd.read_sql_query("""
        SELECT id, x, y, road_node, transit_node 
        FROM pr_nodes;
    """, engine)

    routes: list[ShortestRoute] = []
    for _, pr in pr_nodes.iterrows():
        road_route_df = run_dijkstra(
            source=source_id,
            target=pr['road_node'],
            engine=engine,
            edges_table_name="road_edges",
            nodes_table_name="road_nodes"
        )
        transit_route_df = run_dijkstra(
            source=pr['transit_node'],
            target=target_id,
            engine=engine,
            edges_table_name="transit_edges",
            nodes_table_name="transit_nodes"
        )

        if road_route_df.empty or transit_route_df.empty:
            continue

        nodes = list(zip(road_route_df['y'], road_route_df['x'])) + list(zip(transit_route_df['y'], transit_route_df['x']))
        cost = road_route_df['agg_cost'].iloc[-1] + transit_route_df['agg_cost'].iloc[-1]
        routes.append(PrShortestRoute(nodes=nodes, cost=cost, pr_node=(pr['y'], pr['x'])))

    return min(routes, key=lambda x: x.cost)
