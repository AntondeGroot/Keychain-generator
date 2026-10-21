"""The web page's requests: JSON in, a preview, colours or a zip out."""

import base64
import json
import re
from dataclasses import dataclass
from io import BytesIO

from PIL import Image

from keychain.design import Keychain, design_keychain
from keychain.export.svg import face_svg
from keychain.files import keychain_files, zipped
from keychain.picture.detection import detect_colours
from keychain.picture.handdrawn import Shape
from keychain.picture.painted import ColourPaint, DetailMask, Drawing, PaintedMask, Painting
from keychain.picture.palette import Colour, parse_colour, with_unique_names
from keychain.spec import KeychainSpec

MAX_PICTURE_PX = 4000  # larger pictures take minutes, and far more detail than 5 cm can show
SPEC_FIELDS = ("width_mm", "thickness_mm", "core_mm", "rim_mm", "hole_mm", "curve_tolerance_mm")
JSON = "application/json"


@dataclass(frozen=True)
class Response:
    content_type: str
    body: bytes
    download_name: str | None = None


def colours_action(request: dict) -> Response:
    found = detect_colours(_image(request["image"]))
    return _json({"colours": [{"name": colour.name, "hex": colour.hex} for colour in found]})


def preview_action(request: dict) -> Response:
    keychain = designed_from_request(request)
    svg = face_svg(keychain.face, keychain.outline.shape)
    return _json({"svg": svg, "hole": list(keychain.outline.hole_centre)})


def download_action(request: dict) -> Response:
    name = file_name(request.get("name", ""))
    archive = zipped(keychain_files(name, designed_from_request(request)), name)
    return Response("application/zip", archive, f"{name}.zip")


def designed_from_request(request: dict) -> Keychain:
    """The keychain for a request from the page, or for a project file it saved."""
    image = _image(request["image"])
    palette = _palette(request)
    hole = request.get("hole")
    hole_centre = (float(hole[0]), float(hole[1])) if hole else None
    spec = _spec(request.get("spec", {}))
    painting = _painting(request, image.size)
    return design_keychain(image, palette, spec, painting, hole_centre, _rim_colour(request, palette))


def _palette(request: dict) -> list[Colour]:
    palette = with_unique_names([parse_colour(f"{c['name']}={c['hex']}") for c in request["colours"]])
    if not palette:
        raise ValueError("choose at least one colour")
    return palette


def _painting(request: dict, size: tuple[int, int]) -> Painting:
    """The page sends each layer it painted on as a PNG, and leaves out the others."""
    layers = {name: _image(request[name]) for name in ("mask", "detail", "paint") if request.get(name)}
    return Painting.of(
        size,
        mask=PaintedMask.from_image(layers["mask"], size) if "mask" in layers else None,
        detail=DetailMask.from_image(layers["detail"], size) if "detail" in layers else None,
        colours=ColourPaint.from_image(layers["paint"], size) if "paint" in layers else None,
        drawing=_drawing(request),
    )


def _drawing(request: dict) -> Drawing:
    """The lines and curves drawn on the page, in the picture's own pixels."""
    shapes = request.get("shapes") or []
    return Drawing(
        connections=_connections(request.get("connections") or []),
        edges=tuple(_points(edge) for edge in request.get("edges") or []),
        shapes=tuple(Shape(_points(shape["points"]), shape["colour"]) for shape in shapes),
    )


def _points(points: list) -> tuple:
    return tuple((float(x), float(y)) for x, y in points)


def _connections(lines: list) -> tuple:
    """Each line as ((x, y), (x, y)) in the picture's own pixels."""
    return tuple(((float(a[0]), float(a[1])), (float(b[0]), float(b[1]))) for a, b in lines)


def _rim_colour(request: dict, palette: list[Colour]) -> Colour | None:
    """The colour named for the rim, or none for ink."""
    name = request.get("rim")
    if not name:
        return None
    named = [colour for colour in palette if colour.name == name]
    if not named:
        raise ValueError(f"the rim colour '{name}' is not one of the colours")
    return named[0]


def _spec(values: dict) -> KeychainSpec:
    return KeychainSpec(**{field: float(values[field]) for field in SPEC_FIELDS if field in values})


def _image(data_url: str) -> Image.Image:
    """A picture sent by the page as 'data:image/png;base64,...'."""
    _, _, encoded = data_url.partition(",")
    image = Image.open(BytesIO(base64.b64decode(encoded)))
    image.load()
    if max(image.size) > MAX_PICTURE_PX:
        raise ValueError(f"the picture is larger than {MAX_PICTURE_PX} pixels; make it smaller first")
    return image


def file_name(text: str) -> str:
    """A name safe for files: lowercase letters, digits, dashes and underscores."""
    return re.sub(r"[^a-z0-9_-]+", "-", text.lower()).strip("-") or "keychain"


def _json(content: dict) -> Response:
    return Response(JSON, json.dumps(content).encode())
