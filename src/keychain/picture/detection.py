"""Finding the main colours of a picture, as a starting point for choosing filaments.

Only pixels inside flat areas count: the blends along edges (grey between black and white)
are not colours anyone drew. Small details such as a tongue may be missed; add them by hand.

Painted background does not count either: in a group picture, the colours of the characters
painted away would otherwise be in the list, and the blends along the kept one's lines would
take them, such as brown edges round a yellow cat because another cat is brown."""

from collections.abc import Sequence

import numpy as np
from PIL import Image
from scipy import ndimage

from keychain.picture.palette import Colour, basic_name, with_unique_names

FLAT_SPREAD = 120  # summed RGB range across a 3x3 patch below which a pixel lies in a flat area
NEAR = 30  # RGB distance within which pixels count towards a colour
APART = 45  # colours closer than this are taken as one
MIN_SHARE = 0.001  # a colour must cover this share of the picture to count
BIN_SIZE = 8  # RGB histogram bin width
NEAR_BINS = NEAR // BIN_SIZE


def detect_colours(
    image: Image.Image, background: np.ndarray | None = None, known: Sequence[Colour] = ()
) -> list[Colour]:
    """The main colours, most common first, leaving out the background painted away and the
    colours already known, such as ones chosen by hand. Their names differ from the known ones."""
    rgb = np.asarray(image.convert("RGB"), dtype=float)
    counted = np.ones(rgb.shape[:2], bool) if background is None else ~background
    pixels = rgb[_flat_area(rgb) & counted]
    for colour in known:
        pixels = pixels[_distances(pixels, np.array(colour.rgb)) >= APART]
    minimum = MIN_SHARE * counted.sum()
    found = []
    while len(pixels):
        centre, count = _densest_colour(pixels)
        if count < minimum:
            break
        found.append(centre)
        pixels = pixels[_distances(pixels, centre) >= APART]
    return with_unique_names([*known, *(_as_colour(centre) for centre in found)])[len(known) :]


def _flat_area(rgb: np.ndarray) -> np.ndarray:
    spread = sum(
        ndimage.maximum_filter(rgb[..., channel], 3) - ndimage.minimum_filter(rgb[..., channel], 3)
        for channel in range(3)
    )
    return spread < FLAT_SPREAD


def _densest_colour(pixels: np.ndarray) -> tuple[np.ndarray, int]:
    """The average of the pixels around the colour that has the most pixels near it."""
    bins = (pixels // BIN_SIZE).astype(int)
    histogram = np.zeros((256 // BIN_SIZE,) * 3)
    np.add.at(histogram, tuple(bins.T), 1)
    nearby = ndimage.convolve(histogram, _ball(NEAR_BINS), mode="constant")
    densest_bin = np.unravel_index(nearby.argmax(), nearby.shape)
    bin_centre = (np.array(densest_bin) + 0.5) * BIN_SIZE
    members = pixels[_distances(pixels, bin_centre) < NEAR]
    return members.mean(axis=0), len(members)


def _ball(radius: int) -> np.ndarray:
    offsets = np.arange(-radius, radius + 1)
    x, y, z = np.meshgrid(offsets, offsets, offsets, indexing="ij")
    return (x**2 + y**2 + z**2 <= radius**2).astype(float)


def _distances(pixels: np.ndarray, colour: np.ndarray) -> np.ndarray:
    return np.linalg.norm(pixels - colour, axis=1)


def _as_colour(rgb: np.ndarray) -> Colour:
    hex_code = "#" + "".join(f"{round(value):02x}" for value in rgb)
    return Colour(basic_name(hex_code), hex_code)
