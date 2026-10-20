"""Which filament colour each pixel looks most like."""

import numpy as np
from scipy import ndimage
from skimage import color

from keychain.picture.palette import Colour


def nearest_colours(rgb: np.ndarray, palette: list[Colour], smoothing_px: float = 0) -> np.ndarray:
    """Palette index per pixel, by distance in Lab, which follows how different colours look.

    With smoothing, each colour's closeness is blurred first, so JPEG noise and pixel steps
    do not turn into ragged edges."""
    lab = color.rgb2lab(rgb / 255)
    best_index = np.zeros(rgb.shape[:2], dtype=int)
    best_closeness = np.full(rgb.shape[:2], -np.inf)
    for index, colour in enumerate(palette):
        closeness = -np.linalg.norm(lab - _lab(colour), axis=-1)
        if smoothing_px:
            closeness = ndimage.gaussian_filter(closeness, smoothing_px)
        is_closer = closeness > best_closeness
        best_index[is_closer] = index
        best_closeness[is_closer] = closeness[is_closer]
    return best_index


def darkest(palette: list[Colour]) -> int:
    """The index of the ink colour: the lines, the rim and the core."""
    return min(range(len(palette)), key=lambda index: _lab(palette[index])[0])


def _lab(colour: Colour) -> np.ndarray:
    return color.rgb2lab(np.array([[colour.rgb]]) / 255)[0, 0]
