"""Pixel masks to smooth polygons in millimetres, drawn as splines."""

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry
from skimage import measure

from keychain.picture.curves import smooth_ring
from keychain.spec import KeychainSpec

MIN_RING_POINTS = 4  # fewer cannot enclose an area
PADDING = 1  # empty pixels around the mask, so areas touching the image border get closed rings
Tolerances = Callable[[np.ndarray, np.ndarray, float], np.ndarray]  # rows, columns, base tolerance
EDGE_LEVEL = 0.5  # the outline runs halfway between a pixel inside and one outside


def traced(
    mask: np.ndarray,
    mm_per_px: float,
    centre_px: tuple[float, float],
    spec: KeychainSpec,
    tolerances_at: Tolerances | None = None,
) -> BaseGeometry:
    """The mask's areas as polygons in mm, y up, with the centre pixel at (0, 0).

    With tolerances_at, each edge point gets the curve tolerance of its pixel.

    Every edge comes out as a ring, and a ring inside a ring is a hole, so combining them all
    with XOR gives the areas with their holes."""
    padded = np.pad(mask, PADDING).astype(float)
    shape: BaseGeometry = Polygon()
    for contour in measure.find_contours(padded, EDGE_LEVEL):
        if len(contour) >= MIN_RING_POINTS:
            tolerances = _tolerances(contour, mask.shape, tolerances_at, spec.curve_tolerance_mm)
            curve = smooth_ring(_in_mm(contour, mm_per_px, centre_px), tolerances)
            shape = shape.symmetric_difference(Polygon(curve).buffer(0))
    # The curves are sampled densely; along smooth stretches most points add nothing.
    return shape.simplify(spec.simplify_mm)


@dataclass(frozen=True)
class Placement:
    """Where the page's picture lands in mm: it was traced enlarged by a factor, with the middle
    of what is kept at (0, 0)."""

    mm_per_px: float  # of the enlarged picture
    factor: int
    centre: tuple[float, float]  # row and column of the enlarged picture

    def in_mm(self, x: float, y: float) -> tuple[float, float]:
        """A point on the page's picture, x right and y down, with pixel i from i to i + 1; the
        enlarged pixels are counted by their middles, as the traced edges are."""
        row, column = y * self.factor - 0.5, x * self.factor - 0.5
        centre_row, centre_column = self.centre
        return (column - centre_column) * self.mm_per_px, -(row - centre_row) * self.mm_per_px

    def shift_in_mm(self, x: float, y: float) -> tuple[float, float]:
        """A move on the page's picture, x right and y down."""
        mm_per_page_px = self.mm_per_px * self.factor
        return x * mm_per_page_px, -y * mm_per_page_px


def centre_px(mask: np.ndarray) -> tuple[float, float]:
    """The middle of the mask's bounding box, as (row, column)."""
    rows, columns = np.nonzero(mask)
    return (rows.min() + rows.max()) / 2, (columns.min() + columns.max()) / 2


def _tolerances(
    contour: np.ndarray, shape: tuple[int, int], tolerances_at: Tolerances | None, tolerance_mm: float
) -> np.ndarray | float:
    if tolerances_at is None:
        return tolerance_mm
    rows, columns = (np.clip(np.round(contour - PADDING).astype(int), 0, np.array(shape) - 1)).T
    return tolerances_at(rows, columns, tolerance_mm)


def _in_mm(contour: np.ndarray, mm_per_px: float, centre: tuple[float, float]) -> np.ndarray:
    centre_row, centre_column = centre
    rows = contour[:, 0] - PADDING - centre_row
    columns = contour[:, 1] - PADDING - centre_column
    return np.column_stack([columns, -rows]) * mm_per_px
