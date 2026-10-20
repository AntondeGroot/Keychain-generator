"""Lines drawn by hand from A to B to say: this area is continuous, join it up here.

A strip of hair can fade so much in a picture that for a few pixels it looks like skin, which
splits the hair in two. No rule can tell that apart from real skin, but a person can: a line
from the hair on one side to the hair on the other gets a strip of that colour."""

import numpy as np
from PIL import Image, ImageDraw

from keychain.picture.masks import grown

Point = tuple[float, float]  # (x, y) in pixels of the original picture
Connection = tuple[Point, Point]
STRIP_LINES = 1.5  # the strip is this many printed lines wide, so it prints for sure


def with_connections(
    labels: np.ndarray,
    inside: np.ndarray,
    connections: list[Connection],
    factor: int,
    ink: int,
    line_px: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Labels and inside with a strip along every connection, in the colour where it starts.

    A strip in another colour than ink does not cover ink, so lines it crosses stay whole."""
    labels, inside = labels.copy(), inside.copy()
    for start, end in connections:
        first, last = _enlarged(start, factor), _enlarged(end, factor)
        colour = _colour_at(labels, inside, first, last, ink)
        if colour is None:
            continue
        strip = grown(_line(labels.shape, first, last), STRIP_LINES * line_px / 2)
        if colour != ink:
            strip &= labels != ink
        labels[strip] = colour
        inside |= strip
    return labels, inside


def _colour_at(labels: np.ndarray, inside: np.ndarray, first: Point, last: Point, ink: int) -> int | None:
    """The colour at the start, or at the end when the start is ink or outside the picture."""
    colours = [_label(labels, inside, point) for point in (first, last)]
    for colour in colours:
        if colour is not None and colour != ink:
            return colour
    return next((colour for colour in colours if colour is not None), None)


def _label(labels: np.ndarray, inside: np.ndarray, point: Point) -> int | None:
    column, row = (round(value) for value in point)
    if not (0 <= row < labels.shape[0] and 0 <= column < labels.shape[1]) or not inside[row, column]:
        return None
    return int(labels[row, column])


def _enlarged(point: Point, factor: int) -> Point:
    """The middle of the original pixel, in the enlarged picture."""
    x, y = point
    return (x + 0.5) * factor - 0.5, (y + 0.5) * factor - 0.5


def _line(shape: tuple[int, int], start: Point, end: Point) -> np.ndarray:
    """A one pixel wide line between two (x, y) points, as a mask."""
    canvas = Image.new("1", (shape[1], shape[0]))
    ImageDraw.Draw(canvas).line([start, end], fill=1)
    return np.asarray(canvas)
