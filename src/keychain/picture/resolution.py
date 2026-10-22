"""Whether a picture has enough pixels for the size it is printed at."""

import math
from dataclasses import dataclass

# The soft edge of a drawn line is about a pixel wide. Above this, that edge is a large share of
# a printed line (0.4 mm), and thin lines come out blotchy or broken, such as whiskers.
MAX_PIXEL_MM = 0.15


@dataclass(frozen=True)
class Resolution:
    width_mm: float  # the widest side of the picture as printed
    pixel_mm: float  # how wide one pixel of the picture is printed

    def warning(self) -> str | None:
        """What to tell when each pixel is printed too large; none when it is fine."""
        if self.pixel_mm <= MAX_PIXEL_MM:
            return None
        needed_px = math.ceil(self.width_mm / MAX_PIXEL_MM)
        return (
            f"The picture is small for {self.width_mm:g} mm: each pixel is printed "
            f"{self.pixel_mm:.2f} mm wide, so thin lines can come out blotchy or broken. A picture "
            f"of at least {needed_px} pixels across the part you keep looks better; or redraw the "
            "lines that matter with splines."
        )
