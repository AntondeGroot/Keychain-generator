"""Rough masks painted by hand over the picture: to correct the automatic background, to set
the colour of some pixels, to ask for less or more detail in some areas, and lines that join
an area up."""

from dataclasses import dataclass

import numpy as np
from PIL import Image

from keychain.picture.connections import Connection

PAINTED = 128  # channel value from which a pixel counts as painted
SMOOTH_TOLERANCE_FACTOR = 4  # smooth areas: the curves may stray this many times further
DETAILED_TOLERANCE_FACTOR = 3  # detailed areas: they follow the picture this many times closer
UNPAINTED = -1


@dataclass(frozen=True)
class PaintedMask:
    background: np.ndarray  # surely not part of the keychain
    keep: np.ndarray  # surely part of it, even where it looks like background

    @classmethod
    def nothing_painted(cls, size: tuple[int, int]) -> "PaintedMask":
        return cls(_empty(size), _empty(size))

    @classmethod
    def from_image(cls, image: Image.Image, size: tuple[int, int]) -> "PaintedMask":
        """Red paint marks background, green marks what to keep; the page sends it this way."""
        red, green, _, alpha = _channels(image, size, "mask")
        return cls(alpha & red, alpha & green & ~red)

    def enlarged(self, factor: int) -> "PaintedMask":
        return PaintedMask(_enlarged(self.background, factor), _enlarged(self.keep, factor))

    def applied(self, drawn: np.ndarray) -> np.ndarray:
        return (drawn | self.keep) & ~self.background


@dataclass(frozen=True)
class DetailMask:
    """Areas painted to be drawn with less detail (smooth) or more (detailed) than the rest."""

    smooth: np.ndarray
    detailed: np.ndarray

    @classmethod
    def nothing_painted(cls, size: tuple[int, int]) -> "DetailMask":
        return cls(_empty(size), _empty(size))

    @classmethod
    def from_image(cls, image: Image.Image, size: tuple[int, int]) -> "DetailMask":
        """Blue paint marks smooth areas, yellow marks detailed ones; the page sends it this way."""
        red, green, blue, alpha = _channels(image, size, "detail mask")
        return cls(alpha & blue & ~red, alpha & red & green & ~blue)

    def tolerances(self, rows: np.ndarray, columns: np.ndarray, tolerance_mm: float) -> np.ndarray:
        """The curve tolerance at these pixels of the picture."""
        factors = np.ones(len(rows))
        factors[self.smooth[rows, columns]] = SMOOTH_TOLERANCE_FACTOR
        factors[self.detailed[rows, columns]] = 1 / DETAILED_TOLERANCE_FACTOR
        return tolerance_mm * factors


@dataclass(frozen=True)
class ColourPaint:
    """Strokes painted with one of the filament colours, such as a faint strip of hair.

    They are painted onto the picture itself before anything else, so they are enlarged,
    smoothed and matched to the palette exactly like the drawing, with smooth edges."""

    paint: Image.Image  # RGBA, transparent where nothing was painted

    @classmethod
    def nothing_painted(cls, size: tuple[int, int]) -> "ColourPaint":
        return cls(Image.new("RGBA", size))

    @classmethod
    def from_image(cls, image: Image.Image, size: tuple[int, int]) -> "ColourPaint":
        _, _, _, painted = _channels(image, size, "colour paint")
        solid = image.convert("RGBA")
        solid.putalpha(Image.fromarray(np.where(painted, 255, 0).astype(np.uint8)))
        return cls(solid)

    @property
    def painted(self) -> np.ndarray:
        return np.asarray(self.paint)[..., 3] >= PAINTED

    def painted_enlarged(self, factor: int) -> np.ndarray:
        return _enlarged(self.painted, factor)

    def over(self, picture: Image.Image) -> Image.Image:
        return Image.alpha_composite(picture.convert("RGBA"), self.paint)


@dataclass(frozen=True)
class Painting:
    """Everything painted by hand over one picture."""

    mask: PaintedMask
    detail: DetailMask
    colours: ColourPaint
    connections: tuple[Connection, ...] = ()

    @classmethod
    def of(
        cls,
        size: tuple[int, int],
        mask: PaintedMask | None = None,
        detail: DetailMask | None = None,
        colours: ColourPaint | None = None,
        connections: tuple[Connection, ...] = (),
    ) -> "Painting":
        """The parts that were painted; the others as if nothing was painted."""
        return cls(
            mask or PaintedMask.nothing_painted(size),
            detail or DetailMask.nothing_painted(size),
            colours or ColourPaint.nothing_painted(size),
            connections,
        )

    @classmethod
    def nothing_painted(cls, size: tuple[int, int]) -> "Painting":
        return cls.of(size)


def _channels(image: Image.Image, size: tuple[int, int], what: str) -> np.ndarray:
    """Red, green, blue and alpha, each as painted or not."""
    if image.size != size:
        raise ValueError(f"the {what} is {image.size} pixels but the picture is {size}")
    return np.moveaxis(np.asarray(image.convert("RGBA")) >= PAINTED, -1, 0)


def _empty(size: tuple[int, int]) -> np.ndarray:
    width, height = size
    return np.zeros((height, width), dtype=bool)


def _enlarged(mask: np.ndarray, factor: int) -> np.ndarray:
    """Enlarged with smooth edges; repeating each pixel would turn every stroke into steps."""
    height, width = mask.shape
    grey = Image.fromarray(np.where(mask, 255, 0).astype(np.uint8))
    return np.asarray(grey.resize((width * factor, height * factor), Image.Resampling.BILINEAR)) >= PAINTED
