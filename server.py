# server.py — robust local launcher for PyInstaller (one-folder & one-file)
from __future__ import annotations

import json
import os
import platform
import socket
import subprocess
import sys
import threading
import traceback
import webbrowser
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request
from starlette.responses import FileResponse

# DataLad-enabled backend entrypoint
BACKEND_IMPORT = "eCRF_backend.datalad_main:app"


# ---------------------------------------------------------------------
# path helpers
# ---------------------------------------------------------------------

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


# ---------------------------------------------------------------------
# tiny .env loader (no extra dependency)
# ---------------------------------------------------------------------

def _load_dotenv_if_present() -> None:
    candidates = [
        EXE_DIR / ".env",
        Path.cwd() / ".env",
    ]
    if MEIPASS:
        candidates.append(MEIPASS / ".env")

    seen: set[str] = set()

    for env_path in candidates:
        try:
            env_path = env_path.resolve()
        except Exception:
            continue

        key = str(env_path)
        if key in seen:
            continue
        seen.add(key)

        if not env_path.exists() or not env_path.is_file():
            continue

        try:
            for raw_line in env_path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue

                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip()

                if not k:
                    continue

                if len(v) >= 2 and ((v[0] == v[-1] == '"') or (v[0] == v[-1] == "'")):
                    v = v[1:-1]

                os.environ.setdefault(k, v)

            print(f"[eCRF] Loaded .env from {env_path}")
            return
        except Exception as e:
            print(f"[eCRF] Failed loading .env from {env_path}: {e}")


# ---------------------------------------------------------------------
# local data dir selection
# ---------------------------------------------------------------------

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
    # explicit env wins
    env_dir = (os.environ.get("ECRF_DATA_DIR") or "").strip()
    if env_dir:
        data_dir = Path(env_dir).expanduser().resolve()
        data_dir.mkdir(parents=True, exist_ok=True)
        print(f"[eCRF] Using ECRF_DATA_DIR from environment: {data_dir}")
        return data_dir

    cfg_path = _config_path()

    if cfg_path.exists():
        try:
            with cfg_path.open("r", encoding="utf-8") as f:
                cfg = json.load(f)
            s = cfg.get("data_dir")
            if s:
                data_dir = Path(s).expanduser().resolve()
                data_dir.mkdir(parents=True, exist_ok=True)
                print(f"[eCRF] Using existing data dir from config: {data_dir}")
                return data_dir
        except Exception as e:
            print(f"[eCRF] Failed to read {cfg_path}, regenerating: {e}")

    data_dir = _ask_user_for_data_dir()

    if data_dir is None:
        data_dir = _default_data_dir()
        print(f"[eCRF] No folder chosen; using default data dir: {data_dir}")

    data_dir = data_dir.expanduser().resolve()
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


# ---------------------------------------------------------------------
# local env bootstrap
# ---------------------------------------------------------------------

