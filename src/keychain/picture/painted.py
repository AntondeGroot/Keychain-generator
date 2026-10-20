"""A rough mask painted by hand over the picture, to correct the automatic background."""

from dataclasses import dataclass

import numpy as np
from PIL import Image

PAINTED = 128  # channel value from which a pixel counts as painted


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
