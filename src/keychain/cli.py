"""Command line: find a picture's colours, turn a picture or a saved project into keychain files,
or open the web page."""

import argparse
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from keychain.design import design_keychain
from keychain.files import open_folder, write_keychain_files
from keychain.picture.detection import detect_colours
from keychain.picture.palette import Colour, parse_colour, rim_colour, with_unique_names
from keychain.project import read_project
from keychain.spec import KeychainSpec
from keychain.web.api import designed_from_request, file_name
from keychain.web.server import serve

DEFAULT_PORT = 8765  # 8000 and 8080 are often taken by other local servers
# Size options and the KeychainSpec fields they set. Left out, they keep the project's or the default.
SIZE_OPTIONS = {
    "width": "width_mm",
    "thickness": "thickness_mm",
    "core": "core_mm",
    "rim": "rim_mm",
    "hole": "hole_mm",
}


def main(argv: list[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    try:
        args.command(args)
    except (ValueError, OSError, UnidentifiedImageError) as error:  # bad input, or unreadable files
        raise SystemExit(f"error: {error}") from None


def colours(args) -> None:
    found = detect_colours(Image.open(args.image))
    for colour in found:
        print(f"  {colour.name:10} {colour.hex}")
    print("\nTo make the keychain with these, adding or removing colours as you like:")
    print(f"  keychain make {args.image} --colours {_as_arguments(found)}")


def make(args) -> None:
    keychain, name = _from_project(args) if args.project else _from_picture(args)
    folder = write_keychain_files(name, keychain, args.out)
    print(folder.resolve())
    if args.open:
        open_folder(folder)


def _from_picture(args):
    if args.image is None:
        raise ValueError("give a picture, or a project saved by the web page with --project")
    image = Image.open(args.image)
    palette = _palette(args, image)
    print(f"colours: {_as_arguments(palette)}")
    keychain = design_keychain(image, palette, _spec(args), rim_colour=_rim_colour(args, palette))
    return keychain, _name(args.image)


def _from_project(args):
    """Everything as saved in the page; size options and --rim-colour given here win."""
    if args.image is not None or args.colours:
        raise ValueError("a project already holds the picture and its colours: leave those out")
    request = read_project(args.project)
    request["spec"] = {**request.get("spec", {}), **_size_overrides(args)}
    if args.rim_colour is not None:
        request["rim"] = args.rim_colour
    print(f"project: {args.project}")
    return designed_from_request(request), file_name(request.get("name") or args.project.stem)


def _palette(args, image: Image.Image) -> list[Colour]:
    if args.colours:
        return with_unique_names([parse_colour(text) for text in args.colours])
    return detect_colours(image)


def _rim_colour(args, palette: list[Colour]) -> Colour | None:
    return None if args.rim_colour is None else rim_colour(args.rim_colour, palette)


def _as_arguments(palette: list[Colour]) -> str:
    return " ".join(f"{colour.name}={colour.hex}" for colour in palette)


def _name(image_path: Path) -> str:
    return image_path.stem.lower().replace(" ", "-")


def _spec(args) -> KeychainSpec:
    return KeychainSpec(**_size_overrides(args))


def _size_overrides(args) -> dict[str, float]:
    """The KeychainSpec fields of the size options that were given."""
    given = {option: getattr(args, option) for option in SIZE_OPTIONS}
    return {SIZE_OPTIONS[option]: value for option, value in given.items() if value is not None}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="keychain", description=__doc__)
    commands = parser.add_subparsers(required=True)
    found = commands.add_parser("colours", help="list the main colours of a picture")
    found.add_argument("image", type=Path)
    found.set_defaults(command=colours)
    _add_make(commands)
    web = commands.add_parser("web", help="the keychain page in your browser, to mask and place the ring")
    web.add_argument("--port", type=int, default=DEFAULT_PORT)
    web.add_argument("--no-browser", action="store_true", help="only start the server")
    web.set_defaults(command=lambda args: serve(args.port, open_browser=not args.no_browser))
    return parser


def _add_make(commands) -> None:
    defaults = KeychainSpec()
    parser = commands.add_parser("make", help="3MF, STL and preview files for a keychain")
    parser.add_argument(
        "image", type=Path, nargs="?", help="PNG or JPEG; a transparent background works best"
    )
    parser.add_argument(
        "--project", type=Path, help="a .keychain.json saved by the web page, instead of IMAGE"
    )
    parser.add_argument(
        "--colours", nargs="+", help="filaments as name=#rrggbb; found automatically if left out"
    )
    parser.add_argument(
        "--width",
        type=float,
        help=f"widest side of the picture, mm; the rim comes round it (default {defaults.width_mm})",
    )
    parser.add_argument("--thickness", type=float, help=f"total, mm (default {defaults.thickness_mm})")
    parser.add_argument("--core", type=float, help=f"middle layer, mm (default {defaults.core_mm})")
    parser.add_argument(
        "--rim", type=float, help=f"border around the picture, mm (default {defaults.rim_mm})"
    )
    parser.add_argument("--hole", type=float, help=f"keyring hole diameter, mm (default {defaults.hole_mm})")
    parser.add_argument(
        "--rim-colour",
        help="colour for the rim, the ring and the core: one of the colours by name, or any as "
        "'#2e7d32'; ink if left out",
    )
    parser.add_argument("--out", type=Path, default=Path("out"))
    parser.add_argument("--open", action="store_true", help="show the output folder when done")
    parser.set_defaults(command=make)
