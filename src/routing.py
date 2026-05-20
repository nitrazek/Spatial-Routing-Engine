from dataclasses import dataclass
from textwrap import dedent

import pandas as pd
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
    
    query = dedent(f"""\
        SELECT *
        FROM pgr_Dijkstra(
            'SELECT id, source, target, cost, reverse_cost FROM road_edges',
            {source_id}, {target_id},
            directed => false
        );
    """)

    try:
        df = pd.read_sql_query(query, engine)
        print(df)
    except Exception as e:
        print(f"Błąd połączenia: {e}")


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
