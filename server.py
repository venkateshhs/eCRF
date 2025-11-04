# server.py — robust for PyInstaller (one-folder & one-file)
from __future__ import annotations
import os, sys, socket, threading, webbrowser, traceback
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request
from starlette.responses import FileResponse

BACKEND_IMPORT = "eCRF_backend.main:app"

def exe_dir() -> Path:
    # Folder containing the executable (or this file in dev)
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

def meipass_dir() -> Path | None:
    # PyInstaller temp extraction dir (one-file mode)
    return Path(getattr(sys, "_MEIPASS", "")) if getattr(sys, "frozen", False) else None

EXE_DIR = exe_dir()
MEIPASS = meipass_dir()

# Search bases for packaged resources
SEARCH_BASES = [EXE_DIR]
if MEIPASS:
    SEARCH_BASES.append(MEIPASS)
# Our spec places the data trees under EXE_DIR/_internal
SEARCH_BASES.append(EXE_DIR / "_internal")

def find_frontend_dist() -> Path | None:
    candidates = [
        EXE_DIR / "eCRF_frontend" / "dist",
        EXE_DIR / "eCRF_frontend" / "dist",
        EXE_DIR / "_internal" / "eCRF_frontend" / "dist",
        EXE_DIR / "_internal" / "eCRF_frontend" / "dist",
        MEIPASS / "eCRF_frontend" / "dist" if MEIPASS else None,
        MEIPASS / "eCRF_frontend" / "dist" if MEIPASS else None,
    ]
    for p in filter(None, candidates):
        if p.exists():
            return p
    return None

def find_backend_templates() -> Path | None:
    candidates = [
        EXE_DIR / "eCRF_backend" / "templates",
        EXE_DIR / "_internal" / "eCRF_backend" / "templates",
        MEIPASS / "eCRF_backend" / "templates" if MEIPASS else None,
    ]
    for p in filter(None, candidates):
        if p.exists():
            return p
    return None

# === Writable data dir for the backend ===
# Put persistent data next to the EXE (not inside MEIPASS)
DEFAULT_DATA_DIR = EXE_DIR / "ecrf_data"
os.environ.setdefault("ECRF_DATA_DIR", str(DEFAULT_DATA_DIR))

# Templates env var (read-only assets)
tpl_dir = find_backend_templates()
if tpl_dir:
    os.environ.setdefault("ECRF_TEMPLATES_DIR", str(tpl_dir))

FRONTEND_DIST = find_frontend_dist()
INDEX_HTML = FRONTEND_DIST / "index.html" if FRONTEND_DIST else None

# Ensure our collected code is discoverable (extra safety in frozen runs)
if str(EXE_DIR) not in sys.path:
    sys.path.insert(0, str(EXE_DIR))
if str(EXE_DIR / "_internal") not in sys.path:
    sys.path.insert(0, str(EXE_DIR / "_internal"))

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

    print(f"[eCRF] EXE_DIR       = {EXE_DIR}")
    print(f"[eCRF] MEIPASS       = {MEIPASS}")
    print(f"[eCRF] SEARCH_BASES  = {[str(p) for p in SEARCH_BASES]}")
    print(f"[eCRF] FRONTEND_DIST = {FRONTEND_DIST} (exists={FRONTEND_DIST.exists() if FRONTEND_DIST else False})")
    print(f"[eCRF] ECRF_DATA_DIR = {os.environ.get('ECRF_DATA_DIR')}")

    if FRONTEND_DIST and FRONTEND_DIST.exists():
        app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="spa")

        @app.middleware("http")
        async def spa_fallback(request: Request, call_next):
            path = request.url.path
            API_PREFIXES = (
                "/users", "/forms", "/api", "/health", "/docs", "/openapi.json", "/redoc", "/template_schema.yaml"
            )
            if request.method != "GET" or any(path.startswith(p) for p in API_PREFIXES):
                return await call_next(request)
            resp = await call_next(request)
            if resp.status_code == 404 and INDEX_HTML and INDEX_HTML.exists():
                return FileResponse(str(INDEX_HTML))
            return resp
    else:
        @app.get("/")
        async def _missing_frontend():
            return {"error": "frontend bundle missing", "expected_path": str(FRONTEND_DIST) if FRONTEND_DIST else "not found"}

    return app

def pick_port(default: int = 8000) -> int:
    import socket as _s
    try:
        with _s.socket() as s:
            s.bind(("127.0.0.1", default))
        return default
    except OSError:
        for p in range(default + 1, default + 20):
            try:
                with _s.socket() as s:
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
    # Ensure data dir exists
    try:
        Path(os.environ["ECRF_DATA_DIR"]).mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    app = make_root_app()
    port = int(os.environ.get("ECRF_PORT", pick_port(8000)))
    url = f"http://127.0.0.1:{port}"
    print(f"\n==== eCRF starting on {url} ====\n")
    open_browser(url)

    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")

if __name__ == "__main__":
    main()
