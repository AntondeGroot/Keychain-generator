"""Edge pixels whose colour is a blend of the two colours either side, not a colour of its own.

Anti-aliasing mixes the colours on either side of an edge. Orange hair against a white
background gives pale orange, which is nearest to skin, so every such edge gets a thin fringe
of skin. Here a narrow strip of a colour that lies between two neighbouring colours goes to
whichever of the two is closer."""

import itertools

import numpy as np
from scipy import ndimage
from skimage import color

from keychain.picture.masks import grown, opened
from keychain.picture.palette import Colour

BLEND_LAB = 8.0  # a colour at most this far from the line between two others can be their blend
BLEND_RANGE = (0.2, 0.8)  # and somewhere in the middle part of that line, not at one end


def without_edge_blends(
    labels: np.ndarray, inside: np.ndarray, palette: list[Colour], radius_px: float
) -> np.ndarray:
    """Narrow strips of a blend colour with both its parent colours next to it go to the nearer one.

    The parents are looked for outside the picture too: the background is one of them."""
    labels = labels.copy()
    for blend, first, second in blend_triples(palette):
        area = (labels == blend) & inside
        narrow = area & ~opened(area, radius_px)
        near_both = narrow & grown(labels == first, radius_px) & grown(labels == second, radius_px)
        if near_both.any():
            closer_to_first = _distance_to(labels, first) <= _distance_to(labels, second)
            labels[near_both] = np.where(closer_to_first[near_both], first, second)
    return labels


def blend_triples(palette: list[Colour]) -> list[tuple[int, int, int]]:
    """(blend, first, second) for every colour that looks like a mix of two others."""
    lab = [color.rgb2lab(np.array([[colour.rgb]]) / 255)[0, 0] for colour in palette]
    triples = []
    for blend in range(len(palette)):
        others = [index for index in range(len(palette)) if index != blend]
        for first, second in itertools.combinations(others, 2):
            if _is_between(lab[blend], lab[first], lab[second]):
                triples.append((blend, first, second))
    return triples


def _is_between(middle: np.ndarray, start: np.ndarray, end: np.ndarray) -> bool:
    along = np.dot(middle - start, end - start) / np.dot(end - start, end - start)
    off_line = np.linalg.norm(start + along * (end - start) - middle)
    low, high = BLEND_RANGE
    return low <= along <= high and off_line <= BLEND_LAB


def _distance_to(labels: np.ndarray, index: int) -> np.ndarray:
    return ndimage.distance_transform_edt(labels != index)
