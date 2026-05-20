from enum import StrEnum


class RouteMode(StrEnum):
    CAR = "CAR"
    PUBLIC = "PUBLIC"
    PR = "PR"
    WALK = "WALK"


class NodeType(StrEnum):
    START = "START"
    INTERMEDIATE = "INTERMEDIATE"
    END = "END"