from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from financial_controller.config import Settings
from financial_controller.site.view_model import build_site_state

_STATIC_DIR = Path(__file__).parent / "static"
_STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
}


def route_get(settings: Settings, path: str, query: str) -> tuple[int, str, bytes]:
    """Resolve only allowlisted static files and a curated JSON view of local demo data."""

    if path == "/api/state":
        params = parse_qs(query, keep_blank_values=True)
        selected = params.get("run")
        if selected is not None and len(selected) != 1:
            return HTTPStatus.BAD_REQUEST, "text/plain; charset=utf-8", b"Invalid run ID"
        try:
            state = build_site_state(settings, selected_run_id=selected[0] if selected else None)
        except ValueError:
            return HTTPStatus.BAD_REQUEST, "text/plain; charset=utf-8", b"Invalid run ID"
        except LookupError:
            return HTTPStatus.NOT_FOUND, "text/plain; charset=utf-8", b"Run not found"
        return (
            HTTPStatus.OK,
            "application/json; charset=utf-8",
            json.dumps(state, separators=(",", ":")).encode("utf-8"),
        )
    static = _STATIC_FILES.get(path)
    if static is None:
        return HTTPStatus.NOT_FOUND, "text/plain; charset=utf-8", b"Not found"
    file_name, content_type = static
    try:
        body = (_STATIC_DIR / file_name).read_bytes()
    except OSError:
        return HTTPStatus.INTERNAL_SERVER_ERROR, "text/plain; charset=utf-8", b"Asset unavailable"
    return HTTPStatus.OK, content_type, body


def create_server(settings: Settings, port: int = 4173) -> ThreadingHTTPServer:
    if not 0 <= port <= 65535:
        raise ValueError("Port must be between 0 and 65535")

    class Handler(BaseHTTPRequestHandler):
        server_version = "FinancialControllerSite/1.0"

        def _respond(self, *, head_only: bool = False) -> None:
            request = urlsplit(self.path)
            try:
                status, content_type, body = route_get(settings, request.path, request.query)
            except Exception:
                self.log_error("Could not build the local site state")
                status, content_type, body = (
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    "text/plain; charset=utf-8",
                    b"Site data unavailable",
                )
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'",
            )
            self.end_headers()
            if not head_only:
                self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler contract
            self._respond()

        def do_HEAD(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler contract
            self._respond(head_only=True)

        def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler contract
            self.send_response(HTTPStatus.METHOD_NOT_ALLOWED)
            self.send_header("Allow", "GET, HEAD")
            self.send_header("Content-Length", "0")
            self.end_headers()

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def run_site(settings: Settings, port: int = 4173) -> None:
    server = create_server(settings, port)
    print(f"Synthetic finance review: http://127.0.0.1:{server.server_port}/", flush=True)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
