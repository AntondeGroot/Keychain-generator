"""Smooth curves through a traced edge, the way one would draw it by hand with splines.

An edge is cut at its sharp corners. Each piece in between becomes a cubic spline with as few
segments as keep it within a tolerance of the traced points: one or two for a simple curve,
so four or five control points, and as many as a detailed edge such as curly fur needs, down
to one per printed line width. Pixel steps and JPEG wobble disappear while corners stay sharp.
A closed edge without corners that an ellipse fits, such as an eye, becomes that ellipse.

The tolerance may differ along the edge, so an area painted as detailed keeps more of its
shape than one painted as smooth."""

import math

import numpy as np
from scipy.interpolate import make_lsq_spline
from scipy.spatial import cKDTree
from skimage.measure import EllipseModel

CORNER_DEGREES = 55  # a turn this sharp, over the corner window, is a corner, not a curve
# How far to look either side of a point to judge its turn. Shorter windows mistake JPEG
# noise for corners; the ridges of curly fur get their shape from extra segments instead.
CORNER_WINDOW_MM = 0.3
SAMPLE_MM = 0.05  # spacing of the points along the finished curves
SHORTEST_SEGMENT_MM = 0.4  # a printed line: finer segments would only follow noise
GROWTH = 1.5  # each try has this many times more segments, until the curve fits
ELLIPSE_MAX_AREA_MM2 = 12.0  # only small round blobs are tried as ellipses
END_WEIGHT = 100.0  # how firmly a piece's spline holds on to the corners at its ends
DEGREE = 3
MIN_POINTS = 2 * (DEGREE + 1)  # fewer traced points cannot carry a cubic spline


def smooth_ring(points: np.ndarray, tolerance_mm: float | np.ndarray) -> np.ndarray:
    """A closed ring of points in mm, smoothed; the result is closed too (first point repeated).

    The tolerance is one number, or one per point."""
    tolerances = np.broadcast_to(np.asarray(tolerance_mm, dtype=float), (len(points),))
    moves = _moves(points)
    ring, tolerances = points[moves], tolerances[moves]
    if len(ring) < MIN_POINTS:
        return points
    corners = _corners(ring)
    if not corners:
        return _closed_curve(ring, tolerances)
    ends = list(zip(corners, corners[1:] + corners[:1], strict=True))
    pieces = [_fitted(_piece(ring, start, end), _piece(tolerances, start, end))[:-1] for start, end in ends]
    curve = np.concatenate(pieces)
    return np.vstack([curve, curve[:1]])


def _closed_curve(ring: np.ndarray, tolerances: np.ndarray) -> np.ndarray:
    """An edge without corners: the fitted ellipse if it is one, otherwise one closed spline."""
    ellipse = _ellipse(ring, tolerances)
    if ellipse is not None:
        return ellipse
    return _fitted(np.vstack([ring, ring[:1]]), np.append(tolerances, tolerances[0]), closed=True)


def _moves(points: np.ndarray) -> np.ndarray:
    """Which points differ from the next one; a repeated point has no direction."""
    steps = np.linalg.norm(np.diff(points, axis=0, append=points[:1]), axis=1)
    return steps > 0


def _corners(ring: np.ndarray) -> list[int]:
    """Indices of points where the edge turns sharply: the sharpest point of each sharp bend."""
    step_mm = np.median(np.linalg.norm(np.diff(ring, axis=0), axis=1))
    reach = max(1, round(CORNER_WINDOW_MM / step_mm))
    before = ring - np.roll(ring, reach, axis=0)
    after = np.roll(ring, -reach, axis=0) - ring
    cosine = np.sum(before * after, axis=1) / (np.linalg.norm(before, axis=1) * np.linalg.norm(after, axis=1))
    turn = np.degrees(np.arccos(np.clip(cosine, -1, 1)))
    is_peak = turn == np.max([np.roll(turn, shift) for shift in range(-reach, reach + 1)], axis=0)
    return [int(index) for index in np.nonzero(is_peak & (turn >= CORNER_DEGREES))[0]]


