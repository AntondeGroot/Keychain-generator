"""Areas closed off by curves drawn by hand, such as a head of hair drawn round with edges that
start and end on each other: each such area gets one colour, so nothing of the picture's own
rough borders is left inside it."""

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

from keychain.picture.masks import grown

CURVE_WIDTH_PX = 3  # wide enough that two curves meeting at a point close the area between them


def with_enclosed_areas(
    current: np.ndarray, before: np.ndarray, curves: list[np.ndarray], keep: int
) -> np.ndarray:
    """Every area the curves close off, in one colour: the most common one in it. Colour that
    reaches the curves round the area takes that colour; details within it that do not, such as
    the eyes in a face, stay. Current holds a value per pixel, and pixels with the keep value,
    such as the drawn shapes, stay as they are.

    What reaches the curves is also looked for in the picture as it was before, as the edges
    may have painted over where a patch of colour met them.

    The curves are (x, y) samples in the pixels of current. The pixels on a curve take the
    colour of the nearest pixel beside it, so the border between two areas is the curve itself."""
    on_curve = _drawn_curves(current.shape, curves)
    areas, count = ndimage.label(~on_curve)
    edge_of_picture = np.unique(np.concatenate([areas[0], areas[-1], areas[:, 0], areas[:, -1]]))
    current = current.copy()
    filled = np.zeros(current.shape, dtype=bool)
    for area in sorted(set(range(1, count + 1)) - set(edge_of_picture.tolist())):
        filled |= _one_colour(current, before, areas == area, on_curve, keep)
    _, (rows, columns) = ndimage.distance_transform_edt(on_curve, return_indices=True)
    beside = on_curve & filled[rows, columns] & (current != keep)
    current[beside] = current[rows[beside], columns[beside]]
    return current


def _one_colour(
    current: np.ndarray, before: np.ndarray, area: np.ndarray, on_curve: np.ndarray, keep: int
) -> np.ndarray:
    """Gives the colour that reaches the curves round the area, now or before, the area's most
    common colour; the area if it has one, else nothing."""
    values = current[area & (current != keep)]
    if not len(values):
        return np.zeros(current.shape, dtype=bool)
    found, counts = np.unique(values, return_counts=True)
    main = found[np.argmax(counts)]
    for picture in (before, current):
        pieces, _ = ndimage.label(area & (picture != main) & (picture != keep))
        reaching = np.unique(pieces[grown(on_curve, 1) & (pieces > 0)])
        current[np.isin(pieces, reaching) & (pieces > 0) & (current != keep)] = main
    return area


def _drawn_curves(shape: tuple[int, int], curves: list[np.ndarray]) -> np.ndarray:
    canvas = Image.new("1", (shape[1], shape[0]))
    draw = ImageDraw.Draw(canvas)
    for curve in curves:
        draw.line([tuple(point) for point in curve], fill=1, width=CURVE_WIDTH_PX)
    return np.asarray(canvas)
