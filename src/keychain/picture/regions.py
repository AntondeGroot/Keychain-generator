"""From a picture to a map of filament colours, cleaned up so every area can be printed."""

import math
from dataclasses import dataclass

import numpy as np
from PIL import Image
from scipy import ndimage

from keychain.picture.masks import closed, grown, opened
from keychain.picture.nearest import darkest, nearest_colours
from keychain.picture.painted import PaintedMask
from keychain.picture.palette import Colour
from keychain.spec import KeychainSpec

OUTSIDE = -1
TARGET_MM_PER_PX = 0.025  # fine enough that the traced edges show no pixel steps
OPAQUE = 128  # alpha from which a pixel belongs to the picture
SPECK_DOT_LINES = 1.5  # a piece smaller than a dot this many lines across is a speck, not a detail
STRIP_LINES = 2  # a narrow part covering a square this many lines wide is a strip, not a tip


@dataclass(frozen=True)
class ColourMap:
    labels: np.ndarray  # palette index per pixel, OUTSIDE around the picture
    mm_per_px: float
    ink: int  # palette index of the lines, which also colours the rim and the core

    @property
    def inside(self) -> np.ndarray:
        return self.labels != OUTSIDE


def colour_map(
    image: Image.Image, palette: list[Colour], spec: KeychainSpec, painted: PaintedMask | None = None
) -> ColourMap:
    """The picture enlarged until a pixel is about 0.025 mm, with one palette colour per pixel."""
    painted = painted or PaintedMask.nothing_painted(image.size)
    small = _rgba(image)
    side_px = _widest_side_px(painted.applied(_drawn(nearest_colours(small[..., :3], palette), small)))
    factor = max(1, math.ceil(spec.picture_mm / side_px / TARGET_MM_PER_PX))
    rough_mm_per_px = spec.picture_mm / (side_px * factor)
    big = _rgba(image.resize((image.width * factor, image.height * factor), Image.Resampling.BICUBIC))
    big_painted = painted.enlarged(factor)
    labels = nearest_colours(big[..., :3], palette, spec.smoothing_mm / rough_mm_per_px)
    # Painted background comes off only after finding what the drawing encloses: a stroke
    # through an outline would otherwise open it, and the whole inside would count as outside.
    drawn = _drawn(labels, big) | big_painted.keep
    inside = _picture_area(drawn, spec.gap_mm / 2 / rough_mm_per_px) & ~big_painted.background
    # Closing gaps can make the picture a little larger, so the exact scale is measured after.
    mm_per_px = spec.picture_mm / _widest_side_px(inside)
    ink = darkest(palette)
    labels = _with_printable_areas(labels, inside, ink, spec.min_line_mm / 2 / mm_per_px)
    return ColourMap(np.where(inside, labels, OUTSIDE), mm_per_px, ink)


def _rgba(image: Image.Image) -> np.ndarray:
    return np.asarray(image.convert("RGBA"), dtype=float)


def _drawn(labels: np.ndarray, rgba: np.ndarray) -> np.ndarray:
    """The pixels that are not background: opaque ones, or else those unlike the border colour."""
    opaque = rgba[..., 3] >= OPAQUE
    if not opaque.all():
        return opaque
    border = np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]])
    return labels != np.bincount(border).argmax()


def _widest_side_px(mask: np.ndarray) -> int:
    rows, columns = np.nonzero(mask)
    if not len(rows):
        raise ValueError("the picture is empty: every pixel looks like the background")
    return max(np.ptp(rows), np.ptp(columns)) + 1


def _picture_area(drawn: np.ndarray, gap_radius_px: float) -> np.ndarray:
    """The drawing with small openings in its outer line closed, so white parts inside stay in."""
    return ndimage.binary_fill_holes(closed(drawn, gap_radius_px))


def _with_printable_areas(labels: np.ndarray, inside: np.ndarray, ink: int, radius_px: float) -> np.ndarray:
    """Every colour area at least a printed line wide, the way one would fix it by hand.

    Specks, and colour areas that are narrow everywhere (blends along an edge, such as a
    skin-coloured fringe where orange hair fades into white), go to the colours around them.
    Narrow strips of an area that is wide elsewhere, such as hair along a hairline, are
    thickened instead of lost. A colour never grows over ink, so the lines stay whole."""
    labels = labels.copy()
    colours = sorted(set(np.unique(labels[inside]).tolist()) - {ink})
    for index in [ink, *colours]:
        area = (labels == index) & inside
        pieces, _ = ndimage.label(area)
        wide = np.isin(pieces, np.unique(pieces[opened(area, radius_px)]))
        loose = _specks(pieces, radius_px) | (area & ~wide if index != ink else False)
        _give_to_neighbours(labels, loose, inside)
        strips = _strips(area & ~loose & ~opened(area, radius_px), radius_px)
        may_take = inside if index == ink else inside & (labels != ink)
        labels[grown(strips, radius_px) & may_take] = index
    return labels


def _specks(pieces: np.ndarray, radius_px: float) -> np.ndarray:
    """Pieces smaller than a printable dot."""
    sizes = np.bincount(pieces.ravel())
    too_small = np.nonzero(sizes < math.pi * (SPECK_DOT_LINES * radius_px) ** 2)[0]
    return np.isin(pieces, too_small) & (pieces > 0)


def _strips(narrow: np.ndarray, radius_px: float) -> np.ndarray:
    """Narrow parts long enough to be a strip, not the tip of a line or a sharp corner."""
    pieces, _ = ndimage.label(narrow)
    sizes = np.bincount(pieces.ravel())
    long_enough = np.nonzero(sizes >= (STRIP_LINES * 2 * radius_px) ** 2)[0]
    return np.isin(pieces, long_enough) & (pieces > 0)


def _give_to_neighbours(labels: np.ndarray, loose: np.ndarray, inside: np.ndarray) -> None:
    """Each loose pixel takes the colour of the nearest pixel that is not loose."""
    keeping = inside & ~loose
    if not loose.any() or not keeping.any():
        return
    _, (rows, columns) = ndimage.distance_transform_edt(~keeping, return_indices=True)
    labels[loose] = labels[rows[loose], columns[loose]]
