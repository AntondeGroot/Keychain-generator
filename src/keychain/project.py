"""Project files saved by the web page: the picture with its masks, lines and settings.

The file holds exactly what the page sends the server for a preview, plus a format and a
version, so the command line can build the same keychain from it. The page writes these
fields in web/static/project.js."""

import json
from pathlib import Path

FORMAT = "keychain-project"
NEWEST_VERSION = 1


def read_project(path: Path) -> dict:
    """The project's request, as the page would send it; a readable error for anything else."""
    try:
        project = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValueError(f"{path} is not a keychain project") from None
    if not isinstance(project, dict) or project.get("format") != FORMAT:
        raise ValueError(f"{path} is not a keychain project")
    if project.get("version", 0) > NEWEST_VERSION:
        raise ValueError(f"{path} was saved by a newer version of the keychain page")
    return project
