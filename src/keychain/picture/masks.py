"""Growing, shrinking and smoothing yes/no pixel masks by a distance in pixels.

Distance transforms do this in one pass whatever the distance, where a disc-shaped filter
gets slow at the 10-40 pixel distances used here. They run only on the box around the mask,
as far out as the distance can reach: most masks, such as one colour's patches, cover a small
part of the picture, and outside that box the answer is already known."""

import math

import numpy as np
from scipy import ndimage

BoxSlices = tuple[slice, slice]


def grown(mask: np.ndarray, distance_px: float) -> np.ndarray:
    box = _box(mask, math.ceil(distance_px) + 1)
    result = np.zeros_like(mask)
    if box is not None:
        result[box] = ndimage.distance_transform_edt(~mask[box]) <= distance_px
    return result


def shrunk(mask: np.ndarray, distance_px: float) -> np.ndarray:
    # One empty pixel round the box keeps the distances: any background beyond it is further.
    box = _box(mask, 1)
    result = np.zeros_like(mask)
    if box is not None:
        result[box] = ndimage.distance_transform_edt(mask[box]) > distance_px
    return result


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


def _box(mask: np.ndarray, margin: int) -> BoxSlices | None:
    """The rows and columns holding the mask, widened by the margin within the image."""
    rows = np.flatnonzero(mask.any(axis=1))
    if not len(rows):
        return None
    columns = np.flatnonzero(mask.any(axis=0))
    height, width = mask.shape
    return (
        slice(max(rows[0] - margin, 0), min(rows[-1] + margin + 1, height)),
        slice(max(columns[0] - margin, 0), min(columns[-1] + margin + 1, width)),
    )
