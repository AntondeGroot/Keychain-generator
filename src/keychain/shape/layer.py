"""One colour of one face of the keychain."""

from dataclasses import dataclass

import shapely
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry


@dataclass(frozen=True)
class Layer:
    name: str
    shape: BaseGeometry
    colour: str


def areas_only(shape: BaseGeometry) -> MultiPolygon:
    """Where two edges touch exactly, shapely adds the lines and points they share; only the
    areas can be printed."""
    return MultiPolygon([part for part in shapely.get_parts(shape) if isinstance(part, Polygon)])
