"""A keychain's files: one 3MF with every part, an STL per part, and a preview."""

import os
import subprocess
import sys
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from keychain.design import Keychain
from keychain.export.stl import extruded
from keychain.export.svg import face_svg
from keychain.export.threemf import keychain_3mf


def keychain_files(name: str, keychain: Keychain) -> dict[str, bytes]:
    """File name to contents, the same for the command line and the web page."""
    files = {
        f"{name}.3mf": keychain_3mf(name, keychain.parts),
        f"{name}-preview.svg": face_svg(keychain.face, keychain.outline.shape, keychain.picture).encode(),
    }
    for part in keychain.parts:
        mesh = extruded(part.shape, part.bottom_mm, part.top_mm)
        files[f"{name}-{part.name}.stl"] = mesh.export(file_type="stl")
    return files


def write_keychain_files(name: str, keychain: Keychain, out_dir: Path) -> Path:
    folder = out_dir / name
    folder.mkdir(parents=True, exist_ok=True)
    for file_name, contents in keychain_files(name, keychain).items():
        (folder / file_name).write_bytes(contents)
    return folder


def zipped(files: dict[str, bytes], folder: str) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        for file_name, contents in files.items():
            archive.writestr(f"{folder}/{file_name}", contents)
    return buffer.getvalue()


def open_folder(folder: Path) -> None:
    """Show the folder in Finder, Explorer or the Linux file manager."""
    if sys.platform == "win32":
        os.startfile(folder)  # only exists on Windows
        return
    opener = "open" if sys.platform == "darwin" else "xdg-open"
    subprocess.run([opener, str(folder)], check=False)
