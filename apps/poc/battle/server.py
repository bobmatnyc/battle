"""Loopback HTTP transport and static-file delivery; no simulation or persistence logic."""

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from .contracts import AuditUnavailable, Conflict
from .adapters.http_api import HttpApi

ROOT = Path(__file__).resolve().parent.parent
CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; connect-src 'self'; worker-src 'self'; frame-ancestors 'none'"
)


def make_handler(api: HttpApi, port: int, static_root: Path):
    """Bind one application instance and asset root without global mutable state."""
    static_root = static_root.resolve()
    hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
    origins = {"http://" + host for host in hosts}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            # Request bodies, provider responses and credentials are never logged.
            pass

        def respond(self, status, payload, mime="application/json"):
            data = (
                json.dumps(payload).encode() if mime == "application/json" else payload
            )
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", CSP)
            self.end_headers()
            self.wfile.write(data)

        def allowed(self):
            return self.headers.get("Host") in hosts

        def do_GET(self):
            if not self.allowed():
                return self.respond(403, {"error": "Local access only."})
            parsed = urlparse(self.path)
            try:
                if parsed.path.startswith("/api/"):
                    return self.respond(
                        200, api.read(parsed.path, parse_qs(parsed.query))
                    )
                relative = (
                    "index.html" if parsed.path == "/" else parsed.path.lstrip("/")
                )
                file = (static_root / relative).resolve()
                if not file.is_relative_to(static_root) or not file.is_file():
                    return self.respond(404, {"error": "Not found."})
                return self.respond(
                    200,
                    file.read_bytes(),
                    mimetypes.guess_type(str(file))[0] or "application/octet-stream",
                )
            except AuditUnavailable as exc:
                return self.respond(403, {"error": str(exc)})
            except (ValueError, KeyError):
                return self.respond(400, {"error": "Invalid request."})
            except Exception:
                return self.respond(
                    500, {"error": "The requested battle data could not be read."}
                )

        def do_POST(self):
            origin = self.headers.get("Origin")
            if not self.allowed() or (origin and origin not in origins):
                return self.respond(403, {"error": "Local access only."})
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                return self.respond(415, {"error": "JSON required."})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 16000:
                    raise ValueError("Invalid request size.")
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict):
                    raise ValueError("Expected object.")
                return self.respond(200, api.mutate(urlparse(self.path).path, body))
            except Conflict as exc:
                return self.respond(409, {"error": str(exc)})
            except (ValueError, KeyError, TypeError) as exc:
                return self.respond(400, {"error": str(exc)[:200]})
            except Exception:
                return self.respond(
                    500,
                    {
                        "error": "The action could not be saved. Refresh before retrying."
                    },
                )

    return Handler


def serve_application(service, port, *, static_root=ROOT / "static"):
    api = HttpApi(service)
    server = ThreadingHTTPServer(
        ("127.0.0.1", port), make_handler(api, port, static_root)
    )
    service.start()
    print(
        f"Battle ready: http://127.0.0.1:{port} | commander: {service.mode}", flush=True
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        service.close()
        server.server_close()


def Application(db, offline=False):
    """Compatibility factory; use bootstrap.build_application for new callers."""
    from .bootstrap import build_application

    return HttpApi(build_application(db, offline=offline))


def serve(port, db, offline=False):
    """Compatibility entry point. CLI composes dependencies before serving."""
    from .bootstrap import build_application

    serve_application(build_application(db, offline=offline), port)
