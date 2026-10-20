"""Growing, shrinking and smoothing yes/no pixel masks by a distance in pixels.

Distance transforms do this in one pass whatever the distance, where a disc-shaped filter
gets slow at the 10-40 pixel distances used here."""

import math

import numpy as np
from scipy import ndimage


def grown(mask: np.ndarray, distance_px: float) -> np.ndarray:
    return ndimage.distance_transform_edt(~mask) <= distance_px


def shrunk(mask: np.ndarray, distance_px: float) -> np.ndarray:
    return ndimage.distance_transform_edt(mask) > distance_px


def opened(mask: np.ndarray, radius_px: float) -> np.ndarray:
    """What a brush of this radius can paint inside the mask: parts narrower than it vanish."""
    return grown(shrunk(mask, radius_px), radius_px)


def closed(mask: np.ndarray, radius_px: float) -> np.ndarray:
    """The mask with gaps and notches narrower than twice the radius filled in.

    Beyond the image counts as empty; otherwise a strip of background between the drawing
    and the image edge would be filled in too."""
    margin = math.ceil(radius_px) + 1
    padded = np.pad(mask, margin)
    return shrunk(grown(padded, radius_px), radius_px)[margin:-margin, margin:-margin]
