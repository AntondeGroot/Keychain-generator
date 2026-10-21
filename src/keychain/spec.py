"""Physical dimensions of the keychain and the printer's limits, in millimetres."""

from dataclasses import dataclass


@dataclass(frozen=True)
class KeychainSpec:
    width_mm: float = 50.0  # widest side of the picture: a guide for printable lines; the rim comes round it
    thickness_mm: float = 3.0
    core_mm: float = 1.4  # the middle layer between the two pictures, in the rim's colour
    rim_mm: float = 1.5  # border around the picture, in the rim colour
    hole_mm: float = 4.0  # keyring hole diameter
    hole_wall_mm: float = 2.5  # material around the hole
    min_line_mm: float = 0.4  # narrowest line the nozzle prints reliably
    gap_mm: float = 2.0  # openings in the drawing's outer line up to this wide are closed
    smoothing_mm: float = 0.08  # evens out JPEG noise and pixel steps along colour edges
    curve_tolerance_mm: float = 0.08  # how far the drawn splines may stray from the traced edges
    simplify_mm: float = 0.005  # far below print resolution, and smooth even in a zoomed preview

    def __post_init__(self) -> None:
        if min(self.width_mm, self.thickness_mm, self.core_mm, self.rim_mm, self.hole_mm) <= 0:
            raise ValueError("sizes must be larger than 0 mm")
        if self.core_mm >= self.thickness_mm:
            raise ValueError(f"the core ({self.core_mm} mm) must be thinner than the keychain")

    @property
    def face_mm(self) -> float:
        """Thickness of the picture on each side of the core."""
        return (self.thickness_mm - self.core_mm) / 2
