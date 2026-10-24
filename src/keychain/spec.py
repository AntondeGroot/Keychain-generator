"""Physical dimensions of the keychain and the printer's limits, in millimetres."""

from dataclasses import dataclass


@dataclass(frozen=True)
class KeychainSpec:
    # The picture's size, without the rim that comes round it: its width, its height, or both, and
    # then it fits within both. Also a guide for printable lines.
    width_mm: float | None = 50.0
    height_mm: float | None = None
    thickness_mm: float = 3.0
    core_mm: float = 1.4  # the middle layer between the two pictures, in the rim's colour
    shade_mm: float = 0.2  # a shade's outer layer: one print layer of a colour over another
    rim_mm: float = 1.5  # border around the picture, in the rim colour
    hole_mm: float = 5.0  # keyring hole diameter
    hole_rim_mm: float = 2.5  # the rim round the keyring hole, wider than the picture's for strength
    neck_mm: float = 5.0  # the radius the tab widens by where it meets the keychain, for strength
    min_line_mm: float = 0.4  # narrowest line the nozzle prints reliably
    gap_mm: float = 2.0  # openings in the drawing's outer line up to this wide are closed
    smoothing_mm: float = 0.08  # evens out JPEG noise and pixel steps along colour edges
    curve_tolerance_mm: float = 0.08  # how far the drawn splines may stray from the traced edges
    simplify_mm: float = 0.005  # far below print resolution, and smooth even in a zoomed preview

    def __post_init__(self) -> None:
        if self.width_mm is None and self.height_mm is None:
            raise ValueError("give the picture a width, a height, or both")
        layers = (self.thickness_mm, self.core_mm, self.shade_mm)
        if min(*self._sizes_given(), *layers, self.rim_mm, self.hole_mm, self.hole_rim_mm, self.neck_mm) <= 0:
            raise ValueError("sizes must be larger than 0 mm")
        if self.core_mm >= self.thickness_mm:
            raise ValueError(f"the core ({self.core_mm} mm) must be thinner than the keychain")
        if self.shade_mm >= self.face_mm:
            raise ValueError(f"a shade's outer layer ({self.shade_mm} mm) must be thinner than a face")

    def mm_per_px(self, width_px: float, height_px: float) -> float:
        """The scale that gives a picture this many pixels across its width or height, or fits it
        within both."""
        sides = ((self.width_mm, width_px), (self.height_mm, height_px))
        return min(mm / px for mm, px in sides if mm is not None)

    def _sizes_given(self) -> list[float]:
        return [mm for mm in (self.width_mm, self.height_mm) if mm is not None]

    @property
    def face_mm(self) -> float:
        """Thickness of the picture on each side of the core."""
        return (self.thickness_mm - self.core_mm) / 2
