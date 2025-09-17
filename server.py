# server.py — robust for PyInstaller (one-folder & one-file)
from __future__ import annotations
import os, sys, socket, threading, webbrowser, traceback
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request
from starlette.responses import FileResponse

BACKEND_IMPORT = "ecrf_backend.main:app"

def runtime_base_dir() -> Path:
    # In one-file builds, resources unpack into _MEIPASS.
    # In one-folder, use the executable directory.
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parent

BASE = runtime_base_dir()
FRONTEND_DIST = BASE / "eCRF_frontend" / "dist"
INDEX_HTML = FRONTEND_DIST / "index.html"

# Ensure our collected code is discoverable (extra safety in frozen runs)
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

# Let backend discover DB/templates relative to the bundle
os.environ.setdefault("ECRF_BASE_DIR", str(BASE))
os.environ.setdefault("ECRF_SHACL_DIR", str(BASE / "ecrf_backend" / "shacl" / "templates"))

def import_backend_app() -> FastAPI:
    mod_name, _, attr = BACKEND_IMPORT.partition(":")
    attr = attr or "app"
    try:
        mod = __import__(mod_name, fromlist=[attr])
        return getattr(mod, attr)
    except Exception:
        print("Failed to import backend app from", BACKEND_IMPORT, file=sys.stderr)
        traceback.print_exc()
        return FastAPI(title="eCRF (SPA-only fallback)")

def make_root_app() -> FastAPI:
    app = import_backend_app()

    # Log resolved paths (helps when debugging frozen builds)
    print(f"[eCRF] BASE = {BASE}")
    print(f"[eCRF] FRONTEND_DIST = {FRONTEND_DIST} (exists={FRONTEND_DIST.exists()})")

    if FRONTEND_DIST.exists():
        app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="spa")

        @app.middleware("http")
        async def spa_fallback(request: Request, call_next):
            path = request.url.path
            API_PREFIXES = (
                "/users", "/forms", "/api", "/health", "/docs", "/openapi.json", "/redoc"
            )
            # Let API and non-GET go through
            if request.method != "GET" or any(path.startswith(p) for p in API_PREFIXES):
                return await call_next(request)

            # Serve index.html for unknown frontend routes
            resp = await call_next(request)
            if resp.status_code == 404 and INDEX_HTML.exists():
                return FileResponse(str(INDEX_HTML))
            return resp
    else:
        @app.get("/")
        async def _missing_frontend():
            return {"error": "frontend bundle missing", "expected_path": str(FRONTEND_DIST)}

    return app

def pick_port(default: int = 8000) -> int:
    # If default busy, try next few ports
    try:
        with socket.socket() as s:
            s.bind(("127.0.0.1", default))
        return default
    except OSError:
        for p in range(default + 1, default + 20):
            try:
                with socket.socket() as s:
                    s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
        return default + 20

def open_browser(url: str):
    try:
        threading.Timer(0.8, lambda: webbrowser.open_new_tab(url)).start()
    except Exception:
        pass

def main():
    app = make_root_app()
    port = int(os.environ.get("ECRF_PORT", pick_port(8000)))
    url = f"http://127.0.0.1:{port}"
    print(f"\n==== eCRF starting on {url} ====\n")
    open_browser(url)

    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")

if __name__ == "__main__":
    main()
