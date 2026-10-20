"""Physical dimensions of the keychain and the printer's limits, in millimetres."""

from dataclasses import dataclass


@dataclass(frozen=True)
class KeychainSpec:
    width_mm: float = 50.0  # widest side of the keychain, rim included, keyring tab not
    thickness_mm: float = 3.0
    core_mm: float = 1.4  # the ink-coloured middle layer between the two pictures
    rim_mm: float = 1.5  # ink-coloured border around the picture
    hole_mm: float = 4.0  # keyring hole diameter
    hole_wall_mm: float = 2.5  # material around the hole
    min_line_mm: float = 0.4  # narrowest line the nozzle prints reliably
    gap_mm: float = 2.0  # openings in the drawing's outer line up to this wide are closed
    smoothing_mm: float = 0.08  # evens out JPEG noise and pixel steps along colour edges
    simplify_mm: float = 0.02  # far below print resolution; keeps files small

    def __post_init__(self) -> None:
        if min(self.width_mm, self.thickness_mm, self.core_mm, self.rim_mm, self.hole_mm) <= 0:
            raise ValueError("sizes must be larger than 0 mm")
        if self.core_mm >= self.thickness_mm:
            raise ValueError(f"the core ({self.core_mm} mm) must be thinner than the keychain")

    @property
    def face_mm(self) -> float:
        """Thickness of the picture on each side of the core."""
        return (self.thickness_mm - self.core_mm) / 2

    @property
    def picture_mm(self) -> float:
        """Widest side of the picture itself, inside the rim."""
        return self.width_mm - 2 * self.rim_mm
