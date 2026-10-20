"""Handing loose specks of colour that cannot be printed to the colour around them.

Taken from the Tock lid generator, where it keeps outline rings free of unprintable dots."""

import math
from dataclasses import replace

from shapely.geometry.base import BaseGeometry

from keychain.shape.layer import Layer

# Larger loose pieces are left alone: checking them is slow, and the raster step already
# removed areas thinner than a line.
LARGEST_SLIVER_DOTS = 8
# Every sharp corner leaves a tip of at most ~0.06 mm² that the check cannot tell apart from
# a real problem; a needle or strip the printer would actually botch is several times larger.
NOTICEABLE_SPOT_MM2 = 0.1
BORDER_TOLERANCE_MM = 1e-4  # how close two edges must be to count as a shared border


def without_unprintable_islands(layers: list[Layer], min_line_mm: float) -> list[Layer]:
    """Hands every loose piece too small or thin to print to the layer that surrounds it most."""
    shapes = [layer.shape for layer in layers]
    for index in range(len(shapes)):
        for island in _unprintable_islands(shapes[index], min_line_mm):
            others = [other for other in range(len(shapes)) if other != index]
            neighbour = max(others, key=lambda other: _shared_border_mm(island, shapes[other]))
            shapes[index] = shapes[index].difference(island)
            shapes[neighbour] = shapes[neighbour].union(island)
    return [replace(layer, shape=shape) for layer, shape in zip(layers, shapes, strict=True)]


def _unprintable_islands(shape: BaseGeometry, min_line_mm: float) -> list[BaseGeometry]:
    """Loose pieces whose printable core is under a dot two lines across, or that are mostly thin."""
    smallest_dot_mm2 = math.pi * min_line_mm**2
    candidates = [piece for piece in _pieces(shape) if piece.area < LARGEST_SLIVER_DOTS * smallest_dot_mm2]
    return [piece for piece in candidates if _is_unprintable(piece, smallest_dot_mm2, min_line_mm)]


def _is_unprintable(piece: BaseGeometry, smallest_dot_mm2: float, min_line_mm: float) -> bool:
    radius = min_line_mm / 2
    core_mm2 = piece.buffer(-radius).buffer(radius).area
    return core_mm2 < smallest_dot_mm2 or piece.area - core_mm2 > NOTICEABLE_SPOT_MM2


def _shared_border_mm(island: BaseGeometry, shape: BaseGeometry) -> float:
    return shape.boundary.intersection(island.buffer(BORDER_TOLERANCE_MM)).length


def _pieces(shape: BaseGeometry) -> list[BaseGeometry]:
    return list(getattr(shape, "geoms", [shape]))
