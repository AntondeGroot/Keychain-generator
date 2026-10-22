"""A preview of the front face in millimetres, to check the colours and the size before printing.

A scale below and to the right gives the picture's width and height, without the rim and the ring."""

from shapely.geometry.base import BaseGeometry

from keychain.shape.layer import Layer

CANVAS_PADDING_MM = 2.0
DECIMALS = 3  # micrometres, well below what a printer resolves
PAGE_COLOUR = "#e8e8e8"  # light grey, so white parts of the face still show
SCALE_COLOUR = "#555555"
SCALE_GAP_MM = 2.5  # between the keychain and a scale line
TICK_MM = 1.0  # half the length of the marks at the ends of a scale line
TEXT_MM = 2.5
SCALE_ROOM_MM = SCALE_GAP_MM + TICK_MM + TEXT_MM  # beside the keychain, for a scale and its text


def face_svg(face: list[Layer], outline: BaseGeometry, picture: BaseGeometry) -> str:
    min_x, min_y, max_x, max_y = outline.bounds
    left, top = min_x - CANVAS_PADDING_MM, -max_y - CANVAS_PADDING_MM
    width = max_x - min_x + SCALE_ROOM_MM + 2 * CANVAS_PADDING_MM
    height = max_y - min_y + SCALE_ROOM_MM + 2 * CANVAS_PADDING_MM
    paths = "".join(_layer_path(layer) for layer in face) + _scale(picture.bounds, outline.bounds)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.1f}mm" height="{height:.1f}mm" '
        f'viewBox="{left:.3f} {top:.3f} {width:.3f} {height:.3f}">\n'
        f'  <rect x="{left:.3f}" y="{top:.3f}" width="{width:.3f}" height="{height:.3f}" '
        f'fill="{PAGE_COLOUR}"/>\n'
        f"{paths}</svg>\n"
    )


def _layer_path(layer: Layer) -> str:
    data = path_data(layer.shape)
    return f'  <path id="{layer.name}" fill="{layer.colour}" fill-rule="evenodd" d="{data}"/>\n'


def _scale(picture: tuple, outline: tuple) -> str:
    """The picture's width below the keychain, and its height to the right of it."""
    left, bottom, right, top = picture
    below = -outline[1] + SCALE_GAP_MM  # SVG's y points down
    beside = outline[2] + SCALE_GAP_MM
    width = _measure(right - left, f"translate({left:.3f} {below:.3f})")
    height = _measure(top - bottom, f"translate({beside:.3f} {-bottom:.3f}) rotate(-90)")
    return (
        f'  <g id="scale" stroke="{SCALE_COLOUR}" stroke-width="0.15" fill="{SCALE_COLOUR}" '
        f'font-family="sans-serif" font-size="{TEXT_MM}" text-anchor="middle">\n{width}{height}  </g>\n'
    )


def _measure(length_mm: float, placed: str) -> str:
    """A scale line along x from 0, marked at both ends, with its length written under it."""
    marks = "".join(_line(x, -TICK_MM, x, TICK_MM) for x in (0, length_mm))
    middle, under = length_mm / 2, TICK_MM + TEXT_MM
    label = f'<text stroke="none" x="{middle:.3f}" y="{under:.3f}">{length_mm:.1f} mm</text>'
    return f'    <g transform="{placed}">{_line(0, 0, length_mm, 0)}{marks}{label}</g>\n'


def _line(x1: float, y1: float, x2: float, y2: float) -> str:
    return f'<line x1="{x1:.3f}" y1="{y1:.3f}" x2="{x2:.3f}" y2="{y2:.3f}"/>'


def path_data(shape: BaseGeometry) -> str:
    """SVG has y pointing down, so y is negated to keep the picture upright."""
    polygons = getattr(shape, "geoms", [shape])
    rings = [ring for polygon in polygons for ring in (polygon.exterior, *polygon.interiors)]
    return " ".join(_ring_data(ring.coords) for ring in rings)


def _ring_data(coords) -> str:
    return "M" + " L".join(f"{x:.{DECIMALS}f} {-y:.{DECIMALS}f}" for x, y in coords) + " Z"
