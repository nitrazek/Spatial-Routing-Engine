from enum import StrEnum


class RouteMode(StrEnum):
    CAR = "CAR"
    PUBLIC = "PUBLIC"
    PR = "PR"


class NodeType(StrEnum):
    START = "START"
    INTERMEDIATE = "INTERMEDIATE"
    END = "END"