def _piece(ring: np.ndarray, start: int, end: int) -> np.ndarray:
    """The values from one corner to the next, both included, going round the ring."""
    if end > start:
        return ring[start : end + 1]
    return np.concatenate([ring[start:], ring[: end + 1]])


def _fitted(points: np.ndarray, tolerances: np.ndarray, closed: bool = False) -> np.ndarray:
    """The spline with the fewest segments that stays within each point's tolerance."""
    if len(points) < MIN_POINTS:
        return points
    along = _arc_length_fraction(points)
    most = max(1, int(_length(points) / SHORTEST_SEGMENT_MM))
    segments = 1
    curve = _spline_curve(points, along, segments, closed)
    while not _fits(points, tolerances, curve) and segments < most:
        segments = min(most, math.ceil(segments * GROWTH))
        curve = _spline_curve(points, along, segments, closed)
    if not closed:
        curve[[0, -1]] = points[[0, -1]]  # exactly on the corners, so neighbouring pieces meet
    return curve


def _spline_curve(points: np.ndarray, along: np.ndarray, segments: int, closed: bool) -> np.ndarray:
    samples = np.linspace(0, 1, _sample_count(points))
    if closed:
        curve = _closed_spline(points, along, segments)(samples)
        curve[-1] = curve[0]
        return curve
    return _open_spline(points, along, segments)(samples)


def _open_spline(points: np.ndarray, along: np.ndarray, segments: int):
    weights = np.ones(len(points))
    weights[[0, -1]] = END_WEIGHT
    return make_lsq_spline(along, points, _knots(0, 1, segments), k=DEGREE, w=weights)


def _closed_spline(points: np.ndarray, along: np.ndarray, segments: int):
    """Fitted to the ring with a copy of itself before and after, so that where its two ends
    meet, the curve runs on smoothly instead of bending."""
    along = np.concatenate([along - 1, along[1:], along[1:] + 1])
    points = np.vstack([points, points[1:], points[1:]])
    return make_lsq_spline(along, points, _knots(-1, 2, 3 * segments), k=DEGREE)


def _knots(start: float, end: float, segments: int) -> np.ndarray:
    """Evenly spread knots; the end knots repeat so the spline starts and ends on the data."""
    inner = np.linspace(start, end, segments + 1)
    return np.concatenate([[start] * DEGREE, inner, [end] * DEGREE])


def _arc_length_fraction(points: np.ndarray) -> np.ndarray:
    steps = np.linalg.norm(np.diff(points, axis=0), axis=1)
    distance = np.concatenate([[0], np.cumsum(steps)])
    return distance / distance[-1]


def _fits(points: np.ndarray, tolerances: np.ndarray, curve: np.ndarray) -> bool:
    distances, _ = cKDTree(curve).query(points)
    return bool(np.all(distances <= tolerances))


def _ellipse(ring: np.ndarray, tolerances: np.ndarray) -> np.ndarray | None:
    """The fitted ellipse if the ring is small and every point lies within its tolerance of it."""
    if _area(ring) > ELLIPSE_MAX_AREA_MM2:
        return None
    try:
        model = EllipseModel.from_estimate(ring)
    except (TypeError, ValueError):  # the fit breaks down on shapes far from an ellipse
        return None
    if not model or np.any(np.abs(model.residuals(ring)) > tolerances):
        return None
    return model.predict_xy(np.linspace(0, 2 * np.pi, _sample_count(ring)))


def _sample_count(points: np.ndarray) -> int:
    return max(MIN_POINTS, round(_length(points) / SAMPLE_MM))


def _length(points: np.ndarray) -> float:
    return float(np.sum(np.linalg.norm(np.diff(points, axis=0), axis=1)))


def _area(ring: np.ndarray) -> float:
    x, y = ring.T
    return abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1))) / 2
