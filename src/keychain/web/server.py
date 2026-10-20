"""A small web server for the keychain page. It only listens on this computer."""

import errno
import json
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files

from PIL import UnidentifiedImageError

from keychain.web.api import JSON, Response, colours_action, download_action, preview_action

HOST = "127.0.0.1"  # this computer only, so nobody else on the network can reach the page
STATIC = files("keychain.web") / "static"
CONTENT_TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css"}
ACTIONS = {"/api/colours": colours_action, "/api/preview": preview_action, "/api/download": download_action}
BAD_REQUEST = (ValueError, KeyError, TypeError, OSError, UnidentifiedImageError)
PORT_TRIES = 20  # the asked port and the ones after it; then the system picks any free one
ANY_FREE_PORT = 0


class KeychainHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802  # the name http.server calls
        name = "index.html" if self.path == "/" else self.path.lstrip("/")
        if name not in _static_names():
            self._send(404, Response(JSON, b'{"error": "not found"}'))
            return
        suffix = name[name.rfind(".") :]
        self._send(200, Response(CONTENT_TYPES[suffix], (STATIC / name).read_bytes()))

    def do_POST(self) -> None:  # noqa: N802  # the name http.server calls
        action = ACTIONS.get(self.path)
        if action is None:
            self._send(404, Response(JSON, b'{"error": "not found"}'))
            return
        try:
            request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            response = action(request)
        except BAD_REQUEST as error:
            self._send(400, Response(JSON, json.dumps({"error": str(error)}).encode()))
            return
        self._send(200, response)

    def _send(self, status: int, response: Response) -> None:
        self.send_response(status)
        self.send_header("Content-Type", response.content_type)
        self.send_header("Content-Length", str(len(response.body)))
        if response.download_name:
            self.send_header("Content-Disposition", f'attachment; filename="{response.download_name}"')
        self.end_headers()
        self.wfile.write(response.body)

    def log_message(self, format: str, *args) -> None:  # the signature http.server calls
        """Quiet: a line for every request would bury the address printed at the start."""


class KeychainServer(ThreadingHTTPServer):
    # Address reuse lets a restarted server take its port back at once on macOS and Linux. On
    # Windows it means something else: a second server may take a port that is in use.
    allow_reuse_address = sys.platform != "win32"


def serve(port: int, open_browser: bool) -> None:
    server = server_on_free_port(port)
    actual_port = server.server_address[1]
    if actual_port != port:
        print(f"Port {port} is in use, so the page uses port {actual_port}.", flush=True)
    url = f"http://{HOST}:{actual_port}/"
    print(f"Keychain page: {url}  (Ctrl-C to stop)", flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
    finally:
        server.server_close()


def server_on_free_port(port: int) -> KeychainServer:
    """A server on the asked port, or on the first free one after it."""
    for candidate in [*range(port, port + PORT_TRIES), ANY_FREE_PORT]:
        try:
            return KeychainServer((HOST, candidate), KeychainHandler)
        except OSError as error:
            if error.errno != errno.EADDRINUSE:
                raise
    raise OSError(f"no free port from {port} on")  # unreachable: the system always has one


def _static_names() -> set[str]:
    return {entry.name for entry in STATIC.iterdir() if entry.name[entry.name.rfind(".") :] in CONTENT_TYPES}
