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
from keychain.picture.painted import PaintedMask
from keychain.picture.palette import parse_colour, with_unique_names
from keychain.spec import KeychainSpec

MAX_PICTURE_PX = 4000  # larger pictures take minutes, and far more detail than 5 cm can show
SPEC_FIELDS = ("width_mm", "thickness_mm", "core_mm", "rim_mm", "hole_mm", "smoothing_mm")
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
    keychain = _designed(request)
    svg = face_svg(keychain.face, keychain.outline.shape)
    return _json({"svg": svg, "hole": list(keychain.outline.hole_centre)})


def download_action(request: dict) -> Response:
    name = _file_name(request.get("name", ""))
    archive = zipped(keychain_files(name, _designed(request)), name)
    return Response("application/zip", archive, f"{name}.zip")


def _designed(request: dict) -> Keychain:
    image = _image(request["image"])
    mask = request.get("mask")
    painted = PaintedMask.from_image(_image(mask), image.size) if mask else None
    palette = with_unique_names([parse_colour(f"{c['name']}={c['hex']}") for c in request["colours"]])
    if not palette:
        raise ValueError("choose at least one colour")
    hole = request.get("hole")
    hole_centre = (float(hole[0]), float(hole[1])) if hole else None
    return design_keychain(image, palette, _spec(request.get("spec", {})), painted, hole_centre)


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


def _file_name(text: str) -> str:
    return re.sub(r"[^a-z0-9_-]+", "-", text.lower()).strip("-") or "keychain"


def _json(content: dict) -> Response:
    return Response(JSON, json.dumps(content).encode())
