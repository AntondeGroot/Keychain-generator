"""From a picture to a map of filament colours, cleaned up so every area can be printed."""

import math
from dataclasses import dataclass

import numpy as np
from PIL import Image
from scipy import ndimage

from keychain.picture.masks import closed, grown, opened
from keychain.picture.nearest import darkest, nearest_colours
from keychain.picture.palette import Colour
from keychain.spec import KeychainSpec

OUTSIDE = -1
TARGET_MM_PER_PX = 0.025  # fine enough that the traced edges show no pixel steps
SMOOTHING_MM = 0.08  # evens out JPEG noise along colour edges
OPAQUE = 128  # alpha from which a pixel belongs to the picture


@dataclass(frozen=True)
class ColourMap:
    labels: np.ndarray  # palette index per pixel, OUTSIDE around the picture
    mm_per_px: float
    ink: int  # palette index of the lines, which also colours the rim and the core

    @property
    def inside(self) -> np.ndarray:
        return self.labels != OUTSIDE


def colour_map(image: Image.Image, palette: list[Colour], spec: KeychainSpec) -> ColourMap:
    """The picture enlarged until a pixel is about 0.025 mm, with one palette colour per pixel."""
    small = _rgba(image)
    side_px = _widest_side_px(_drawn(nearest_colours(small[..., :3], palette), small))
    factor = max(1, math.ceil(spec.picture_mm / side_px / TARGET_MM_PER_PX))
    rough_mm_per_px = spec.picture_mm / (side_px * factor)
    big = _rgba(image.resize((image.width * factor, image.height * factor), Image.Resampling.BICUBIC))
    labels = nearest_colours(big[..., :3], palette, SMOOTHING_MM / rough_mm_per_px)
    inside = _picture_area(_drawn(labels, big), spec.gap_mm / 2 / rough_mm_per_px)
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
    """Thickens ink lines thinner than a printed line, and turns too-thin colour areas into ink."""
    labels = labels.copy()
    is_ink = (labels == ink) & inside
    thin_ink = is_ink & ~opened(is_ink, radius_px)
    labels[grown(thin_ink, radius_px / 2) & inside] = ink
    for index in set(np.unique(labels[inside]).tolist()) - {ink}:
        area = (labels == index) & inside
        labels[area & ~opened(area, radius_px)] = ink
    return labels
