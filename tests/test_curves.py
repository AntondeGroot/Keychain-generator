import numpy as np
import pytest
from shapely.geometry import LinearRing, Point, box

from keychain.picture.curves import smooth_ring

TOLERANCE_MM = 0.08
SIDE_MM = 10.0
POINTS_PER_SIDE = 200  # like a traced edge: a point every 0.05 mm


def _wobbly_square() -> np.ndarray:
    """A 10 mm square traced with JPEG-like wobble of a few hundredths of a mm."""
    along = np.linspace(0, SIDE_MM, POINTS_PER_SIDE, endpoint=False)
    zeros, sides = np.zeros_like(along), np.full_like(along, SIDE_MM)
    square = np.concatenate(
        [
            np.column_stack([along, zeros]),
            np.column_stack([sides, along]),
            np.column_stack([SIDE_MM - along, sides]),
            np.column_stack([zeros, SIDE_MM - along]),
        ]
    )
    return square + np.random.default_rng(seed=1).normal(0, 0.02, square.shape)


def test_a_wobbly_square_keeps_its_four_sharp_corners_and_straight_sides():
    curve = smooth_ring(_wobbly_square(), TOLERANCE_MM)

    square_edge = LinearRing(box(0, 0, SIDE_MM, SIDE_MM).exterior.coords)
    largest_wobble_mm = max(square_edge.distance(Point(point)) for point in curve)
    corners = [(0, 0), (SIDE_MM, 0), (SIDE_MM, SIDE_MM), (0, SIDE_MM)]
    nearest_to_corner_mm = [min(np.hypot(*(curve - corner).T)) for corner in corners]
    assert largest_wobble_mm < TOLERANCE_MM
    assert LinearRing(curve).length == pytest.approx(4 * SIDE_MM, rel=0.01)  # no zigzag left
    assert max(nearest_to_corner_mm) < TOLERANCE_MM  # sharp corners, not rounded off


def test_a_curly_edge_keeps_its_ridges_instead_of_becoming_a_smooth_wave():
    # A 10 mm blob with 12 rounded ridges of 0.3 mm all round, like the waves in Snowy's fur:
    # curves, not corners, so the whole edge is one spline that needs many segments.
    ridges, ridge_height_mm, radius_mm = 12, 0.3, 5.0
    angles = np.linspace(0, 2 * np.pi, 1200, endpoint=False)
    radii = radius_mm + ridge_height_mm * np.sin(ridges * angles)
    ridged_edge = np.column_stack([radii * np.cos(angles), radii * np.sin(angles)])
    traced = ridged_edge + np.random.default_rng(seed=1).normal(0, 0.02, ridged_edge.shape)

    curve = smooth_ring(traced, TOLERANCE_MM)

    true_edge = LinearRing(ridged_edge)
    assert max(true_edge.distance(Point(point)) for point in curve) < TOLERANCE_MM
