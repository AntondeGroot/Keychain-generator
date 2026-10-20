"""The filament colours a picture is printed in."""

import re
from collections import Counter
from dataclasses import dataclass

HEX_COLOUR = re.compile(r"#[0-9a-f]{6}")
NAME = re.compile(r"[a-z0-9_-]+")  # names end up in file names, so nothing else
# Rough names, so parts in the slicer read "front-blue" rather than "front-28b6e0".
BASIC_NAMES = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "grey": (128, 128, 128),
    "red": (220, 40, 40),
    "orange": (230, 125, 40),
    "yellow": (250, 220, 50),
    "cream": (250, 235, 170),
    "skin": (250, 190, 145),
    "brown": (120, 70, 30),
    "green": (40, 160, 60),
    "blue": (40, 120, 220),
    "lightblue": (40, 180, 225),
    "purple": (130, 60, 170),
    "pink": (240, 130, 170),
}


@dataclass(frozen=True)
class Colour:
    name: str
    hex: str

    @property
    def rgb(self) -> tuple[int, int, int]:
        red, green, blue = (int(self.hex[start : start + 2], 16) for start in (1, 3, 5))
        return red, green, blue


def parse_colour(text: str) -> Colour:
    """'skin=#f9bf92', or just '#f9bf92' to have it named after the nearest basic colour."""
    name, _, hex_code = text.rpartition("=")
    hex_code = hex_code.lower()
    if not HEX_COLOUR.fullmatch(hex_code):
        raise ValueError(f"'{text}' is not a colour like '#f9bf92' or 'skin=#f9bf92'")
    if name and not NAME.fullmatch(name):
        raise ValueError(f"colour name '{name}' may only have lowercase letters, digits, '-' and '_'")
    return Colour(name or basic_name(hex_code), hex_code)


def basic_name(hex_code: str) -> str:
    rgb = Colour("", hex_code).rgb
    return min(BASIC_NAMES, key=lambda name: _distance_squared(BASIC_NAMES[name], rgb))


def with_unique_names(colours: list[Colour]) -> list[Colour]:
    """Numbers repeated names, e.g. two blues become 'blue1' and 'blue2'."""
    totals = Counter(colour.name for colour in colours)
    seen: Counter[str] = Counter()
    unique = []
    for colour in colours:
        seen[colour.name] += 1
        name = f"{colour.name}{seen[colour.name]}" if totals[colour.name] > 1 else colour.name
        unique.append(Colour(name, colour.hex))
    return unique


def _distance_squared(first: tuple[int, ...], second: tuple[int, ...]) -> int:
    return sum((a - b) ** 2 for a, b in zip(first, second, strict=True))