def _configure_local_environment() -> Path:
    _load_dotenv_if_present()

    data_dir = _load_or_init_data_dir()
    bids_root = Path(os.environ.get("BIDS_ROOT", "")).expanduser().resolve() if os.environ.get("BIDS_ROOT") else (data_dir / "bids_datasets").resolve()
    db_path = (data_dir / "ecrf.db").resolve()

    os.environ["ECRF_DATA_DIR"] = str(data_dir)
    os.environ.setdefault("BIDS_ROOT", str(bids_root))

    os.environ["ECRF_ENV"] = "development"
    os.environ["ECRF_PROFILE"] = "local"
    os.environ["ECRF_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["ECRF_DB_AUTO_CREATE"] = "1"
    os.environ["ECRF_ALLOW_SQLITE_IN_PRODUCTION"] = "0"

    os.environ.setdefault("ECRF_SECRET_KEY", "case-e-local-dev-secret")
    os.environ.setdefault("ECRF_JWT_ALGORITHM", "HS256")
    os.environ.setdefault("ECRF_PASSWORD_HASHING_ENABLED", "1")

    os.environ.setdefault("ECRF_BOOTSTRAP_ADMIN", "1")
    os.environ.setdefault("ECRF_ADMIN_USERNAME", "admin")
    os.environ.setdefault("ECRF_ADMIN_EMAIL", "admin@case-e.local")
    os.environ.setdefault("ECRF_ADMIN_PASSWORD", "Admin123!")
    os.environ.setdefault("ECRF_ADMIN_FIRST_NAME", "Admin")
    os.environ.setdefault("ECRF_ADMIN_LAST_NAME", "User")
    os.environ.setdefault("ECRF_ADMIN_ROLE", "Administrator")

    os.environ["ECRF_BIND_HOST"] = "127.0.0.1"
    os.environ["ECRF_OPEN_BROWSER"] = "1"
    os.environ["ECRF_PORT"] = os.environ.get("ECRF_PORT", "8000")

    # Local DataLad mode
    os.environ.setdefault("BIDS_DATALAD_ENABLED", "1")
    os.environ.setdefault("ECRF_DATALAD_MODE", "shadow")
    os.environ.setdefault("ECRF_DATALAD_SYNC_MODE", "sync")
    os.environ.setdefault("ECRF_DATALAD_GIT_NAME", "case-e local")
    os.environ.setdefault("ECRF_DATALAD_GIT_EMAIL", "case-e@localhost")
    os.environ.setdefault("ECRF_DATALAD_PUSH_ON_SAVE", "0")
    os.environ.setdefault("ECRF_DATALAD_PUSH_DATA_MODE", "auto-if-wanted")
    os.environ.setdefault("ECRF_DATALAD_RIA_NAME", "ria")
    os.environ.setdefault("ECRF_DATALAD_REQUIRE_RIA_FOR_WRITES", "0")
    os.environ.setdefault("ECRF_DATALAD_GPGSIGN", "0")
    os.environ.setdefault("ECRF_DATALAD_LOCK_TIMEOUT_SECONDS", "120")

    # templates
    tpl_dir = find_backend_templates()
    if tpl_dir:
        os.environ.setdefault("ECRF_TEMPLATES_DIR", str(tpl_dir))

    # make sure folders exist
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        bids_root.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    return data_dir


DATA_DIR = _configure_local_environment()
FRONTEND_DIST = find_frontend_dist()
INDEX_HTML = FRONTEND_DIST / "index.html" if FRONTEND_DIST else None

if str(EXE_DIR) not in sys.path:
    sys.path.insert(0, str(EXE_DIR))
if str(EXE_DIR / "_internal") not in sys.path:
    sys.path.insert(0, str(EXE_DIR / "_internal"))


# ---------------------------------------------------------------------
# app import / assembly
# ---------------------------------------------------------------------

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

    print(f"[eCRF] EXE_DIR                        = {EXE_DIR}")
    print(f"[eCRF] MEIPASS                        = {MEIPASS}")
    print(f"[eCRF] SEARCH_BASES                   = {[str(p) for p in SEARCH_BASES]}")
    print(f"[eCRF] FRONTEND_DIST                  = {FRONTEND_DIST} (exists={FRONTEND_DIST.exists() if FRONTEND_DIST else False})")
    print(f"[eCRF] ECRF_ENV                       = {os.environ.get('ECRF_ENV')}")
    print(f"[eCRF] ECRF_PROFILE                   = {os.environ.get('ECRF_PROFILE')}")
    print(f"[eCRF] ECRF_DATA_DIR                  = {os.environ.get('ECRF_DATA_DIR')}")
    print(f"[eCRF] BIDS_ROOT                      = {os.environ.get('BIDS_ROOT')}")
    print(f"[eCRF] ECRF_DATABASE_URL              = {os.environ.get('ECRF_DATABASE_URL')}")
    print(f"[eCRF] ECRF_TEMPLATES_DIR             = {os.environ.get('ECRF_TEMPLATES_DIR')}")
    print(f"[eCRF] BIDS_DATALAD_ENABLED           = {os.environ.get('BIDS_DATALAD_ENABLED')}")
    print(f"[eCRF] ECRF_DATALAD_MODE              = {os.environ.get('ECRF_DATALAD_MODE')}")
    print(f"[eCRF] ECRF_DATALAD_SYNC_MODE         = {os.environ.get('ECRF_DATALAD_SYNC_MODE')}")
    print(f"[eCRF] ECRF_DATALAD_PUSH_ON_SAVE      = {os.environ.get('ECRF_DATALAD_PUSH_ON_SAVE')}")
    print(f"[eCRF] ECRF_DATALAD_PUSH_DATA_MODE    = {os.environ.get('ECRF_DATALAD_PUSH_DATA_MODE')}")
    print(f"[eCRF] ECRF_DATALAD_REQUIRE_RIA_WRITES= {os.environ.get('ECRF_DATALAD_REQUIRE_RIA_FOR_WRITES')}")

    if FRONTEND_DIST and FRONTEND_DIST.exists():
        app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="spa")

        @app.middleware("http")
        async def spa_fallback(request: Request, call_next):
            path = request.url.path
            api_prefixes = (
                "/users",
                "/forms",
                "/api",
                "/health",
                "/docs",
                "/openapi.json",
                "/redoc",
                "/template_schema.yaml",
                "/datalad",
            )
            if request.method != "GET" or any(path.startswith(p) for p in api_prefixes):
                return await call_next(request)

            resp = await call_next(request)
            if resp.status_code == 404 and INDEX_HTML and INDEX_HTML.exists():
                return FileResponse(str(INDEX_HTML))
            return resp

    else:
        @app.get("/")
        async def _missing_frontend():
            return {
                "error": "frontend bundle missing",
                "expected_path": str(FRONTEND_DIST) if FRONTEND_DIST else "not found",
            }

    return app


# ---------------------------------------------------------------------
# local port / browser helpers
# ---------------------------------------------------------------------

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


# ---------------------------------------------------------------------
# entrypoint
# ---------------------------------------------------------------------

def main():
    try:
        Path(os.environ["ECRF_DATA_DIR"]).mkdir(parents=True, exist_ok=True)
        Path(os.environ["BIDS_ROOT"]).mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    app = make_root_app()

    port_env = os.environ.get("ECRF_PORT")
    if port_env and str(port_env).strip().isdigit():
        port = int(port_env)
    else:
        port = pick_port(8000)

    bind_host = os.environ.get("ECRF_BIND_HOST", "127.0.0.1").strip() or "127.0.0.1"
    url_host = "127.0.0.1" if bind_host == "0.0.0.0" else bind_host
    url = f"http://{url_host}:{port}"

    print(f"\n==== eCRF starting on {url} ====\n")

    if (os.environ.get("ECRF_OPEN_BROWSER", "1").strip().lower() in {"1", "true", "yes", "on"}):
        open_browser(url)

    import uvicorn
    uvicorn.run(app, host=bind_host, port=port, log_level="info")


if __name__ == "__main__":
    main()