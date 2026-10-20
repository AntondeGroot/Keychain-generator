"""Pixel masks to smooth polygons in millimetres, drawn as splines."""

import numpy as np
from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry
from skimage import measure

from keychain.picture.curves import smooth_ring
from keychain.spec import KeychainSpec

MIN_RING_POINTS = 4  # fewer cannot enclose an area
EDGE_LEVEL = 0.5  # the outline runs halfway between a pixel inside and one outside


def traced(mask: np.ndarray, mm_per_px: float, centre_px: tuple[float, float], spec: KeychainSpec):
    """The mask's areas as polygons in mm, y up, with the centre pixel at (0, 0).

    Every edge comes out as a ring, and a ring inside a ring is a hole, so combining them all
    with XOR gives the areas with their holes."""
    padded = np.pad(mask, 1).astype(float)  # so areas touching the image border get closed rings
    shape: BaseGeometry = Polygon()
    for contour in measure.find_contours(padded, EDGE_LEVEL):
        if len(contour) >= MIN_RING_POINTS:
            curve = smooth_ring(_in_mm(contour, mm_per_px, centre_px), spec.curve_tolerance_mm)
            shape = shape.symmetric_difference(Polygon(curve).buffer(0))
    # The curves are sampled densely; along smooth stretches most points add nothing.
    return shape.simplify(spec.simplify_mm)


def centre_px(mask: np.ndarray) -> tuple[float, float]:
    """The middle of the mask's bounding box, as (row, column)."""
    rows, columns = np.nonzero(mask)
    return (rows.min() + rows.max()) / 2, (columns.min() + columns.max()) / 2


def _in_mm(contour: np.ndarray, mm_per_px: float, centre: tuple[float, float]) -> np.ndarray:
    centre_row, centre_column = centre
    padding = 1
    rows = contour[:, 0] - padding - centre_row
    columns = contour[:, 1] - padding - centre_column
    return np.column_stack([columns, -rows]) * mm_per_px
