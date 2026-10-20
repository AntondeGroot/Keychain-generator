"""A preview of the front face in millimetres, to check the colours before printing."""

from shapely.geometry.base import BaseGeometry

from keychain.shape.layer import Layer

CANVAS_PADDING_MM = 2.0
DECIMALS = 3  # micrometres, well below what a printer resolves
PAGE_COLOUR = "#e8e8e8"  # light grey, so white parts of the face still show


def face_svg(face: list[Layer], outline: BaseGeometry) -> str:
    min_x, min_y, max_x, max_y = outline.bounds
    left, top = min_x - CANVAS_PADDING_MM, -max_y - CANVAS_PADDING_MM
    width, height = max_x - min_x + 2 * CANVAS_PADDING_MM, max_y - min_y + 2 * CANVAS_PADDING_MM
    paths = "".join(_layer_path(layer) for layer in face)
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


def path_data(shape: BaseGeometry) -> str:
    """SVG has y pointing down, so y is negated to keep the picture upright."""
    polygons = getattr(shape, "geoms", [shape])
    rings = [ring for polygon in polygons for ring in (polygon.exterior, *polygon.interiors)]
    return " ".join(_ring_data(ring.coords) for ring in rings)


def _ring_data(coords) -> str:
    return "M" + " L".join(f"{x:.{DECIMALS}f} {-y:.{DECIMALS}f}" for x, y in coords) + " Z"
