# server.py — robust for PyInstaller (one-folder & one-file)
from __future__ import annotations
import os
import sys
import socket
import threading
import webbrowser
import traceback
import json
import platform
import subprocess
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request
from starlette.responses import FileResponse

# CHANGED: point to DataLad-enabled backend entrypoint
BACKEND_IMPORT = "eCRF_backend.datalad_main:app"


def exe_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def meipass_dir() -> Path | None:
    return Path(getattr(sys, "_MEIPASS", "")) if getattr(sys, "frozen", False) else None


EXE_DIR = exe_dir()
MEIPASS = meipass_dir()

SEARCH_BASES = [EXE_DIR]
if MEIPASS:
    SEARCH_BASES.append(MEIPASS)
SEARCH_BASES.append(EXE_DIR / "_internal")


def find_frontend_dist() -> Path | None:
    candidates = [
        EXE_DIR / "eCRF_frontend" / "dist",
        EXE_DIR / "_internal" / "eCRF_frontend" / "dist",
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


CONFIG_FILENAME = "ecrf_config.json"


def _config_path() -> Path:
    return EXE_DIR / CONFIG_FILENAME


def _default_data_dir() -> Path:
    return EXE_DIR / "ecrf_data"


def _ask_user_for_data_dir() -> Path | None:
    system = platform.system()

    if system == "Darwin":
        try:
            result = subprocess.run(
                [
                    "osascript",
                    "-e",
                    'set theFolder to choose folder with prompt "Select folder where eCRF should store its data:"',
                    "-e",
                    "POSIX path of theFolder",
                ],
                capture_output=True,
                text=True,
            )
            print(f"[eCRF] osascript rc={result.returncode}")
            if result.stderr.strip():
                print(f"[eCRF] osascript stderr: {result.stderr.strip()}")

            if result.returncode == 0:
                p = result.stdout.strip()
                if p:
                    print(f"[eCRF] osascript selected: {p}")
                    return Path(p)
        except Exception as e:
            print(f"[eCRF] osascript failed: {e}")
        return None

    if system == "Windows":
        ps_script = r'''
        Add-Type -AssemblyName System.Windows.Forms | Out-Null
        $dlg = New-Object System.Windows.Forms.FolderBrowserDialog
        $dlg.Description = "Select folder where eCRF should store its data"
        $dlg.ShowNewFolderButton = $true
        if ($dlg.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
            Write-Output $dlg.SelectedPath
        }
        '''
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                p = result.stdout.strip()
                if p:
                    print(f"[eCRF] powershell selected: {p}")
                    return Path(p)
        except Exception as e:
            print(f"[eCRF] powershell folder dialog failed: {e}")
        return None

    return None


def _load_or_init_data_dir() -> Path:
    cfg_path = _config_path()

    if cfg_path.exists():
        try:
            with cfg_path.open("r", encoding="utf-8") as f:
                cfg = json.load(f)
            s = cfg.get("data_dir")
            if s:
                data_dir = Path(s)
                data_dir.mkdir(parents=True, exist_ok=True)
                print(f"[eCRF] Using existing data dir from config: {data_dir}")
                return data_dir
        except Exception as e:
            print(f"[eCRF] Failed to read {cfg_path}, regenerating: {e}")

    data_dir = _ask_user_for_data_dir()

    if data_dir is None:
        data_dir = _default_data_dir()
        print(f"[eCRF] No folder chosen; using default data dir: {data_dir}")

    data_dir.mkdir(parents=True, exist_ok=True)

    cfg = {
        "data_dir": str(data_dir),
        "exe_dir": str(EXE_DIR),
    }
    try:
        with cfg_path.open("w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        print(f"[eCRF] Wrote config at {cfg_path}")
    except Exception as e:
        print(f"[eCRF] Failed to write config at {cfg_path}: {e}")

    return data_dir


DATA_DIR = _load_or_init_data_dir()
os.environ["ECRF_DATA_DIR"] = str(DATA_DIR)

# =========================
#   DataLad local config
# =========================
os.environ.setdefault("BIDS_DATALAD_ENABLED", "1")
os.environ.setdefault("ECRF_DATALAD_MODE", "shadow")
os.environ.setdefault("ECRF_DATALAD_SYNC_MODE", "sync")
os.environ.setdefault("BIDS_ROOT", str(DATA_DIR / "bids_datasets"))
os.environ.setdefault("ECRF_DATALAD_GIT_NAME", "case-e local")
os.environ.setdefault("ECRF_DATALAD_GIT_EMAIL", "case-e@localhost")
os.environ.setdefault("ECRF_DATALAD_PUSH_ON_SAVE", "0")


tpl_dir = find_backend_templates()
if tpl_dir:
    os.environ.setdefault("ECRF_TEMPLATES_DIR", str(tpl_dir))

FRONTEND_DIST = find_frontend_dist()
INDEX_HTML = FRONTEND_DIST / "index.html" if FRONTEND_DIST else None

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

    print(f"[eCRF] EXE_DIR                  = {EXE_DIR}")
    print(f"[eCRF] MEIPASS                  = {MEIPASS}")
    print(f"[eCRF] SEARCH_BASES             = {[str(p) for p in SEARCH_BASES]}")
    print(f"[eCRF] FRONTEND_DIST            = {FRONTEND_DIST} (exists={FRONTEND_DIST.exists() if FRONTEND_DIST else False})")
    print(f"[eCRF] ECRF_DATA_DIR            = {os.environ.get('ECRF_DATA_DIR')}")
    print(f"[eCRF] BIDS_ROOT                = {os.environ.get('BIDS_ROOT')}")
    print(f"[eCRF] BIDS_DATALAD_ENABLED     = {os.environ.get('BIDS_DATALAD_ENABLED')}")
    print(f"[eCRF] ECRF_DATALAD_MODE        = {os.environ.get('ECRF_DATALAD_MODE')}")
    print(f"[eCRF] ECRF_DATALAD_SYNC_MODE   = {os.environ.get('ECRF_DATALAD_SYNC_MODE')}")

    if FRONTEND_DIST and FRONTEND_DIST.exists():
        app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="spa")

        @app.middleware("http")
        async def spa_fallback(request: Request, call_next):
            path = request.url.path
            API_PREFIXES = (
                "/users", "/forms", "/api", "/health", "/docs",
                "/openapi.json", "/redoc", "/template_schema.yaml", "/datalad"
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
    try:
        Path(os.environ["ECRF_DATA_DIR"]).mkdir(parents=True, exist_ok=True)
        Path(os.environ["BIDS_ROOT"]).mkdir(parents=True, exist_ok=True)
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