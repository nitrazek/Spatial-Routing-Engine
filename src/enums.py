from enum import StrEnum


class RouteMode(StrEnum):
    CAR = "CAR"
    PUBLIC = "PUBLIC"
    PR = "PR"
    WALK_PUBLIC = "WALK_PUBLIC"
    WALK_PR = "WALK_PR"


class NodeType(StrEnum):
    START = "START"
    INTERMEDIATE = "INTERMEDIATE"
    END = "END"