"""Curves drawn by hand over the picture, for edges the picture itself does not show cleanly.

An edge is an open curve from A to B through a few points: along it, the border between the
colours on either side follows the curve exactly, such as the outer edge of a head of hair. A
shape is a closed curve filled with one colour, such as a pill-shaped strand of a quiff. Both
are Catmull-Rom splines through the clicked points; the page draws the same curve."""

from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw
from scipy.spatial import cKDTree

from keychain.picture.palette import Colour

Point = tuple[float, float]  # (x, y) in pixels of the original picture
SAMPLES_PER_SPAN = 24  # points of the curve between two clicked points
EDGE_BAND_MM = 0.6  # pixels this close to an edge go to the colour on their side of it
SIDE_REACH = 2  # a side's colour is read beyond the band, up to this many band widths away
OUTSIDE = -1  # the side of an edge that is background
LEFT, RIGHT = -1, 1
SAMPLE_PX = 1.0  # spacing of the curve points used to find the nearest spot on it


@dataclass(frozen=True)
class Shape:
    points: tuple[Point, ...]
    colour: str  # hex, matched to the nearest palette colour


def spline(points: list[Point] | tuple[Point, ...], closed: bool) -> np.ndarray:
    """A Catmull-Rom curve through the points, as (x, y) samples."""
    ring = np.asarray(points, dtype=float)
    if len(ring) < 2:
        return ring
    padded = np.vstack([ring[-1:], ring, ring[:2]]) if closed else np.vstack([ring[:1], ring, ring[-1:]])
    spans = len(ring) if closed else len(ring) - 1
    t = np.linspace(0, 1, SAMPLES_PER_SPAN, endpoint=False)[:, None]
    pieces = [_span(padded[i : i + 4], t) for i in range(spans)]
    end = padded[1:2] if closed else ring[-1:]
    return np.vstack([*pieces, end])


def with_shapes(
    labels: np.ndarray, inside: np.ndarray, shapes: tuple[Shape, ...], palette: list[Colour], factor: int
) -> tuple[np.ndarray, np.ndarray]:
    """Each shape filled with its colour, on top of the picture; it counts as part of it."""
    labels, inside = labels.copy(), inside.copy()
    for shape in shapes:
        filled = _polygon_mask(labels.shape, _enlarged(spline(shape.points, closed=True), factor))
        labels[filled] = _nearest_index(shape.colour, palette)
        inside |= filled
    return labels, inside


def with_edges(
    labels: np.ndarray,
    inside: np.ndarray,
    edges: tuple[tuple[Point, ...], ...],
    factor: int,
    mm_per_px: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Along each edge, every pixel close to it takes the colour of its own side.

    The colour of a side is what lies there now, just beyond the band: the two colours whose
    border the edge redraws. A side that is background makes those pixels background."""
    current = np.where(inside, labels, OUTSIDE)
    band_px = EDGE_BAND_MM / mm_per_px
    for points in edges:
        band = _band(_enlarged(spline(points, closed=False), factor), current.shape, band_px)
        colours = [band.colour_on(side, current) for side in (LEFT, RIGHT)]
        if colours[0] == colours[1]:
            continue  # nothing to separate here
        for side, colour in zip((LEFT, RIGHT), colours, strict=True):
            on_side = (band.sides == side) & (band.distances <= band_px)
            current[band.rows[on_side], band.columns[on_side]] = colour
    return np.where(current == OUTSIDE, labels, current), current != OUTSIDE


@dataclass(frozen=True)
class Band:
    """The pixels close to an edge, with the side of the edge each lies on and how close."""

    rows: np.ndarray
    columns: np.ndarray
    sides: np.ndarray  # LEFT or RIGHT, looking along the edge from A to B
    distances: np.ndarray
    width_px: float

    def colour_on(self, side: int, current: np.ndarray) -> int:
        """The most common colour on one side, just beyond the band, where the edge does not reach."""
        away = (self.sides == side) & (self.distances > self.width_px)
        values = current[self.rows[away], self.columns[away]]
        if not len(values):
            return OUTSIDE
        found, counts = np.unique(values, return_counts=True)
        return int(found[np.argmax(counts)])


def _span(four: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Uniform Catmull-Rom between the middle two of four points."""
    p0, p1, p2, p3 = four
    return 0.5 * (
        2 * p1 + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t**2 + (3 * p1 - p0 - 3 * p2 + p3) * t**3
    )


def _band(curve: np.ndarray, shape: tuple[int, int], band_px: float) -> Band:
    """The pixels along the curve, out to where the sides' colours are read. Those beyond its two
    ends are left out, so the edge does not round off at its ends."""
    reach_px = SIDE_REACH * band_px
    rows, columns = np.nonzero(_polyline_mask(shape, curve, 2 * reach_px))
    pixels = np.column_stack([columns, rows]).astype(float)
    dense = _resampled(curve, SAMPLE_PX)
    distances, nearest = cKDTree(dense).query(pixels)
    tangents = np.gradient(dense, axis=0)
    offsets = pixels - dense[nearest]
    cross = tangents[nearest, 0] * offsets[:, 1] - tangents[nearest, 1] * offsets[:, 0]
    along = np.einsum("pk,pk->p", tangents[nearest], offsets)
    beyond_ends = ((nearest == 0) & (along < 0)) | ((nearest == len(dense) - 1) & (along > 0))
    keep = ~beyond_ends & (distances <= reach_px)
    sides = np.where(cross[keep] < 0, LEFT, RIGHT)
    return Band(rows[keep], columns[keep], sides, distances[keep], band_px)


def _resampled(curve: np.ndarray, spacing_px: float) -> np.ndarray:
    """The curve with a point about every spacing, so the nearest point is close to the nearest spot."""
    steps = np.linalg.norm(np.diff(curve, axis=0), axis=1)
    along = np.concatenate([[0], np.cumsum(steps)])
    wanted = np.linspace(0, along[-1], max(2, int(along[-1] / spacing_px) + 1))
    return np.column_stack([np.interp(wanted, along, curve[:, axis]) for axis in range(2)])


def _nearest_index(hex_code: str, palette: list[Colour]) -> int:
    rgb = np.array([int(hex_code[i : i + 2], 16) for i in (1, 3, 5)])
    return int(np.argmin([np.linalg.norm(rgb - np.array(colour.rgb)) for colour in palette]))


def _enlarged(curve: np.ndarray, factor: int) -> np.ndarray:
    """The middle of the original pixels, in the enlarged picture."""
    return (curve + 0.5) * factor - 0.5


def _polygon_mask(shape: tuple[int, int], points: np.ndarray) -> np.ndarray:
    canvas = Image.new("1", (shape[1], shape[0]))
    ImageDraw.Draw(canvas).polygon([tuple(point) for point in points], fill=1)
    return np.asarray(canvas)


def _polyline_mask(shape: tuple[int, int], points: np.ndarray, width_px: float) -> np.ndarray:
    canvas = Image.new("1", (shape[1], shape[0]))
    ImageDraw.Draw(canvas).line(
        [tuple(point) for point in points], fill=1, width=max(1, round(width_px)), joint="curve"
    )
    return np.asarray(canvas)
