"""Handing loose specks of colour that cannot be printed to the colour around them.

Adapted from the Tock lid generator. There it also took pieces that were partly too thin;
here the colour map already thickens or removes narrow areas, and what is left narrow is the
tapered end of a line, like an eyebrow, which must stay."""

import math
from collections import defaultdict
from dataclasses import replace

from shapely.geometry import MultiPolygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from keychain.shape.layer import Layer, areas_only

# Larger loose pieces are left alone: checking them is slow, and they always have a core.
LARGEST_SPECK_DOTS = 8
BORDER_TOLERANCE_MM = 1e-4  # how close two edges must be to count as a shared border


def without_unprintable_islands(layers: list[Layer], min_line_mm: float) -> list[Layer]:
    """Hands every loose piece too small to print to the layer that surrounds it most.

    A layer's pieces move all at once, with one union for each layer they go to: one for each
    piece took seconds for a picture with a thousand specks."""
    shapes = [layer.shape for layer in layers]
    for index in range(len(shapes)):
        kept, islands = _split(shapes[index], min_line_mm)
        if not islands:
            continue
        borders = {other: shapes[other].boundary for other in range(len(shapes)) if other != index}
        going_to = defaultdict(list)
        for island in islands:
            going_to[max(borders, key=lambda other: _shared_border_mm(island, borders[other]))].append(island)
        shapes[index] = areas_only(MultiPolygon(kept))
        for neighbour, moving in going_to.items():
            shapes[neighbour] = areas_only(unary_union([shapes[neighbour], *moving]))
    return [replace(layer, shape=shape) for layer, shape in zip(layers, shapes, strict=True)]


def _split(shape: BaseGeometry, min_line_mm: float) -> tuple[list[BaseGeometry], list[BaseGeometry]]:
    """The shape's loose pieces: the ones to keep, and the islands whose printable core is
    smaller than a dot two lines across."""
    smallest_dot_mm2 = math.pi * min_line_mm**2
    kept, islands = [], []
    for piece in _pieces(shape):
        small = piece.area < LARGEST_SPECK_DOTS * smallest_dot_mm2
        unprintable = small and _printable_core_mm2(piece, min_line_mm) < smallest_dot_mm2
        (islands if unprintable else kept).append(piece)
    return kept, islands


def _printable_core_mm2(piece: BaseGeometry, min_line_mm: float) -> float:
    radius = min_line_mm / 2
    return piece.buffer(-radius).buffer(radius).area


def _shared_border_mm(island: BaseGeometry, border: BaseGeometry) -> float:
    return border.intersection(island.buffer(BORDER_TOLERANCE_MM)).length


def _pieces(shape: BaseGeometry) -> list[BaseGeometry]:
    return list(getattr(shape, "geoms", [shape]))
