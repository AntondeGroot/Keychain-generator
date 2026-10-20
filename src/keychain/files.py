"""Writing a keychain's files: one 3MF with every part, an STL per part, and a preview."""

import os
import subprocess
import sys
from pathlib import Path

from keychain.design import Keychain
from keychain.export.stl import extruded
from keychain.export.svg import face_svg, write_svg
from keychain.export.threemf import write_3mf


def write_keychain_files(name: str, keychain: Keychain, out_dir: Path) -> Path:
    folder = out_dir / name
    folder.mkdir(parents=True, exist_ok=True)
    write_3mf(folder / f"{name}.3mf", name, keychain.parts)
    write_svg(folder / f"{name}-preview.svg", face_svg(keychain.face, keychain.outline))
    for part in keychain.parts:
        extruded(part.shape, part.bottom_mm, part.top_mm).export(folder / f"{name}-{part.name}.stl")
    return folder


def open_folder(folder: Path) -> None:
    """Show the folder in Finder, Explorer or the Linux file manager."""
    if sys.platform == "win32":
        os.startfile(folder)  # only exists on Windows
        return
    opener = "open" if sys.platform == "darwin" else "xdg-open"
    subprocess.run([opener, str(folder)], check=False)
