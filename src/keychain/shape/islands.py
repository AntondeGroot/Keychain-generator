"""Handing loose specks of colour that cannot be printed to the colour around them.

Adapted from the Tock lid generator. There it also took pieces that were partly too thin;
here the colour map already thickens or removes narrow areas, and what is left narrow is the
tapered end of a line, like an eyebrow, which must stay."""

import math
from dataclasses import replace

from shapely.geometry.base import BaseGeometry

from keychain.shape.layer import Layer, areas_only

# Larger loose pieces are left alone: checking them is slow, and they always have a core.
LARGEST_SPECK_DOTS = 8
BORDER_TOLERANCE_MM = 1e-4  # how close two edges must be to count as a shared border


def without_unprintable_islands(layers: list[Layer], min_line_mm: float) -> list[Layer]:
    """Hands every loose piece too small to print to the layer that surrounds it most."""
    shapes = [layer.shape for layer in layers]
    for index in range(len(shapes)):
        for island in _unprintable_islands(shapes[index], min_line_mm):
            others = [other for other in range(len(shapes)) if other != index]
            neighbour = max(others, key=lambda other: _shared_border_mm(island, shapes[other]))
            shapes[index] = areas_only(shapes[index].difference(island))
            shapes[neighbour] = areas_only(shapes[neighbour].union(island))
    return [replace(layer, shape=shape) for layer, shape in zip(layers, shapes, strict=True)]


def _unprintable_islands(shape: BaseGeometry, min_line_mm: float) -> list[BaseGeometry]:
    """Loose pieces whose printable core is smaller than a dot two lines across."""
    smallest_dot_mm2 = math.pi * min_line_mm**2
    candidates = [piece for piece in _pieces(shape) if piece.area < LARGEST_SPECK_DOTS * smallest_dot_mm2]
    return [piece for piece in candidates if _printable_core_mm2(piece, min_line_mm) < smallest_dot_mm2]


def _printable_core_mm2(piece: BaseGeometry, min_line_mm: float) -> float:
    radius = min_line_mm / 2
    return piece.buffer(-radius).buffer(radius).area


def _shared_border_mm(island: BaseGeometry, shape: BaseGeometry) -> float:
    return shape.boundary.intersection(island.buffer(BORDER_TOLERANCE_MM)).length


def _pieces(shape: BaseGeometry) -> list[BaseGeometry]:
    return list(getattr(shape, "geoms", [shape]))
