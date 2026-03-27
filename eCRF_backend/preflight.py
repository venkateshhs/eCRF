from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple
from urllib.parse import urlparse

from .settings import get_settings
from .datalad_config import get_datalad_config


def _ok(msg: str) -> None:
    print(f"[OK] {msg}")


def _warn(msg: str) -> None:
    print(f"[WARN] {msg}")


def _fail(msg: str) -> None:
    print(f"[FAIL] {msg}")


def _check_command(name: str) -> bool:
    path = shutil.which(name)
    if path:
        _ok(f"command found: {name} -> {path}")
        return True
    _fail(f"missing command: {name}")
    return False


def _check_dir_writable(path: Path, label: str) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        test_file = path / ".casee_write_test"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink(missing_ok=True)
        _ok(f"{label} writable: {path}")
        return True
    except Exception as e:
        _fail(f"{label} not writable: {path} ({e})")
        return False


def _check_file_exists(path: Path, label: str) -> bool:
    if path.exists():
        _ok(f"{label} exists: {path}")
        return True
    _fail(f"{label} missing: {path}")
    return False


def _check_datalad_import() -> bool:
    try:
        import datalad  # noqa: F401
        _ok("python import works: datalad")
        return True
    except Exception as e:
        _fail(f"python import failed: datalad ({e})")
        return False


def _check_db_url(db_url: str) -> bool:
    if not db_url:
        _fail("ECRF_DATABASE_URL is empty")
        return False

    if db_url.startswith("sqlite:///"):
        _ok(f"database url looks valid (sqlite): {db_url}")
        return True

    parsed = urlparse(db_url)
    if parsed.scheme:
        _ok(f"database url looks valid: scheme={parsed.scheme}")
        return True

    _fail(f"database url invalid: {db_url}")
    return False


def _extract_ria_ssh_target(ria_url: str) -> Tuple[str, int] | None:
    """
    Supports:
      ria+ssh://user@host:/path
      ria+ssh://user@host/path
    """
    if not ria_url or not ria_url.startswith("ria+ssh://"):
        return None

    raw = ria_url[len("ria+ssh://") :]

    if ":/" in raw:
        hostpart, _ = raw.split(":/", 1)
    else:
        parsed = urlparse("ssh://" + raw)
        hostpart = parsed.netloc

    if "@" in hostpart:
        _, host = hostpart.split("@", 1)
    else:
        host = hostpart

    if ":" in host:
        hostname, port_s = host.rsplit(":", 1)
        try:
            return hostname, int(port_s)
        except Exception:
            return hostname, 22

    return host, 22


def _check_tcp(host: str, port: int, timeout: float = 5.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            _ok(f"TCP reachable: {host}:{port}")
            return True
    except Exception as e:
        _fail(f"TCP unreachable: {host}:{port} ({e})")
        return False


def _check_ssh_quick(ria_url: str) -> bool:
    target = _extract_ria_ssh_target(ria_url)
    if not target:
        _warn("RIA URL is not ssh-based; skipping SSH reachability test")
        return True

    host, port = target
    return _check_tcp(host, port)


def _check_git_identity() -> bool:
    cfg = get_datalad_config()
    ok = True
    if not cfg.git_name.strip():
        _fail("ECRF_DATALAD_GIT_NAME is empty")
        ok = False
    else:
        _ok(f"ECRF_DATALAD_GIT_NAME set: {cfg.git_name}")

    if not cfg.git_email.strip():
        _fail("ECRF_DATALAD_GIT_EMAIL is empty")
        ok = False
    else:
        _ok(f"ECRF_DATALAD_GIT_EMAIL set: {cfg.git_email}")

    return ok


def main() -> int:
    print("[case-e] preflight starting")

    ok = True

    try:
        settings = get_settings()
        cfg = get_datalad_config()
    except Exception as e:
        _fail(f"config load failed: {e}")
        return 2

    print(f"[case-e] env={settings.env} profile={settings.profile}")
    print(f"[case-e] database_url={settings.database_url}")
    print(f"[case-e] data_dir={settings.data_dir}")
    print(f"[case-e] bids_root={settings.bids_root}")
    print(f"[case-e] templates_dir={settings.templates_dir}")
    print(f"[case-e] datalad_mode={cfg.mode}")
    print(f"[case-e] datalad_sync_mode={cfg.sync_mode}")
    print(f"[case-e] datalad_ria_url={cfg.ria_url}")
    print(f"[case-e] datalad_push_on_save={cfg.push_on_save}")

    for cmd in ["git", "git-annex"]:
        ok = _check_command(cmd) and ok

    ok = _check_datalad_import() and ok
    ok = _check_db_url(settings.database_url) and ok
    ok = _check_dir_writable(settings.data_dir, "ECRF_DATA_DIR") and ok
    ok = _check_dir_writable(settings.bids_root, "BIDS_ROOT") and ok
    ok = _check_git_identity() and ok

    if settings.templates_dir is not None:
        ok = _check_file_exists(settings.templates_dir, "ECRF_TEMPLATES_DIR") and ok
    else:
        _warn("ECRF_TEMPLATES_DIR not set; backend must resolve templates another way")

    if cfg.require_ria_for_writes:
        if not cfg.ria_url:
            _fail("RIA is required for writes but ECRF_DATALAD_RIA_URL is not set")
            ok = False
        else:
            ok = _check_ssh_quick(cfg.ria_url) and ok
    else:
        if cfg.ria_url:
            _check_ssh_quick(cfg.ria_url)
        else:
            _warn("RIA URL not configured; remote push disabled")

    if ok:
        print("[case-e] preflight PASSED")
        return 0

    print("[case-e] preflight FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())