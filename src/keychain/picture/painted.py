"""Rough masks painted by hand over the picture: to correct the automatic background, and to
ask for less or more detail in some areas."""

from dataclasses import dataclass

import numpy as np
from PIL import Image

PAINTED = 128  # channel value from which a pixel counts as painted
SMOOTH_TOLERANCE_FACTOR = 4  # smooth areas: the curves may stray this many times further
DETAILED_TOLERANCE_FACTOR = 3  # detailed areas: they follow the picture this many times closer


@dataclass(frozen=True)
class PaintedMask:
    background: np.ndarray  # surely not part of the keychain
    keep: np.ndarray  # surely part of it, even where it looks like background

    @classmethod
    def nothing_painted(cls, size: tuple[int, int]) -> "PaintedMask":
        width, height = size
        empty = np.zeros((height, width), dtype=bool)
        return cls(empty, empty)

    @classmethod
    def from_image(cls, image: Image.Image, size: tuple[int, int]) -> "PaintedMask":
        """Red paint marks background, green marks what to keep; the page sends it this way."""
        if image.size != size:
            raise ValueError(f"the mask is {image.size} pixels but the picture is {size}")
        red, green, _, alpha = np.moveaxis(np.asarray(image.convert("RGBA")), -1, 0)
        painted = alpha >= PAINTED
        return cls(painted & (red >= PAINTED), painted & (green >= PAINTED) & (red < PAINTED))

    def enlarged(self, factor: int) -> "PaintedMask":
        return PaintedMask(_enlarged(self.background, factor), _enlarged(self.keep, factor))

    def applied(self, drawn: np.ndarray) -> np.ndarray:
        return (drawn | self.keep) & ~self.background


def _enlarged(mask: np.ndarray, factor: int) -> np.ndarray:
    return mask.repeat(factor, axis=0).repeat(factor, axis=1)


@dataclass(frozen=True)
class DetailMask:
    """Areas painted to be drawn with less detail (smooth) or more (detailed) than the rest."""

    smooth: np.ndarray
    detailed: np.ndarray

    @classmethod
    def nothing_painted(cls, size: tuple[int, int]) -> "DetailMask":
        empty = PaintedMask.nothing_painted(size)
        return cls(empty.background, empty.keep)

    @classmethod
    def from_image(cls, image: Image.Image, size: tuple[int, int]) -> "DetailMask":
        """Blue paint marks smooth areas, yellow marks detailed ones; the page sends it this way."""
        if image.size != size:
            raise ValueError(f"the detail mask is {image.size} pixels but the picture is {size}")
        red, green, blue, alpha = np.moveaxis(np.asarray(image.convert("RGBA")) >= PAINTED, -1, 0)
        return cls(alpha & blue & ~red, alpha & red & green & ~blue)

    def tolerances(self, rows: np.ndarray, columns: np.ndarray, tolerance_mm: float) -> np.ndarray:
        """The curve tolerance at these pixels of the picture."""
        factors = np.ones(len(rows))
        factors[self.smooth[rows, columns]] = SMOOTH_TOLERANCE_FACTOR
        factors[self.detailed[rows, columns]] = 1 / DETAILED_TOLERANCE_FACTOR
        return tolerance_mm * factors
