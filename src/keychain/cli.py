"""Command line: find a picture's colours, turn the picture into keychain files, or open the web page."""

import argparse
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from keychain.design import design_keychain
from keychain.files import open_folder, write_keychain_files
from keychain.picture.detection import detect_colours
from keychain.picture.palette import Colour, parse_colour, with_unique_names
from keychain.spec import KeychainSpec
from keychain.web.server import serve

DEFAULT_PORT = 8765  # 8000 and 8080 are often taken by other local servers


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
    image = Image.open(args.image)
    palette = _palette(args, image)
    print(f"colours: {_as_arguments(palette)}")
    keychain = design_keychain(image, palette, _spec(args), rim_colour=_rim_colour(args, palette))
    folder = write_keychain_files(_name(args.image), keychain, args.out)
    print(folder.resolve())
    if args.open:
        open_folder(folder)


def _palette(args, image: Image.Image) -> list[Colour]:
    if args.colours:
        return with_unique_names([parse_colour(text) for text in args.colours])
    return detect_colours(image)


def _rim_colour(args, palette: list[Colour]) -> Colour | None:
    if args.rim_colour is None:
        return None
    named = [colour for colour in palette if colour.name == args.rim_colour]
    if not named:
        raise ValueError(
            f"--rim-colour '{args.rim_colour}' is not one of the colours: {_as_arguments(palette)}"
        )
    return named[0]


def _as_arguments(palette: list[Colour]) -> str:
    return " ".join(f"{colour.name}={colour.hex}" for colour in palette)


def _name(image_path: Path) -> str:
    return image_path.stem.lower().replace(" ", "-")


def _spec(args) -> KeychainSpec:
    return KeychainSpec(
        width_mm=args.width,
        thickness_mm=args.thickness,
        core_mm=args.core,
        rim_mm=args.rim,
        hole_mm=args.hole,
    )


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
    parser.add_argument("image", type=Path, help="PNG or JPEG; a transparent background works best")
    parser.add_argument(
        "--colours", nargs="+", help="filaments as name=#rrggbb; found automatically if left out"
    )
    parser.add_argument("--width", type=float, default=defaults.width_mm, help="widest side, mm")
    parser.add_argument("--thickness", type=float, default=defaults.thickness_mm, help="total, mm")
    parser.add_argument("--core", type=float, default=defaults.core_mm, help="middle layer, mm")
    parser.add_argument("--rim", type=float, default=defaults.rim_mm, help="border around the picture, mm")
    parser.add_argument("--hole", type=float, default=defaults.hole_mm, help="keyring hole diameter, mm")
    parser.add_argument(
        "--rim-colour", help="name of the colour for the rim, the ring and the core; ink if left out"
    )
    parser.add_argument("--out", type=Path, default=Path("out"))
    parser.add_argument("--open", action="store_true", help="show the output folder when done")
    parser.set_defaults(command=make)
