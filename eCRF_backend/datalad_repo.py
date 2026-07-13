from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from .logger import logger
from .datalad_config import get_datalad_config
from .datalad_lock import dataset_lock, LockSpec
from .datalad_runtime import get_datalad_worker
from .settings import get_settings
import tempfile

if os.getenv("ECRF_JUSELESS_SSH_PASSWORD"):
    os.environ.setdefault("DATALAD_SSH_MULTIPLEX_CONNECTIONS", "0")

try:
    from datalad.api import Dataset  # type: ignore
except Exception:
    Dataset = None  # type: ignore

try:
    from datalad.api import create_sibling_ria  # type: ignore
except Exception:
    create_sibling_ria = None  # type: ignore


ALLOWED_STUDY_STATUS = {"DRAFT", "PUBLISHED", "ARCHIVED"}


def local_now() -> datetime:
    return datetime.now(timezone.utc)

def _safe_filename(name: str) -> str:
    name = os.path.basename(name)  # remove paths
    name = re.sub(r"[^\w.\- ]", "_", name)  # clean weird chars
    return name.strip() or "file"

def _slugify(value: str) -> str:
    s = (value or "").strip()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^A-Za-z0-9_\-]+", "", s)
    return s[:120] or "study"


def _safe_path_part(value: Optional[str], default: str = "unknown") -> str:
    s = str(value or "").strip()
    if not s:
        return default
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^A-Za-z0-9._\-]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("._-")
    return s or default


def _normalize_modality(value: Optional[str]) -> str:
    return _safe_path_part(str(value or "").lower(), default="misc")


def _deepcopy_json(obj: Any) -> Any:
    try:
        return json.loads(json.dumps(obj, ensure_ascii=False))
    except Exception:
        return copy.deepcopy(obj)


def _json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _json_load(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _ensure_gitignore(ds_path: Path) -> None:
    gitignore = ds_path / ".gitignore"
    lines: List[str] = []
    if gitignore.exists():
        lines = gitignore.read_text(encoding="utf-8").splitlines()

    wanted = {".DS_Store", "*.lock", "__pycache__/"}
    changed = False
    for item in wanted:
        if item not in lines:
            lines.append(item)
            changed = True
    if changed:
        gitignore.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _run_git(ds_path: Path, args: List[str]) -> str:
    out = subprocess.check_output(
        ["git", "-C", str(ds_path), *args],
        stderr=subprocess.STDOUT,
        text=True,
    )
    return out.strip()


def _ssh_connect_timeout_seconds() -> int:
    try:
        return max(1, int(os.getenv("ECRF_JUSELESS_SSH_CONNECT_TIMEOUT_SECONDS", "15")))
    except Exception:
        return 15


def _configure_local_ssh_password_if_requested() -> None:
    password = os.getenv("ECRF_JUSELESS_SSH_PASSWORD")
    connect_timeout = _ssh_connect_timeout_seconds()
    if not password:
        os.environ.setdefault(
            "GIT_SSH_COMMAND",
            "ssh -o StrictHostKeyChecking=accept-new "
            "-o BatchMode=yes "
            "-o NumberOfPasswordPrompts=0 "
            f"-o ConnectTimeout={connect_timeout} "
            "-o ServerAliveInterval=30 "
            "-o ServerAliveCountMax=4",
        )
        return
    if shutil.which("sshpass") is None:
        raise RuntimeError(
            "ECRF_JUSELESS_SSH_PASSWORD is set but sshpass is not installed; "
            "install sshpass or use SSH key authentication."
        )
    existing = os.getenv("GIT_SSH_COMMAND", "")
    if existing and "sshpass" in existing:
        return
    os.environ["GIT_SSH_COMMAND"] = (
        "sshpass -p "
        f"{shlex.quote(password)} "
        "ssh -o StrictHostKeyChecking=accept-new "
        f"-o ConnectTimeout={connect_timeout} "
        "-o NumberOfPasswordPrompts=1 "
        "-o ServerAliveInterval=30 "
        "-o ServerAliveCountMax=4"
    )
    os.environ.setdefault("GIT_TERMINAL_PROMPT", "0")


def _ssh_command_prefix() -> List[str]:
    cmd: List[str] = []
    password = os.getenv("ECRF_JUSELESS_SSH_PASSWORD")
    connect_timeout = str(_ssh_connect_timeout_seconds())
    if password:
        if shutil.which("sshpass") is None:
            raise RuntimeError(
                "ECRF_JUSELESS_SSH_PASSWORD is set but sshpass is not installed; "
                "install sshpass or use SSH key authentication."
            )
        cmd.extend(["sshpass", "-p", password])
        cmd.extend(
            [
                "ssh",
                "-o",
                "StrictHostKeyChecking=accept-new",
                "-o",
                f"ConnectTimeout={connect_timeout}",
                "-o",
                "NumberOfPasswordPrompts=1",
                "-o",
                "ServerAliveInterval=30",
                "-o",
                "ServerAliveCountMax=4",
            ]
        )
    else:
        cmd.extend(
            [
                "ssh",
                "-o",
                "StrictHostKeyChecking=accept-new",
                "-o",
                "BatchMode=yes",
                "-o",
                "NumberOfPasswordPrompts=0",
                "-o",
                f"ConnectTimeout={connect_timeout}",
                "-o",
                "ServerAliveInterval=30",
                "-o",
                "ServerAliveCountMax=4",
            ]
        )
    return cmd


def _parse_ria_ssh_url(ria_url: str) -> tuple[str, Optional[int], str]:
    parsed = urlparse(ria_url)
    if parsed.scheme != "ria+ssh" or not parsed.hostname or not parsed.path:
        raise RuntimeError(f"Unsupported ECRF_DATALAD_RIA_URL for Juseless mirror: {ria_url}")

    target = parsed.hostname
    if parsed.username:
        target = f"{parsed.username}@{target}"
    return target, parsed.port, parsed.path


def _parse_ssh_url(ssh_url: str) -> tuple[str, Optional[int], str]:
    parsed = urlparse(ssh_url)
    if parsed.scheme != "ssh" or not parsed.hostname or not parsed.path:
        raise RuntimeError(f"Unsupported SSH remote URL: {ssh_url}")

    target = parsed.hostname
    if parsed.username:
        target = f"{parsed.username}@{target}"
    return target, parsed.port, parsed.path


def _result_has_error(results: Any) -> bool:
    if results is None:
        return False
    if isinstance(results, dict):
        rows = [results]
    elif isinstance(results, list):
        rows = results
    else:
        try:
            rows = list(results)
        except TypeError:
            rows = [results]
    for row in rows:
        if isinstance(row, dict) and row.get("status") in {"error", "impossible"}:
            return True
    return False


def _git_show_json(ds_path: Path, rev: str, rel_path: str, default: Any = None) -> Any:
    try:
        raw = _run_git(ds_path, ["show", f"{rev}:{rel_path}"])
        return json.loads(raw)
    except Exception:
        return default


def _safe_status(s: Optional[str]) -> str:
    s2 = (s or "PUBLISHED").strip().upper()
    return s2 if s2 in ALLOWED_STUDY_STATUS else "PUBLISHED"


def _append_jsonl(path: Path, row: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


@dataclass
class StudyPaths:
    dataset_path: Path
    canonical_dir: Path
    metadata_json: Path
    content_json: Path
    templates_dir: Path
    entries_dir: Path
    files_dir: Path
    audit_dir: Path
    audit_system_dir: Path
    audit_system_study_dir: Path
    audit_subject_dir: Path
    shares_dir: Path
    access_dir: Path


class DataladStudyRepo:
    def __init__(self, root: Optional[str] = None) -> None:
        _configure_local_ssh_password_if_requested()
        settings = get_settings()
        base = root or os.environ.get("BIDS_ROOT") or str(settings.bids_root)
        self.root = Path(base).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # config / runtime helpers
    # ------------------------------------------------------------------

    def _settings(self):
        return get_settings()

    def _cfg(self):
        return get_datalad_config()

    def _validate_storage_ready(self) -> None:
        settings = self._settings()
        cfg = self._cfg()

        if settings.is_production and not settings.bids_root:
            raise RuntimeError("BIDS_ROOT must be configured in production.")

        if (
            settings.is_production
            and cfg.require_ria_for_writes
            and not cfg.ria_url
            and not cfg.ssh_remote_template
        ):
            raise RuntimeError(
                "ECRF_DATALAD_RIA_URL or ECRF_DATALAD_SSH_REMOTE_TEMPLATE must be "
                "configured in production when ECRF_DATALAD_REQUIRE_RIA_FOR_WRITES=1."
            )

    def _set_repo_identity(self, ds) -> None:
        try:
            ds.repo.set_config("user.name", self._cfg().git_name, where="local")
            ds.repo.set_config("user.email", self._cfg().git_email, where="local")
            if self._cfg().gpgsign:
                ds.repo.set_config("commit.gpgsign", "true", where="local")
                if self._cfg().gpg_keyid:
                    ds.repo.set_config("user.signingkey", self._cfg().gpg_keyid, where="local")
        except Exception:
            pass

    def _ssh_remote_url_for_dataset(self, dataset_path: Path) -> Optional[str]:
        template = self._cfg().ssh_remote_template
        if not template:
            return None

        dataset_name = Path(dataset_path).expanduser().resolve().name
        return template.format(study=dataset_name, dataset=dataset_name)

    def remote_delete_url_for_dataset(self, dataset_path: Path) -> Optional[str]:
        return self._ssh_remote_url_for_dataset(dataset_path)

    def _ensure_remote_bare_repo(self, remote_url: str) -> None:
        ssh_target, ssh_port, remote_path = _parse_ssh_url(remote_url)
        remote_parent = str(Path(remote_path).parent)
        remote_cmd = " && ".join(
            [
                "set -e",
                f"mkdir -p {shlex.quote(remote_parent)}",
                (
                    f"if [ ! -d {shlex.quote(remote_path)} ]; then "
                    f"git init --bare {shlex.quote(remote_path)}; fi"
                ),
            ]
        )

        ssh_cmd = _ssh_command_prefix()
        if ssh_port:
            ssh_cmd.extend(["-p", str(ssh_port)])
        ssh_cmd.extend([ssh_target, remote_cmd])

        result = subprocess.run(ssh_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(
                f"Failed to ensure SSH bare repo {remote_url}: "
                f"{detail or f'exit code {result.returncode}'}"
            )

    def delete_remote_bare_repo_url(self, remote_url: str, *, expected_dataset_name: Optional[str] = None) -> None:
        remote_url = str(remote_url or "").strip()
        if not remote_url:
            return

        ssh_target, ssh_port, remote_path = _parse_ssh_url(remote_url)
        remote_name = Path(remote_path).name
        if not remote_name.startswith("study_") or not remote_name.endswith(".git"):
            raise RuntimeError(f"Refusing to delete unexpected remote study repo path: {remote_path}")
        if expected_dataset_name:
            expected_remote_name = f"{expected_dataset_name}.git"
            if remote_name != expected_remote_name:
                raise RuntimeError(
                    f"Refusing to delete remote repo {remote_path}; expected {expected_remote_name}"
                )

        remote_parent = str(Path(remote_path).parent)
        if remote_parent in {"", "/", "."}:
            raise RuntimeError(f"Refusing to delete remote study repo with unsafe parent: {remote_path}")

        remote_cmd = " && ".join(
            [
                "set -e",
                (
                    f"if [ -d {shlex.quote(remote_path)} ]; then "
                    f"rm -rf {shlex.quote(remote_path)}; fi"
                ),
            ]
        )

        ssh_cmd = _ssh_command_prefix()
        if ssh_port:
            ssh_cmd.extend(["-p", str(ssh_port)])
        ssh_cmd.extend([ssh_target, remote_cmd])

        result = subprocess.run(ssh_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(
                f"Failed to delete SSH bare repo {remote_url}: "
                f"{detail or f'exit code {result.returncode}'}"
            )

    def delete_remote_worktree_for_dataset(self, dataset_path: Path) -> None:
        remote_url = self._ssh_remote_url_for_dataset(dataset_path)
        if not remote_url:
            return

        dataset_name = Path(dataset_path).expanduser().resolve().name
        if not dataset_name.startswith("study_"):
            raise RuntimeError(f"Refusing to delete unexpected remote worktree name: {dataset_name}")

        ssh_target, ssh_port, _remote_repo_path = _parse_ssh_url(remote_url)
        studies_dir = os.getenv("ECRF_JUSELESS_STUDIES_DIR", "/home/vshivashankar/casee-studies")
        remote_dataset_path = f"{studies_dir.rstrip('/')}/{dataset_name}"
        remote_parent = str(Path(remote_dataset_path).parent)
        if remote_parent in {"", "/", "."}:
            raise RuntimeError(f"Refusing to delete remote worktree with unsafe parent: {remote_dataset_path}")

        remote_cmd = " && ".join(
            [
                "set -e",
                (
                    f"if [ -e {shlex.quote(remote_dataset_path)} ] "
                    f"&& [ ! -d {shlex.quote(remote_dataset_path + '/.git')} ] "
                    f"&& [ ! -d {shlex.quote(remote_dataset_path + '/.datalad')} ]; then "
                    f"echo 'Refusing to delete non-repository mirror path: {shlex.quote(remote_dataset_path)}' >&2; "
                    f"exit 2; fi"
                ),
                (
                    f"if [ -e {shlex.quote(remote_dataset_path)} ]; then "
                    f"rm -rf {shlex.quote(remote_dataset_path)}; fi"
                ),
            ]
        )

        ssh_cmd = _ssh_command_prefix()
        if ssh_port:
            ssh_cmd.extend(["-p", str(ssh_port)])
        ssh_cmd.extend([ssh_target, remote_cmd])

        result = subprocess.run(ssh_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(
                f"Failed to delete SSH worktree mirror {remote_dataset_path}: "
                f"{detail or f'exit code {result.returncode}'}"
            )

    def _delete_remote_bare_repo_if_configured(self, dataset_path: Path) -> None:
        remote_url = self._ssh_remote_url_for_dataset(dataset_path)
        if not remote_url:
            return

        expected_dataset_name = Path(dataset_path).expanduser().resolve().name
        self.delete_remote_bare_repo_url(
            remote_url,
            expected_dataset_name=expected_dataset_name,
        )

    def _ensure_ssh_sibling_if_needed(self, dataset_path: Path) -> Optional[str]:
        remote_url = self._ssh_remote_url_for_dataset(dataset_path)
        if not remote_url:
            return None

        if Dataset is None:
            raise RuntimeError("DataLad is not installed")

        ds = Dataset(str(dataset_path))
        if not ds.is_installed():
            raise RuntimeError(f"Dataset not installed at {dataset_path}")

        self._ensure_remote_bare_repo(remote_url)

        try:
            existing_url = _run_git(dataset_path, ["remote", "get-url", "origin"])
        except Exception:
            existing_url = ""

        if existing_url:
            if existing_url != remote_url:
                logger.info(
                    "[DataladStudyRepo._ensure_ssh_sibling_if_needed] Updating origin remote dataset=%s old=%s new=%s",
                    dataset_path,
                    existing_url,
                    remote_url,
                )
                _run_git(dataset_path, ["remote", "set-url", "origin", remote_url])
        else:
            _run_git(dataset_path, ["remote", "add", "origin", remote_url])

        try:
            ds.repo.set_config("remote.origin.annex-ignore", "false", where="local")
        except Exception:
            pass

        return "origin"

    def _ensure_ria_sibling_if_needed(self, dataset_path: Path) -> str:
        ssh_target = self._ensure_ssh_sibling_if_needed(dataset_path)
        if ssh_target:
            return ssh_target

        cfg = self._cfg()
        if not cfg.ria_url:
            logger.info(
                "[DataladStudyRepo._ensure_ria_sibling_if_needed] No RIA URL configured; skipping sibling setup for dataset=%s",
                dataset_path,
            )
            return cfg.ria_name

        if Dataset is None:
            logger.error(
                "[DataladStudyRepo._ensure_ria_sibling_if_needed] DataLad is not installed; cannot configure RIA sibling for dataset=%s",
                dataset_path,
            )
            raise RuntimeError("DataLad is not installed")

        logger.info(
            "[DataladStudyRepo._ensure_ria_sibling_if_needed] Checking RIA sibling for dataset=%s ria_name=%s ria_url=%s",
            dataset_path,
            cfg.ria_name,
            cfg.ria_url,
        )

        ds = Dataset(str(dataset_path))
        if not ds.is_installed():
            logger.error(
                "[DataladStudyRepo._ensure_ria_sibling_if_needed] Dataset not installed at dataset=%s",
                dataset_path,
            )
            raise RuntimeError(f"Dataset not installed at {dataset_path}")

        try:
            siblings = ds.siblings()
            logger.info(
                "[DataladStudyRepo._ensure_ria_sibling_if_needed] Existing siblings loaded for dataset=%s count=%s",
                dataset_path,
                len(siblings or []),
            )
        except Exception:
            logger.exception(
                "[DataladStudyRepo._ensure_ria_sibling_if_needed] Failed to list siblings for dataset=%s",
                dataset_path,
            )
            siblings = []

        existing_names = set()
        for item in siblings or []:
            if isinstance(item, dict):
                name = item.get("name")
                if name:
                    existing_names.add(str(name))

        if cfg.ria_name in existing_names:
            logger.info(
                "[DataladStudyRepo._ensure_ria_sibling_if_needed] RIA sibling already exists for dataset=%s sibling=%s",
                dataset_path,
                cfg.ria_name,
            )
            return cfg.ria_name

        if "ria-storage" in existing_names and "origin" in existing_names:
            logger.info(
                "[DataladStudyRepo._ensure_ria_sibling_if_needed] Dataset has RIA storage sibling and origin; using origin as push target for dataset=%s",
                dataset_path,
            )
            return "origin"

        if "ria-storage" in existing_names:
            raise RuntimeError(
                f"Dataset {dataset_path} has ria-storage configured but no git push sibling "
                f"named {cfg.ria_name!r} or 'origin'."
            )

        if create_sibling_ria is None:
            logger.error(
                "[DataladStudyRepo._ensure_ria_sibling_if_needed] create_sibling_ria is unavailable for dataset=%s",
                dataset_path,
            )
            raise RuntimeError(
                "DataLad create_sibling_ria is not available but a RIA sibling is required."
            )

        try:
            logger.info(
                "[DataladStudyRepo._ensure_ria_sibling_if_needed] Creating RIA sibling for dataset=%s sibling=%s",
                dataset_path,
                cfg.ria_name,
            )
            create_sibling_ria(
                dataset=str(dataset_path),
                url=cfg.ria_url,
                name=cfg.ria_name,
                new_store_ok=True,
            )
            logger.info(
                "[DataladStudyRepo._ensure_ria_sibling_if_needed] Configured RIA sibling for dataset=%s sibling=%s",
                dataset_path,
                cfg.ria_name,
            )
            return cfg.ria_name
        except Exception:
            logger.exception(
                "[DataladStudyRepo._ensure_ria_sibling_if_needed] Failed to create RIA sibling for dataset=%s sibling=%s",
                dataset_path,
                cfg.ria_name,
            )
            raise

    def _get_dataset_content(self, dataset_path: Path, path: Optional[Path] = None) -> None:
        cfg = self._cfg()
        if cfg.mode not in {"shadow", "primary"} or not cfg.get_on_open:
            return
        if Dataset is None:
            raise RuntimeError("DataLad is not installed")

        dataset_path = Path(dataset_path).expanduser().resolve()
        if not dataset_path.exists():
            return

        with dataset_lock(LockSpec(dataset_path=dataset_path)):
            ds = Dataset(str(dataset_path))
            if not ds.is_installed():
                return

            kwargs: Dict[str, Any] = {}
            if path is not None:
                kwargs["path"] = str(Path(path).expanduser().resolve())
            else:
                kwargs["path"] = str(dataset_path)
                kwargs["recursive"] = True

            logger.info("[DataladStudyRepo._get_dataset_content] datalad get dataset=%s path=%s", dataset_path, kwargs["path"])
            results = ds.get(**kwargs)
            if _result_has_error(results):
                raise RuntimeError(f"DataLad get failed for {kwargs['path']}")

    def get_study_content(self, study_id: int, study_name: str) -> None:
        p = self.paths(study_id, study_name)
        self._get_dataset_content(p.dataset_path)

    def dataset_id(self, dataset_path: Path) -> Optional[str]:
        dataset_path = Path(dataset_path).expanduser().resolve()
        if Dataset is not None:
            try:
                ds = Dataset(str(dataset_path))
                dataset_id = getattr(ds, "id", None)
                if dataset_id:
                    return str(dataset_id)
            except Exception:
                pass
        try:
            out = _run_git(dataset_path, ["config", "--get", "datalad.dataset.id"])
        except Exception:
            return None
        return out.strip() or None

    def clone_study_from_remote(
        self,
        study_id: int,
        study_name: str,
        dataset_id: str,
        *,
        source_dataset_path: Optional[Path] = None,
    ) -> StudyPaths:
        if Dataset is None:
            raise RuntimeError("DataLad is not installed")

        cfg = self._cfg()
        p = self.paths(study_id, study_name)
        if p.dataset_path.exists():
            if self.dataset_id(p.dataset_path):
                return p
            backup_path = p.dataset_path.with_name(f"{p.dataset_path.name}.invalid-{int(time.time())}")
            suffix = 1
            while backup_path.exists():
                backup_path = p.dataset_path.with_name(
                    f"{p.dataset_path.name}.invalid-{int(time.time())}-{suffix}"
                )
                suffix += 1
            logger.warning(
                "[DataladStudyRepo.clone_study_from_remote] Local path exists but is not a DataLad dataset; moving aside path=%s backup=%s",
                p.dataset_path,
                backup_path,
            )
            shutil.move(str(p.dataset_path), str(backup_path))

        remote_source_path = Path(source_dataset_path).expanduser().resolve() if source_dataset_path else p.dataset_path
        clone_url = self._ssh_remote_url_for_dataset(remote_source_path)
        if not clone_url:
            if not cfg.ria_url:
                raise RuntimeError("ECRF_DATALAD_RIA_URL is not configured; cannot clone study.")
            clone_url = f"{cfg.ria_url}#{dataset_id}"

        p.dataset_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(
            "[DataladStudyRepo.clone_study_from_remote] Cloning study_id=%s from=%s to=%s",
            study_id,
            clone_url,
            p.dataset_path,
        )
        result = subprocess.run(
            ["datalad", "clone", clone_url, str(p.dataset_path)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(
                f"DataLad clone failed for study_id={study_id}: "
                f"{detail or f'exit code {result.returncode}'}"
            )

        self._get_dataset_content(p.dataset_path)
        return p

    def _verify_push(self, ds: Any, to: str) -> None:
        cfg = self._cfg()
        if not cfg.verify_push:
            return
        logger.info("[DataladStudyRepo._verify_push] Verifying push dataset=%s to=%s", ds.path, to)
        results = ds.push(to=to, data="nothing")
        if _result_has_error(results):
            raise RuntimeError(f"DataLad push verification failed for {ds.path} to={to}")

    def _drop_annex_content_after_push(self, ds: Any, dataset_path: Path) -> None:
        cfg = self._cfg()
        if not cfg.drop_after_push:
            return
        logger.info("[DataladStudyRepo._drop_annex_content_after_push] Dropping annex content dataset=%s", dataset_path)
        results = ds.drop(
            path=str(dataset_path),
            what="filecontent",
            recursive=True,
            reckless="availability",
        )
        if _result_has_error(results):
            logger.warning(
                "[DataladStudyRepo._drop_annex_content_after_push] DataLad drop reported non-fatal errors dataset=%s results=%s",
                dataset_path,
                results,
            )

    def _mirror_to_juseless_worktree(self, ds: Any, dataset_path: Path) -> None:
        if os.getenv("ECRF_JUSELESS_MIRROR_AFTER_PUSH", "1") != "1":
            return

        cfg = self._cfg()
        studies_dir = os.getenv("ECRF_JUSELESS_STUDIES_DIR", "/home/vshivashankar/casee-studies")
        dataset_name = Path(dataset_path).expanduser().resolve().name
        remote_dataset_path = f"{studies_dir.rstrip('/')}/{dataset_name}"

        if cfg.ssh_remote_template:
            remote_url = self._ssh_remote_url_for_dataset(dataset_path)
            if not remote_url:
                return
            ssh_target, ssh_port, remote_repo_path = _parse_ssh_url(remote_url)
            remote_repo_name = Path(remote_repo_path).name
            if remote_repo_name != f"{dataset_name}.git":
                raise RuntimeError(
                    f"Refusing to mirror unexpected remote repo {remote_repo_path}; expected {dataset_name}.git"
                )
            remote_clone_url = remote_repo_path
        elif cfg.ria_url:
            dataset_id = getattr(ds, "id", None)
            if not dataset_id:
                dataset_id = _run_git(dataset_path, ["config", "--get", "datalad.dataset.id"])
            if not dataset_id:
                raise RuntimeError(f"Cannot mirror {dataset_path}; DataLad dataset id is missing.")

            ssh_target, ssh_port, ria_store_path = _parse_ria_ssh_url(cfg.ria_url)
            remote_clone_url = f"ria+file://{ria_store_path}#{dataset_id}"
        else:
            return

        remote_cmd = " && ".join(
            [
                "set -e",
                f"mkdir -p {shlex.quote(studies_dir)}",
                (
                    f"if [ -e {shlex.quote(remote_dataset_path)} ] "
                    f"&& [ ! -d {shlex.quote(remote_dataset_path + '/.git')} ] "
                    f"&& [ ! -d {shlex.quote(remote_dataset_path + '/.datalad')} ]; then "
                    f"echo 'Refusing to overwrite non-repository mirror path: {shlex.quote(remote_dataset_path)}' >&2; "
                    f"exit 2; fi"
                ),
                (
                    f"if [ ! -d {shlex.quote(remote_dataset_path + '/.git')} ] "
                    f"&& [ ! -d {shlex.quote(remote_dataset_path + '/.datalad')} ]; then "
                    f"datalad clone {shlex.quote(remote_clone_url)} {shlex.quote(remote_dataset_path)}; "
                    f"else cd {shlex.quote(remote_dataset_path)} && datalad update --merge; fi"
                ),
                f"cd {shlex.quote(remote_dataset_path)} && datalad get -r .",
            ]
        )

        ssh_cmd = _ssh_command_prefix()
        if ssh_port:
            ssh_cmd.extend(["-p", str(ssh_port)])
        ssh_cmd.extend([ssh_target, remote_cmd])

        logger.info(
            "[DataladStudyRepo._mirror_to_juseless_worktree] Updating Juseless worktree dataset=%s remote_path=%s",
            dataset_path,
            remote_dataset_path,
        )
        result = subprocess.run(ssh_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(
                "Juseless worktree mirror failed "
                f"for {remote_dataset_path}: {detail or f'exit code {result.returncode}'}"
            )

    def _logical_path(self, dataset_path: Path, absolute_path: Path) -> str:
        return str(Path(absolute_path).resolve().relative_to(dataset_path.resolve()))

    # ------------------------------------------------------------------
    # dataset layout
    # ------------------------------------------------------------------

    def study_dataset_path(self, study_id: int, study_name: str) -> Path:
        return self.root / f"study_{int(study_id)}_{_slugify(study_name)}"

    def paths(self, study_id: int, study_name: str) -> StudyPaths:
        ds = self.study_dataset_path(study_id, study_name)
        c = ds / "canonical"
        audit_dir = c / "audit"
        return StudyPaths(
            dataset_path=ds,
            canonical_dir=c,
            metadata_json=c / "study_metadata.json",
            content_json=c / "study_content.json",
            templates_dir=c / "templates",
            entries_dir=c / "entries",
            files_dir=c / "files",
            audit_dir=audit_dir,
            audit_system_dir=audit_dir / "system",
            audit_system_study_dir=audit_dir / "system" / "study",
            audit_subject_dir=audit_dir / "subject",
            shares_dir=c / "shared_links",
            access_dir=c / "access",
        )

    def ensure_dataset(self, study_id: int, study_name: str) -> StudyPaths:
        self._validate_storage_ready()
        p = self.paths(study_id, study_name)

        logger.info(
            "[DataladStudyRepo.ensure_dataset] Start study_id=%s study_name=%s dataset_path=%s",
            study_id,
            study_name,
            p.dataset_path,
        )

        p.dataset_path.mkdir(parents=True, exist_ok=True)
        logger.info(
            "[DataladStudyRepo.ensure_dataset] Ensured dataset directory exists dataset_path=%s",
            p.dataset_path,
        )

        if Dataset is None:
            logger.error(
                "[DataladStudyRepo.ensure_dataset] DataLad is not installed for dataset_path=%s",
                p.dataset_path,
            )
            raise RuntimeError("DataLad is not installed")

        logger.info(
            "[DataladStudyRepo.ensure_dataset] About to acquire dataset lock dataset_path=%s",
            p.dataset_path,
        )
        with dataset_lock(LockSpec(dataset_path=p.dataset_path)):
            logger.info(
                "[DataladStudyRepo.ensure_dataset] Acquired dataset lock dataset_path=%s",
                p.dataset_path,
            )

            ds = Dataset(str(p.dataset_path))
            logger.info(
                "[DataladStudyRepo.ensure_dataset] Dataset object created dataset_path=%s",
                p.dataset_path,
            )

            installed = ds.is_installed()
            logger.info(
                "[DataladStudyRepo.ensure_dataset] Dataset install status dataset_path=%s installed=%s",
                p.dataset_path,
                installed,
            )

            if not installed:
                try:
                    logger.info(
                        "[DataladStudyRepo.ensure_dataset] Creating dataset dataset_path=%s cfg_proc=text2git",
                        p.dataset_path,
                    )
                    ds.create(force=True, cfg_proc="text2git")
                    logger.info(
                        "[DataladStudyRepo.ensure_dataset] Dataset created dataset_path=%s",
                        p.dataset_path,
                    )
                except Exception:
                    logger.exception(
                        "[DataladStudyRepo.ensure_dataset] Dataset creation failed dataset_path=%s",
                        p.dataset_path,
                    )
                    raise

            self._set_repo_identity(ds)
            logger.info(
                "[DataladStudyRepo.ensure_dataset] Repo identity configured dataset_path=%s",
                p.dataset_path,
            )

            _ensure_gitignore(p.dataset_path)
            logger.info(
                "[DataladStudyRepo.ensure_dataset] .gitignore ensured dataset_path=%s",
                p.dataset_path,
            )

            for d in [
                p.canonical_dir,
                p.templates_dir,
                p.entries_dir,
                p.files_dir,
                p.audit_dir,
                p.audit_system_dir,
                p.audit_system_study_dir,
                p.audit_subject_dir,
                p.shares_dir,
                p.access_dir,
            ]:
                d.mkdir(parents=True, exist_ok=True)
                logger.info(
                    "[DataladStudyRepo.ensure_dataset] Ensured directory exists path=%s",
                    d,
                )

        logger.info(
            "[DataladStudyRepo.ensure_dataset] Completed study_id=%s dataset_path=%s",
            study_id,
            p.dataset_path,
        )
        return p

    def next_study_id(self) -> int:
        max_id = 0
        for ds in self.root.glob("study_*"):
            m = re.match(r"study_(\d+)_", ds.name)
            if m:
                max_id = max(max_id, int(m.group(1)))
            else:
                m2 = re.match(r"study_(\d+)$", ds.name)
                if m2:
                    max_id = max(max_id, int(m2.group(1)))
        return max_id + 1

    # ------------------------------------------------------------------
    # git / datalad history
    # ------------------------------------------------------------------

    def save(self, ds_path: Path, message: str) -> None:
        if Dataset is None:
            logger.error(
                "[DataladStudyRepo.save] DataLad is not installed ds_path=%s message=%s",
                ds_path,
                message,
            )
            raise RuntimeError("DataLad is not installed")

        cfg = self._cfg()
        ds_path = Path(ds_path).expanduser().resolve()
        worker = get_datalad_worker()

        logger.info(
            "[DataladStudyRepo.save] Start ds_path=%s message=%s sync_mode=%s push_on_save=%s ria_name=%s",
            ds_path,
            message,
            cfg.sync_mode,
            cfg.push_on_save,
            cfg.ria_name,
        )

        if cfg.sync_mode == "async" and worker is not None:
            worker.enqueue_save(ds_path, message)
            logger.info("[DataladStudyRepo.save] Enqueued dataset save ds_path=%s msg=%s", ds_path, message)
            return

        logger.info(
            "[DataladStudyRepo.save] About to acquire dataset lock ds_path=%s message=%s",
            ds_path,
            message,
        )
        with dataset_lock(LockSpec(dataset_path=ds_path)):
            logger.info(
                "[DataladStudyRepo.save] Acquired dataset lock ds_path=%s message=%s",
                ds_path,
                message,
            )

            ds = Dataset(str(ds_path))
            logger.info("[DataladStudyRepo.save] Dataset object created ds_path=%s", ds_path)

            if not ds.is_installed():
                logger.error("[DataladStudyRepo.save] Dataset not installed ds_path=%s", ds_path)
                raise RuntimeError(f"Dataset not installed at {ds_path}")

            self._set_repo_identity(ds)
            logger.info("[DataladStudyRepo.save] Repo identity configured ds_path=%s", ds_path)

            try:
                logger.info("[DataladStudyRepo.save] Calling ds.save ds_path=%s message=%s", ds_path, message)
                ds.save(message=message)
                logger.info("[DataladStudyRepo.save] Saved dataset ds_path=%s msg=%s", ds_path, message)
            except Exception:
                logger.exception("[DataladStudyRepo.save] ds.save failed ds_path=%s msg=%s", ds_path, message)
                raise

            if cfg.push_on_save and (cfg.ria_name or cfg.ssh_remote_template):
                if not cfg.ria_url and not cfg.ssh_remote_template:
                    raise RuntimeError(
                        "ECRF_DATALAD_RIA_URL or ECRF_DATALAD_SSH_REMOTE_TEMPLATE is not configured; cannot push dataset."
                    )
                push_target = self._ensure_ria_sibling_if_needed(ds_path)
                push_kwargs = {"to": push_target}
                if cfg.push_data_mode != "nothing":
                    push_kwargs["data"] = cfg.push_data_mode
                try:
                    logger.info(
                        "[DataladStudyRepo.save] Pushing dataset ds_path=%s to=%s data_mode=%s",
                        ds_path,
                        push_target,
                        cfg.push_data_mode,
                    )
                    ds.push(**push_kwargs)
                    logger.info(
                        "[DataladStudyRepo.save] Pushed dataset ds_path=%s to=%s data_mode=%s",
                        ds_path,
                        push_target,
                        cfg.push_data_mode,
                    )
                    self._verify_push(ds, push_target)
                    self._drop_annex_content_after_push(ds, ds_path)
                    self._mirror_to_juseless_worktree(ds, ds_path)
                except Exception:
                    logger.exception(
                        "[DataladStudyRepo.save] ds.push failed ds_path=%s to=%s data_mode=%s",
                        ds_path,
                        push_target,
                        cfg.push_data_mode,
                    )
                    raise

    def sync_to_remote(self, ds_path: Path, message: str) -> Optional[str]:
        if Dataset is None:
            raise RuntimeError("DataLad is not installed")

        cfg = self._cfg()
        if not cfg.ria_name and not cfg.ssh_remote_template:
            raise RuntimeError("ECRF_DATALAD_RIA_NAME or ECRF_DATALAD_SSH_REMOTE_TEMPLATE is not configured")
        if not cfg.ria_url and not cfg.ssh_remote_template:
            raise RuntimeError("ECRF_DATALAD_RIA_URL or ECRF_DATALAD_SSH_REMOTE_TEMPLATE is not configured; cannot sync dataset.")

        ds_path = Path(ds_path).expanduser().resolve()
        logger.info(
            "[DataladStudyRepo.sync_to_remote] Start ds_path=%s message=%s remote=%s data_mode=%s",
            ds_path,
            message,
            cfg.ria_name,
            cfg.push_data_mode,
        )

        with dataset_lock(LockSpec(dataset_path=ds_path)):
            ds = Dataset(str(ds_path))
            if not ds.is_installed():
                raise RuntimeError(f"Dataset not installed at {ds_path}")

            self._set_repo_identity(ds)
            push_target = self._ensure_ria_sibling_if_needed(ds_path)
            ds.save(message=message)

            push_kwargs = {"to": push_target}
            if cfg.push_data_mode != "nothing":
                push_kwargs["data"] = cfg.push_data_mode
            results = ds.push(**push_kwargs)
            if _result_has_error(results):
                raise RuntimeError(f"DataLad push failed for {ds_path} to={push_target}")

            self._verify_push(ds, push_target)
            self._drop_annex_content_after_push(ds, ds_path)
            dataset_id = getattr(ds, "id", None) or self.dataset_id(ds_path)
            self._mirror_to_juseless_worktree(ds, ds_path)
            logger.info(
                "[DataladStudyRepo.sync_to_remote] Completed ds_path=%s remote=%s",
                ds_path,
                push_target,
            )
            return dataset_id

    def previous_study_content(self, ds_path: Path) -> Dict[str, Any]:
        return _git_show_json(ds_path, "HEAD~1", "canonical/study_content.json", default={}) or {}

    def previous_template_schema(self, ds_path: Path, version: int) -> Dict[str, Any]:
        rel = f"canonical/templates/v{int(version):03d}/schema.json"
        return _git_show_json(ds_path, "HEAD~1", rel, default={}) or {}

    # ------------------------------------------------------------------
    # helpers for labels / users
    # ------------------------------------------------------------------

    def _load_study_content_data(self, p: StudyPaths) -> Dict[str, Any]:
        content = _json_load(p.content_json, {}) or {}
        if isinstance(content, dict) and isinstance(content.get("study_data"), dict):
            return content.get("study_data") or {}
        return {}

    def _resolve_subject_label(self, study_data: Dict[str, Any], subject_index: Optional[int]) -> str:
        if subject_index is None:
            return "study"

        subjects = study_data.get("subjects") if isinstance(study_data.get("subjects"), list) else []
        try:
            idx = int(subject_index)
        except Exception:
            idx = 0

        if 0 <= idx < len(subjects):
            subj = subjects[idx] or {}
            raw = (
                subj.get("id")
                or subj.get("subject_id")
                or subj.get("label")
                or subj.get("name")
                or f"subject_{idx + 1:03d}"
            )
            return _safe_path_part(raw, default=f"subject_{idx + 1:03d}")

        return f"subject_{idx + 1:03d}"

    def _resolve_visit_label(self, study_data: Dict[str, Any], visit_index: Optional[int]) -> Optional[str]:
        if visit_index is None:
            return None

        visits = study_data.get("visits") if isinstance(study_data.get("visits"), list) else []
        try:
            idx = int(visit_index)
        except Exception:
            idx = 0

        if 0 <= idx < len(visits):
            visit = visits[idx] or {}
            raw = (
                visit.get("name")
                or visit.get("label")
                or visit.get("id")
                or f"visit_{idx + 1:02d}"
            )
            return _safe_path_part(raw, default=f"visit_{idx + 1:02d}")

        return f"visit_{idx + 1:02d}"

    def _resolve_group_label(self, study_data: Dict[str, Any], group_index: Optional[int]) -> Optional[str]:
        if group_index is None:
            return None

        groups = study_data.get("groups") if isinstance(study_data.get("groups"), list) else []
        try:
            idx = int(group_index)
        except Exception:
            idx = 0

        if 0 <= idx < len(groups):
            grp = groups[idx] or {}
            raw = (
                grp.get("name")
                or grp.get("label")
                or grp.get("id")
                or f"group_{idx + 1:02d}"
            )
            return _safe_path_part(raw, default=f"group_{idx + 1:02d}")

        return f"group_{idx + 1:02d}"

    def _resolve_subject_visit_group_labels(
        self,
        p: StudyPaths,
        *,
        subject_index: Optional[int] = None,
        visit_index: Optional[int] = None,
        group_index: Optional[int] = None,
        subject_raw: Optional[str] = None,
        visit_raw: Optional[str] = None,
        group_raw: Optional[str] = None,
    ) -> Dict[str, Any]:
        study_data = self._load_study_content_data(p)

        resolved_subject_raw = subject_raw
        resolved_visit_raw = visit_raw
        resolved_group_raw = group_raw

        try:
            if resolved_subject_raw in (None, "") and subject_index is not None:
                resolved_subject_raw = self._resolve_subject_label(study_data, subject_index)
        except Exception:
            pass

        try:
            if resolved_visit_raw in (None, "") and visit_index is not None:
                resolved_visit_raw = self._resolve_visit_label(study_data, visit_index)
        except Exception:
            pass

        try:
            if resolved_group_raw in (None, "") and group_index is not None:
                resolved_group_raw = self._resolve_group_label(study_data, group_index)
        except Exception:
            pass

        return {
            "subject_raw": resolved_subject_raw,
            "visit_raw": resolved_visit_raw,
            "group_raw": resolved_group_raw,
        }

    def _build_actor_payload(
        self,
        *,
        actor: Optional[str] = None,
        user_id: Optional[int] = None,
        actor_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {}
        if user_id is not None:
            payload["user_id"] = int(user_id)
        if actor_name:
            payload["actor_name"] = str(actor_name).strip()
        if actor:
            payload["actor"] = str(actor).strip()
        elif actor_name:
            payload["actor"] = str(actor_name).strip()
        elif user_id is not None:
            payload["actor"] = f"User#{int(user_id)}"
        return payload

    def _resolve_primary_modality_label(self, modalities: Optional[List[str]]) -> str:
        if isinstance(modalities, list):
            for item in modalities:
                if str(item or "").strip():
                    return _normalize_modality(item)
        return "misc"

    def _resolve_file_storage_dir(
        self,
        p: StudyPaths,
        *,
        subject_index: Optional[int] = None,
        visit_index: Optional[int] = None,
        group_index: Optional[int] = None,
        modalities: Optional[List[str]] = None,
        form_version: Optional[int] = None,
    ) -> Path:
        if subject_index is None and visit_index is None:
            return p.files_dir / "metadata"

        study_data = self._load_study_content_data(p)
        version = int(form_version or 1)

        subject_label = self._resolve_subject_label(study_data, subject_index)
        visit_label = self._resolve_visit_label(study_data, visit_index)
        group_label = self._resolve_group_label(study_data, group_index)
        modality_label = self._resolve_primary_modality_label(modalities)

        base = p.files_dir / f"v{version:03d}" / f"sub-{subject_label}"
        if visit_label:
            base = base / f"ses-{visit_label}"
        if group_label:
            base = base / f"grp-{group_label}"

        return base / modality_label

    # ------------------------------------------------------------------
    # published snapshot methods used by forms_hybrid
    # ------------------------------------------------------------------

    def create_or_replace_published_snapshot(
        self,
        *,
        study_id: int,
        study_name: str,
        template_schema: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        study_content: Optional[Dict[str, Any]] = None,
        created_by: Optional[int] = None,
        study_description: Optional[str] = None,
        study_data: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
        draft_of_study_id: Optional[int] = None,
        last_completed_step: Optional[int] = None,
        actor: Optional[str] = None,
        actor_name: Optional[str] = None,
        user_id: Optional[int] = None,
        audit_label: Optional[str] = None,
        commit_message: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        logger.info(
            "[DataladStudyRepo.create_or_replace_published_snapshot] Start study_id=%s study_name=%s audit_label=%s",
            study_id,
            study_name,
            audit_label,
        )

        p = self.ensure_dataset(study_id, study_name)
        logger.info(
            "[DataladStudyRepo.create_or_replace_published_snapshot] Dataset ready study_id=%s dataset_path=%s",
            study_id,
            p.dataset_path,
        )

        now_iso = local_now().isoformat()

        if metadata is not None:
            safe_meta = _deepcopy_json(metadata or {})
        else:
            safe_meta = {
                "id": int(study_id),
                "created_by": int(created_by) if created_by is not None else None,
                "study_name": study_name,
                "study_description": study_description or "",
                "status": _safe_status(status),
                "draft_of_study_id": draft_of_study_id,
                "last_completed_step": last_completed_step,
                "updated_at": now_iso,
                "created_at": now_iso,
            }

        if study_content is not None:
            safe_content = _deepcopy_json(study_content or {})
        else:
            safe_content = {
                "id": int(study_id),
                "study_id": int(study_id),
                "study_data": _deepcopy_json(study_data or {}),
            }

        safe_schema = _deepcopy_json(template_schema or {})

        safe_meta.setdefault("id", int(study_id))
        safe_meta.setdefault("study_name", study_name)
        safe_meta.setdefault("study_description", study_description or "")
        safe_meta["status"] = _safe_status(safe_meta.get("status"))
        safe_meta["updated_at"] = now_iso
        safe_meta.setdefault("created_at", now_iso)

        safe_content["id"] = int(study_id)
        safe_content["study_id"] = int(study_id)
        safe_content.setdefault("study_data", _deepcopy_json(study_data or {}))

        logger.info(
            "[DataladStudyRepo.create_or_replace_published_snapshot] Prepared payloads study_id=%s meta_keys=%s content_keys=%s schema_keys=%s",
            study_id,
            sorted(list(safe_meta.keys())),
            sorted(list(safe_content.keys())),
            sorted(list(safe_schema.keys())) if isinstance(safe_schema, dict) else type(safe_schema).__name__,
        )

        logger.info(
            "[DataladStudyRepo.create_or_replace_published_snapshot] About to acquire dataset lock study_id=%s dataset_path=%s",
            study_id,
            p.dataset_path,
        )
        with dataset_lock(LockSpec(dataset_path=p.dataset_path)):
            logger.info(
                "[DataladStudyRepo.create_or_replace_published_snapshot] Acquired dataset lock study_id=%s dataset_path=%s",
                study_id,
                p.dataset_path,
            )

            _json_dump(p.metadata_json, safe_meta)
            logger.info(
                "[DataladStudyRepo.create_or_replace_published_snapshot] Wrote metadata study_id=%s path=%s",
                study_id,
                p.metadata_json,
            )

            _json_dump(p.content_json, safe_content)
            logger.info(
                "[DataladStudyRepo.create_or_replace_published_snapshot] Wrote content study_id=%s path=%s",
                study_id,
                p.content_json,
            )

            version = 1
            if isinstance(safe_schema, dict):
                try:
                    version = int(safe_schema.get("version") or safe_schema.get("template_version") or 1)
                except Exception:
                    version = 1
            version = max(1, version)
            logger.info(
                "[DataladStudyRepo.create_or_replace_published_snapshot] Resolved template version study_id=%s version=%s",
                study_id,
                version,
            )

            version_dir = p.templates_dir / f"v{version:03d}"
            version_dir.mkdir(parents=True, exist_ok=True)
            logger.info(
                "[DataladStudyRepo.create_or_replace_published_snapshot] Ensured version dir study_id=%s path=%s",
                study_id,
                version_dir,
            )

            _json_dump(version_dir / "schema.json", safe_schema)
            logger.info(
                "[DataladStudyRepo.create_or_replace_published_snapshot] Wrote template schema study_id=%s path=%s",
                study_id,
                version_dir / "schema.json",
            )

            actor_payload = self._build_actor_payload(
                actor=actor,
                actor_name=actor_name,
                user_id=user_id if user_id is not None else created_by,
            )
            logger.info(
                "[DataladStudyRepo.create_or_replace_published_snapshot] Built actor payload study_id=%s actor_payload=%s",
                study_id,
                actor_payload,
            )

            self._append_audit(
                p,
                action="study_snapshot_written",
                study_id=study_id,
                payload={
                    "study_name": study_name,
                    "status": safe_meta.get("status"),
                    "version": version,
                    "ui_label": audit_label,
                    **actor_payload,
                },
            )
            logger.info(
                "[DataladStudyRepo.create_or_replace_published_snapshot] Appended audit study_id=%s action=study_snapshot_written",
                study_id,
            )

        final_commit_message = commit_message or f"case-e: published snapshot study={study_id} version={version}"
        logger.info(
            "[DataladStudyRepo.create_or_replace_published_snapshot] About to save dataset study_id=%s dataset_path=%s message=%s",
            study_id,
            p.dataset_path,
            final_commit_message,
        )
        self.save(
            p.dataset_path,
            final_commit_message,
        )
        logger.info(
            "[DataladStudyRepo.create_or_replace_published_snapshot] Dataset save complete study_id=%s dataset_path=%s",
            study_id,
            p.dataset_path,
        )

        result = {
            "dataset_path": str(p.dataset_path),
            "metadata_path": self._logical_path(p.dataset_path, p.metadata_json),
            "content_path": self._logical_path(p.dataset_path, p.content_json),
            "template_path": self._logical_path(p.dataset_path, version_dir / "schema.json"),
            "version": version,
        }
        logger.info(
            "[DataladStudyRepo.create_or_replace_published_snapshot] Completed study_id=%s result=%s",
            study_id,
            result,
        )
        return result

    # ------------------------------------------------------------------
    # study CRUD
    # ------------------------------------------------------------------

    def create_study(
        self,
        *,
        study_id: int,
        created_by: int,
        study_name: str,
        study_description: str,
        study_data: Dict[str, Any],
        status: str = "PUBLISHED",
        draft_of_study_id: Optional[int] = None,
        last_completed_step: Optional[int] = None,
        actor: Optional[str] = None,
        actor_name: Optional[str] = None,
        user_id: Optional[int] = None,
        audit_label: Optional[str] = None,
    ) -> Dict[str, Any]:
        p = self.ensure_dataset(study_id, study_name)

        metadata = {
            "id": int(study_id),
            "created_by": int(created_by),
            "study_name": study_name,
            "study_description": study_description or "",
            "status": _safe_status(status),
            "draft_of_study_id": draft_of_study_id,
            "last_completed_step": last_completed_step,
            "created_at": local_now().isoformat(),
            "updated_at": local_now().isoformat(),
        }
        content = {
            "id": int(study_id),
            "study_id": int(study_id),
            "study_data": _deepcopy_json(study_data or {}),
        }

        with dataset_lock(LockSpec(dataset_path=p.dataset_path)):
            _json_dump(p.metadata_json, metadata)
            _json_dump(p.content_json, content)

            v1_dir = p.templates_dir / "v001"
            v1_dir.mkdir(parents=True, exist_ok=True)
            _json_dump(v1_dir / "schema.json", self._snapshot_schema(study_data or {}, study_id, version=1))

            actor_payload = self._build_actor_payload(
                actor=actor,
                actor_name=actor_name,
                user_id=user_id if user_id is not None else created_by,
            )

            self._append_audit(
                p,
                action="study_created",
                study_id=study_id,
                payload={
                    "study_name": study_name,
                    "ui_label": audit_label,
                    **actor_payload,
                },
            )

        self.save(p.dataset_path, f"case-e: create_study study={study_id}")
        return {"metadata": metadata, "content": content}

    def read_study(self, study_id: int, study_name: str) -> Dict[str, Any]:
        p = self.paths(study_id, study_name)
        self._get_dataset_content(p.dataset_path)
        metadata = _json_load(p.metadata_json)
        content = _json_load(p.content_json)
        if not metadata or not content:
            raise FileNotFoundError("Study not found")
        return {"metadata": metadata, "content": content}

    def list_studies(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for ds in sorted(self.root.glob("study_*")):
            meta = _json_load(ds / "canonical" / "study_metadata.json")
            if meta:
                out.append(meta)
        return out

    def update_study(
        self,
        *,
        study_id: int,
        current_study_name: str,
        study_name: Optional[str],
        study_description: Optional[str],
        study_data: Dict[str, Any],
        status: Optional[str] = None,
        last_completed_step: Optional[int] = None,
        audit_label: Optional[str] = None,
        actor: Optional[str] = None,
        actor_name: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        p = self.paths(study_id, current_study_name)
        metadata = _json_load(p.metadata_json)
        content = _json_load(p.content_json)

        if not metadata or not content:
            raise FileNotFoundError("Study not found")

        old_content = self.previous_study_content(p.dataset_path) if p.dataset_path.exists() else {}

        if study_name is not None:
            metadata["study_name"] = study_name
        if study_description is not None:
            metadata["study_description"] = study_description
        if status is not None:
            metadata["status"] = _safe_status(status)
        if last_completed_step is not None:
            metadata["last_completed_step"] = int(last_completed_step)

        metadata["updated_at"] = local_now().isoformat()
        content["id"] = int(study_id)
        content["study_id"] = int(study_id)
        content["study_data"] = _deepcopy_json(study_data or {})

        latest_version = self.latest_template_version(p)
        latest_schema_path = p.templates_dir / f"v{latest_version:03d}" / "schema.json"
        old_schema = self.previous_template_schema(p.dataset_path, latest_version)
        new_schema = self._snapshot_schema(content["study_data"], study_id, version=latest_version)

        with dataset_lock(LockSpec(dataset_path=p.dataset_path)):
            _json_dump(p.metadata_json, metadata)
            _json_dump(p.content_json, content)
            _json_dump(latest_schema_path, new_schema)

            diffs = self._compute_json_diff(
                old_content.get("study_data", {}) if isinstance(old_content, dict) else {},
                content["study_data"],
            )

            actor_payload = self._build_actor_payload(actor=actor, actor_name=actor_name, user_id=user_id)

            self._append_audit(
                p,
                action="study_edited",
                study_id=study_id,
                payload={
                    "ui_label": audit_label,
                    "diff_kind": "study_template",
                    "diff_payload": diffs,
                    "old_template_schema": old_schema,
                    **actor_payload,
                },
            )

        self.save(p.dataset_path, f"case-e: update_study study={study_id}")

        final_name = metadata["study_name"]
        new_ds_path = self.study_dataset_path(study_id, final_name)
        if new_ds_path != p.dataset_path and not new_ds_path.exists():
            shutil.move(str(p.dataset_path), str(new_ds_path))

        return {"metadata": metadata, "content": content}

    def delete_study(self, study_id: int, study_name: str) -> None:
        ds = self.study_dataset_path(study_id, study_name)
        self._delete_remote_bare_repo_if_configured(ds)
        self.delete_local_study(study_id, study_name)

    def delete_local_study(self, study_id: int, study_name: str) -> None:
        ds = self.study_dataset_path(study_id, study_name)
        if ds.exists():
            shutil.rmtree(ds, ignore_errors=True)

    def build_full_study_zip(
        self,
        *,
        study_id: int,
        study_name: str,
    ) -> tuple[Path, str]:
        ds_path = self.study_dataset_path(study_id, study_name)

        if not ds_path.exists() or not ds_path.is_dir():
            raise FileNotFoundError("Study dataset folder not found")
        self._get_dataset_content(ds_path)

        safe_study_name = _slugify(study_name)
        zip_basename = f"study_{int(study_id)}_{safe_study_name}"
        tmp_dir = Path(tempfile.mkdtemp(prefix=f"casee_study_zip_{study_id}_"))
        zip_base_path = tmp_dir / zip_basename

        archive_path = shutil.make_archive(
            base_name=str(zip_base_path),
            format="zip",
            root_dir=str(ds_path.parent),
            base_dir=ds_path.name,
        )

        return Path(archive_path), f"{zip_basename}.zip"

    # ------------------------------------------------------------------
    # templates
    # ------------------------------------------------------------------

    def latest_template_version(self, p: StudyPaths) -> int:
        versions = []
        for vdir in p.templates_dir.glob("v*"):
            m = re.match(r"v(\d+)$", vdir.name)
            if m:
                versions.append(int(m.group(1)))
        return max(versions) if versions else 1

    def list_versions(self, study_id: int, study_name: str) -> List[Dict[str, Any]]:
        p = self.paths(study_id, study_name)
        out = []
        for vdir in sorted(p.templates_dir.glob("v*")):
            m = re.match(r"v(\d+)$", vdir.name)
            if not m:
                continue
            schema = _json_load(vdir / "schema.json", {})
            out.append({
                "version": int(m.group(1)),
                "created_at": schema.get("created_at"),
            })
        return out

    def get_template(self, study_id: int, study_name: str, version: Optional[int] = None) -> Dict[str, Any]:
        p = self.paths(study_id, study_name)
        v = version or self.latest_template_version(p)
        schema = _json_load(p.templates_dir / f"v{v:03d}" / "schema.json")
        if not schema:
            raise FileNotFoundError("Template version not found")
        return {
            "study_id": study_id,
            "version": v,
            "schema": schema,
            "created_at": schema.get("created_at"),
        }

    # ------------------------------------------------------------------
    # entries
    # ------------------------------------------------------------------

    def _entry_path(
        self,
        p: StudyPaths,
        *,
        form_version: int,
        subject_index: int,
        visit_index: int,
        group_index: int,
        entry_id: int,
    ) -> Path:
        study_data = self._load_study_content_data(p)
        subject_label = self._resolve_subject_label(study_data, subject_index)
        visit_label = self._resolve_visit_label(study_data, visit_index) or f"visit_{int(visit_index) + 1:02d}"
        group_label = self._resolve_group_label(study_data, group_index) or f"group_{int(group_index) + 1:02d}"

        return (
            p.entries_dir
            / f"v{int(form_version):03d}"
            / f"subject_{int(subject_index):05d}_{subject_label}"
            / f"visit_{int(visit_index):05d}_{visit_label}"
            / f"group_{int(group_index):05d}_{group_label}"
            / f"entry_{int(entry_id):09d}.json"
        )

    def _next_entry_id(self, p: StudyPaths) -> int:
        max_id = 0
        for f in p.entries_dir.rglob("entry_*.json"):
            m = re.match(r"entry_(\d+)\.json$", f.name)
            if m:
                max_id = max(max_id, int(m.group(1)))
        return max_id + 1

    def _next_entry_id_from_rows(self, rows: List[Dict[str, Any]]) -> int:
        max_id = 0
        for row in rows or []:
            try:
                max_id = max(max_id, int(row.get("id") or 0))
            except Exception:
                continue
        return max_id + 1

    def bulk_clone_entries_to_version(
        self,
        *,
        study_id: int,
        study_name: str,
        source_version: int,
        target_version: int,
        clones: List[Dict[str, Any]],
        actor: str = "system",
        actor_name: Optional[str] = "System clone forward",
        audit_label: Optional[str] = None,
    ) -> Dict[str, Any]:
        p = self.ensure_dataset(study_id, study_name)
        self._get_dataset_content(p.dataset_path)

        with dataset_lock(LockSpec(dataset_path=p.dataset_path)):
            existing_rows = []
            for f in sorted(p.entries_dir.rglob("entry_*.json")):
                row = _json_load(f)
                if row:
                    existing_rows.append(row)
            next_entry_id = self._next_entry_id_from_rows(existing_rows)
            written_ids: List[int] = []

            for item in clones or []:
                entry_id = next_entry_id
                next_entry_id += 1

                subject_index = int(item["subject_index"])
                visit_index = int(item["visit_index"])
                group_index = int(item["group_index"])

                entry = {
                    "id": entry_id,
                    "study_id": int(study_id),
                    "subject_index": subject_index,
                    "visit_index": visit_index,
                    "group_index": group_index,
                    "form_version": int(target_version),
                    "data": _deepcopy_json(item.get("data") or {}),
                    "skipped_required_flags": _deepcopy_json(item.get("skipped_required_flags") or []),
                    "created_at": local_now().isoformat(),
                    "updated_at": local_now().isoformat(),
                    "cloned_from_version": int(source_version),
                }

                path = self._entry_path(
                    p,
                    form_version=target_version,
                    subject_index=subject_index,
                    visit_index=visit_index,
                    group_index=group_index,
                    entry_id=entry_id,
                )
                _json_dump(path, entry)

                labels = self._resolve_subject_visit_group_labels(
                    p,
                    subject_index=subject_index,
                    visit_index=visit_index,
                    group_index=group_index,
                    subject_raw=item.get("subject_raw"),
                    visit_raw=item.get("visit_raw"),
                    group_raw=item.get("group_raw"),
                )
                actor_payload = self._build_actor_payload(
                    actor=actor,
                    actor_name=actor_name,
                    user_id=None,
                )

                self._append_audit(
                    p,
                    action="entry_cloned_forward",
                    study_id=study_id,
                    payload={
                        "entry_id": entry_id,
                        "subject_index": subject_index,
                        "visit_index": visit_index,
                        "group_index": group_index,
                        "from_version": int(source_version),
                        "to_version": int(target_version),
                        "ui_label": audit_label or f"Clone entries forward v{source_version}→v{target_version}",
                        **labels,
                        **actor_payload,
                    },
                    subject_index=subject_index,
                )

                written_ids.append(entry_id)

        if written_ids:
            self.save(
                p.dataset_path,
                f"case-e: clone_entries_forward study={study_id} from_v={source_version} to_v={target_version} count={len(written_ids)}",
            )

        return {
            "written_count": len(written_ids),
            "entry_ids": written_ids,
        }

    def save_entry(
        self,
        *,
        study_id: int,
        study_name: str,
        subject_index: int,
        visit_index: int,
        group_index: int,
        form_version: int,
        data: Dict[str, Any],
        skipped_required_flags: Any,
        actor: str,
        audit_label: Optional[str] = None,
        progress_status: Optional[str] = None,
        progress_percentage: Optional[int] = None,
        progress_completed: Optional[int] = None,
        progress_total: Optional[int] = None,
        progress_skipped: Optional[int] = None,
        subject_raw: Optional[str] = None,
        visit_raw: Optional[str] = None,
        group_raw: Optional[str] = None,
        user_id: Optional[int] = None,
        actor_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        p = self.ensure_dataset(study_id, study_name)

        with dataset_lock(LockSpec(dataset_path=p.dataset_path)):
            entry_id = self._next_entry_id(p)

            entry = {
                "id": entry_id,
                "study_id": study_id,
                "subject_index": int(subject_index),
                "visit_index": int(visit_index),
                "group_index": int(group_index),
                "form_version": int(form_version),
                "data": _deepcopy_json(data or {}),
                "skipped_required_flags": _deepcopy_json(skipped_required_flags or []),
                "progress_status": progress_status,
                "progress_percentage": progress_percentage,
                "progress_completed": progress_completed,
                "progress_total": progress_total,
                "progress_skipped": progress_skipped,
                "created_at": local_now().isoformat(),
                "updated_at": local_now().isoformat(),
            }

            path = self._entry_path(
                p,
                form_version=form_version,
                subject_index=subject_index,
                visit_index=visit_index,
                group_index=group_index,
                entry_id=entry_id,
            )
            _json_dump(path, entry)

            labels = self._resolve_subject_visit_group_labels(
                p,
                subject_index=subject_index,
                visit_index=visit_index,
                group_index=group_index,
                subject_raw=subject_raw,
                visit_raw=visit_raw,
                group_raw=group_raw,
            )
            actor_payload = self._build_actor_payload(actor=actor, actor_name=actor_name, user_id=user_id)

            self._append_audit(
                p,
                action="entry_upserted",
                study_id=study_id,
                payload={
                    "entry_id": entry_id,
                    "subject_index": subject_index,
                    "visit_index": visit_index,
                    "group_index": group_index,
                    "form_version": form_version,
                    "ui_label": audit_label,
                    **labels,
                    **actor_payload,
                },
                subject_index=subject_index,
            )

        self.save(p.dataset_path, f"case-e: upsert_entry study={study_id} entry={entry_id}")
        return entry

    def update_entry(
        self,
        *,
        study_id: int,
        study_name: str,
        entry_id: int,
        payload: Dict[str, Any],
        actor: str,
        audit_label: Optional[str] = None,
        subject_raw: Optional[str] = None,
        visit_raw: Optional[str] = None,
        group_raw: Optional[str] = None,
        user_id: Optional[int] = None,
        actor_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        p = self.paths(study_id, study_name)
        target = None
        for f in p.entries_dir.rglob(f"entry_{int(entry_id):09d}.json"):
            target = f
            break
        if target is None:
            raise FileNotFoundError("Entry not found")

        with dataset_lock(LockSpec(dataset_path=p.dataset_path)):
            old_entry = _json_load(target, {})
            new_entry = _deepcopy_json(old_entry)
            new_entry.update({
                "subject_index": int(payload["subject_index"]),
                "visit_index": int(payload["visit_index"]),
                "group_index": int(payload["group_index"]),
                "data": _deepcopy_json(payload.get("data") or {}),
                "skipped_required_flags": _deepcopy_json(payload.get("skipped_required_flags") or []),
                "progress_status": payload.get("progress_status"),
                "progress_percentage": payload.get("progress_percentage"),
                "progress_completed": payload.get("progress_completed"),
                "progress_total": payload.get("progress_total"),
                "progress_skipped": payload.get("progress_skipped"),
                "updated_at": local_now().isoformat(),
            })

            diffs = self._compute_json_diff(old_entry.get("data", {}), new_entry.get("data", {}))

            new_path = self._entry_path(
                p,
                form_version=int(new_entry.get("form_version") or 1),
                subject_index=int(new_entry["subject_index"]),
                visit_index=int(new_entry["visit_index"]),
                group_index=int(new_entry["group_index"]),
                entry_id=int(entry_id),
            )

            if new_path.resolve() != target.resolve():
                new_path.parent.mkdir(parents=True, exist_ok=True)
                _json_dump(new_path, new_entry)
                try:
                    target.unlink()
                except Exception:
                    pass
            else:
                _json_dump(target, new_entry)

            labels = self._resolve_subject_visit_group_labels(
                p,
                subject_index=new_entry["subject_index"],
                visit_index=new_entry["visit_index"],
                group_index=new_entry["group_index"],
                subject_raw=subject_raw,
                visit_raw=visit_raw,
                group_raw=group_raw,
            )
            actor_payload = self._build_actor_payload(actor=actor, actor_name=actor_name, user_id=user_id)

            self._append_audit(
                p,
                action="entry_upserted",
                study_id=study_id,
                payload={
                    "entry_id": entry_id,
                    "subject_index": new_entry["subject_index"],
                    "visit_index": new_entry["visit_index"],
                    "group_index": new_entry["group_index"],
                    "ui_label": audit_label,
                    "diff_kind": "entry_data",
                    "diff_payload": diffs,
                    **labels,
                    **actor_payload,
                },
                subject_index=new_entry["subject_index"],
            )

        self.save(p.dataset_path, f"case-e: update_entry study={study_id} entry={entry_id}")
        return new_entry

    def list_entries(self, study_id: int, study_name: str) -> List[Dict[str, Any]]:
        p = self.paths(study_id, study_name)
        self._get_dataset_content(p.dataset_path)
        out = []
        for f in sorted(p.entries_dir.rglob("entry_*.json")):
            row = _json_load(f)
            if row:
                out.append(row)
        return out

    def _entry_sort_key(self, row: Dict[str, Any]) -> tuple:
        updated_at = str(row.get("updated_at") or "")
        created_at = str(row.get("created_at") or "")
        entry_id = int(row.get("id") or 0)
        return (updated_at, created_at, entry_id)

    def _stable_json_dumps(self, obj: Any) -> str:
        return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def find_entries_for_slot(
        self,
        *,
        study_id: int,
        study_name: str,
        subject_index: int,
        visit_index: int,
        group_index: int,
        form_version: int,
    ) -> List[Dict[str, Any]]:
        p = self.paths(study_id, study_name)
        out: List[Dict[str, Any]] = []

        for f in p.entries_dir.rglob("entry_*.json"):
            row = _json_load(f)
            if not row:
                continue

            try:
                if int(row.get("study_id")) != int(study_id):
                    continue
                if int(row.get("subject_index")) != int(subject_index):
                    continue
                if int(row.get("visit_index")) != int(visit_index):
                    continue
                if int(row.get("group_index")) != int(group_index):
                    continue
                if int(row.get("form_version")) != int(form_version):
                    continue
            except Exception:
                continue

            out.append(row)

        out.sort(key=self._entry_sort_key)
        return out

    def get_latest_entry_for_slot(
        self,
        *,
        study_id: int,
        study_name: str,
        subject_index: int,
        visit_index: int,
        group_index: int,
        form_version: int,
    ) -> Optional[Dict[str, Any]]:
        rows = self.find_entries_for_slot(
            study_id=study_id,
            study_name=study_name,
            subject_index=subject_index,
            visit_index=visit_index,
            group_index=group_index,
            form_version=form_version,
        )
        return rows[-1] if rows else None

    def compute_entry_revision_token(self, entry: Optional[Dict[str, Any]]) -> str:
        if not entry:
            payload = {
                "empty": True,
            }
        else:
            payload = {
                "id": entry.get("id"),
                "study_id": entry.get("study_id"),
                "subject_index": entry.get("subject_index"),
                "visit_index": entry.get("visit_index"),
                "group_index": entry.get("group_index"),
                "form_version": entry.get("form_version"),
                "data": entry.get("data") or {},
                "skipped_required_flags": entry.get("skipped_required_flags") or [],
                "updated_at": entry.get("updated_at"),
                "created_at": entry.get("created_at"),
            }

        raw = self._stable_json_dumps(payload).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def get_current_slot_state(
        self,
        *,
        study_id: int,
        study_name: str,
        subject_index: int,
        visit_index: int,
        group_index: int,
        form_version: int,
    ) -> Dict[str, Any]:
        latest = self.get_latest_entry_for_slot(
            study_id=study_id,
            study_name=study_name,
            subject_index=subject_index,
            visit_index=visit_index,
            group_index=group_index,
            form_version=form_version,
        )

        labels = self._resolve_subject_visit_group_labels(
            self.paths(study_id, study_name),
            subject_index=subject_index,
            visit_index=visit_index,
            group_index=group_index,
        )

        if not latest:
            return {
                "exists": False,
                "entry_id": None,
                "study_id": int(study_id),
                "subject_index": int(subject_index),
                "visit_index": int(visit_index),
                "group_index": int(group_index),
                "form_version": int(form_version),
                "data": {},
                "skipped_required_flags": [],
                "created_at": None,
                "updated_at": None,
                "revision_token": self.compute_entry_revision_token(None),
                **labels,
            }

        return {
            "exists": True,
            "entry_id": latest.get("id"),
            "study_id": int(study_id),
            "subject_index": int(subject_index),
            "visit_index": int(visit_index),
            "group_index": int(group_index),
            "form_version": int(form_version),
            "data": _deepcopy_json(latest.get("data") or {}),
            "skipped_required_flags": _deepcopy_json(latest.get("skipped_required_flags") or []),
            "created_at": latest.get("created_at"),
            "updated_at": latest.get("updated_at"),
            "revision_token": self.compute_entry_revision_token(latest),
            **labels,
        }

    def assert_slot_revision_unchanged(
        self,
        *,
        study_id: int,
        study_name: str,
        subject_index: int,
        visit_index: int,
        group_index: int,
        form_version: int,
        expected_revision_token: Optional[str],
    ) -> Dict[str, Any]:
        latest_state = self.get_current_slot_state(
            study_id=study_id,
            study_name=study_name,
            subject_index=subject_index,
            visit_index=visit_index,
            group_index=group_index,
            form_version=form_version,
        )

        current_token = str(latest_state.get("revision_token") or "")
        expected_token = str(expected_revision_token or "")

        if expected_token != current_token:
            raise ValueError("Slot state changed")

        return latest_state

    def version_has_entries(self, study_id: int, study_name: str, version: int) -> bool:
        p = self.paths(study_id, study_name)
        version_dir = p.entries_dir / f"v{int(version):03d}"
        if not version_dir.exists():
            return False
        for _ in version_dir.rglob("entry_*.json"):
            return True
        return False

    def list_latest_entries_by_slot(self, study_id: int, study_name: str) -> List[Dict[str, Any]]:
        rows = self.list_entries(study_id, study_name)
        latest_by_slot: Dict[tuple, Dict[str, Any]] = {}

        for row in rows:
            try:
                key = (
                    int(row.get("subject_index")),
                    int(row.get("visit_index")),
                    int(row.get("group_index")),
                    int(row.get("form_version")),
                )
            except Exception:
                continue

            prev = latest_by_slot.get(key)
            if prev is None or self._entry_sort_key(row) > self._entry_sort_key(prev):
                latest_by_slot[key] = row

        out = list(latest_by_slot.values())
        out.sort(key=self._entry_sort_key)
        return out

    # ------------------------------------------------------------------
    # files
    # ------------------------------------------------------------------

    def _next_file_id(self, p: StudyPaths) -> int:
        max_id = 0
        for f in p.files_dir.glob("file_*.json"):
            m = re.match(r"file_(\d+)\.json$", f.name)
            if m:
                max_id = max(max_id, int(m.group(1)))
        return max_id + 1

    def save_uploaded_file(
        self,
        *,
        study_id: int,
        study_name: str,
        filename: str,
        source_path: str,
        description: str = "",
        subject_index: Optional[int] = None,
        visit_index: Optional[int] = None,
        group_index: Optional[int] = None,
        modalities: Optional[List[str]] = None,
        form_version: Optional[int] = None,
        actor: str,
        audit_label: Optional[str] = None,
        user_id: Optional[int] = None,
        actor_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        p = self.ensure_dataset(study_id, study_name)

        with dataset_lock(LockSpec(dataset_path=p.dataset_path)):
            file_id = self._next_file_id(p)

            original_name = _safe_filename(filename)
            stored_name = f"{file_id:09d}_{original_name}"

            target_dir = self._resolve_file_storage_dir(
                p,
                subject_index=subject_index,
                visit_index=visit_index,
                group_index=group_index,
                modalities=modalities,
                form_version=form_version,
            )
            dest = target_dir / stored_name

            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, dest)

            record = {
                "id": file_id,
                "study_id": study_id,
                "file_name": original_name,
                "file_path": self._logical_path(p.dataset_path, dest),
                "description": description or "",
                "storage_option": "bids",
                "subject_index": subject_index,
                "visit_index": visit_index,
                "group_index": group_index,
                "modalities": modalities or [],
                "form_version": int(form_version) if form_version is not None else None,
                "created_at": local_now().isoformat(),
            }
            _json_dump(p.files_dir / f"file_{file_id:09d}.json", record)

            labels = self._resolve_subject_visit_group_labels(
                p,
                subject_index=subject_index,
                visit_index=visit_index,
                group_index=group_index,
            )
            actor_payload = self._build_actor_payload(actor=actor, actor_name=actor_name, user_id=user_id)

            self._append_audit(
                p,
                action="file_added",
                study_id=study_id,
                payload={
                    "file_id": file_id,
                    "file_name": original_name,
                    "stored_file_name": stored_name,
                    "stored_path": self._logical_path(p.dataset_path, dest),
                    "modalities": modalities or [],
                    "form_version": int(form_version) if form_version is not None else None,
                    "ui_label": audit_label,
                    "subject_index": subject_index,
                    "visit_index": visit_index,
                    "group_index": group_index,
                    **labels,
                    **actor_payload,
                },
                subject_index=subject_index,
            )

        self.save(p.dataset_path, f"case-e: upload_file study={study_id} file={file_id}")
        return record

    def save_url_file(
        self,
        *,
        study_id: int,
        study_name: str,
        url: str,
        description: str = "",
        subject_index: Optional[int] = None,
        visit_index: Optional[int] = None,
        group_index: Optional[int] = None,
        modalities: Optional[List[str]] = None,
        form_version: Optional[int] = None,
        actor: str,
        audit_label: Optional[str] = None,
        user_id: Optional[int] = None,
        actor_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        p = self.ensure_dataset(study_id, study_name)

        with dataset_lock(LockSpec(dataset_path=p.dataset_path)):
            file_id = self._next_file_id(p)
            name = _safe_filename(os.path.basename(url) or "link")

            target_dir = self._resolve_file_storage_dir(
                p,
                subject_index=subject_index,
                visit_index=visit_index,
                group_index=group_index,
                modalities=modalities,
                form_version=form_version,
            )
            target_dir.mkdir(parents=True, exist_ok=True)

            record = {
                "id": file_id,
                "study_id": study_id,
                "file_name": name,
                "file_path": url,
                "description": description or "",
                "storage_option": "url",
                "subject_index": subject_index,
                "visit_index": visit_index,
                "group_index": group_index,
                "modalities": modalities or [],
                "form_version": int(form_version) if form_version is not None else None,
                "created_at": local_now().isoformat(),
            }
            _json_dump(p.files_dir / f"file_{file_id:09d}.json", record)

            labels = self._resolve_subject_visit_group_labels(
                p,
                subject_index=subject_index,
                visit_index=visit_index,
                group_index=group_index,
            )
            actor_payload = self._build_actor_payload(actor=actor, actor_name=actor_name, user_id=user_id)

            self._append_audit(
                p,
                action="file_added",
                study_id=study_id,
                payload={
                    "file_id": file_id,
                    "url": url,
                    "file_name": name,
                    "modalities": modalities or [],
                    "form_version": int(form_version) if form_version is not None else None,
                    "ui_label": audit_label,
                    "subject_index": subject_index,
                    "visit_index": visit_index,
                    "group_index": group_index,
                    **labels,
                    **actor_payload,
                },
                subject_index=subject_index,
            )

        self.save(p.dataset_path, f"case-e: create_url_file study={study_id} file={file_id}")
        return record

    def list_files(self, study_id: int, study_name: str) -> List[Dict[str, Any]]:
        p = self.paths(study_id, study_name)
        self._get_dataset_content(p.dataset_path)
        out = []
        for f in sorted(p.files_dir.glob("file_*.json")):
            if re.match(r"file_\d+\.json$", f.name):
                row = _json_load(f)
                if row:
                    out.append(row)
        return out

    def get_file_record(
        self,
        *,
        study_id: int,
        study_name: str,
        file_id: int,
    ) -> Dict[str, Any]:
        p = self.paths(study_id, study_name)
        self._get_dataset_content(p.dataset_path)
        rec_path = p.files_dir / f"file_{int(file_id):09d}.json"
        row = _json_load(rec_path)

        if not row:
            raise FileNotFoundError("File record not found")

        return row

    def get_file_for_download(
        self,
        *,
        study_id: int,
        study_name: str,
        file_id: int,
    ) -> Dict[str, Any]:
        p = self.paths(study_id, study_name)
        row = self.get_file_record(
            study_id=study_id,
            study_name=study_name,
            file_id=file_id,
        )

        storage_option = str(row.get("storage_option") or "").strip().lower()

        if storage_option == "url":
            url = row.get("file_path")
            if not url:
                raise FileNotFoundError("URL file path not found")

            return {
                "id": row.get("id"),
                "study_id": row.get("study_id"),
                "file_name": row.get("file_name") or "link",
                "storage_option": "url",
                "url": url,
            }

        rel_path = row.get("file_path")
        if not rel_path:
            raise FileNotFoundError("Stored file path not found")

        abs_path = (p.dataset_path / rel_path).resolve()
        self._get_dataset_content(p.dataset_path, abs_path)

        dataset_root = p.dataset_path.resolve()
        try:
            abs_path.relative_to(dataset_root)
        except Exception:
            raise ValueError("Invalid file path outside study dataset")

        if not abs_path.exists() or not abs_path.is_file():
            raise FileNotFoundError("Stored file not found on disk")

        return {
            "id": row.get("id"),
            "study_id": row.get("study_id"),
            "file_name": row.get("file_name") or abs_path.name,
            "storage_option": storage_option or "bids",
            "absolute_path": abs_path,
            "record": row,
        }

    # ------------------------------------------------------------------
    # access / shares
    # ------------------------------------------------------------------

    def save_access_grant(
        self,
        *,
        study_id: int,
        study_name: str,
        user_id: int,
        permissions: Dict[str, Any],
        created_by: int,
        actor: Optional[str] = None,
        actor_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        p = self.ensure_dataset(study_id, study_name)
        row = {
            "study_id": study_id,
            "user_id": user_id,
            "permissions": permissions or {"view": True, "add_data": True, "edit_study": False},
            "created_by": created_by,
            "created_at": local_now().isoformat(),
        }

        with dataset_lock(LockSpec(dataset_path=p.dataset_path)):
            _json_dump(p.access_dir / f"user_{int(user_id):09d}.json", row)

            actor_payload = self._build_actor_payload(
                actor=actor,
                actor_name=actor_name,
                user_id=created_by,
            )

            self._append_audit(
                p,
                action="access_changed",
                study_id=study_id,
                payload={
                    "target_user_id": user_id,
                    "permissions": row["permissions"],
                    **actor_payload,
                },
            )

        self.save(p.dataset_path, f"case-e: access_change study={study_id} user={user_id}")
        return row

    def revoke_access_grant(
        self,
        *,
        study_id: int,
        study_name: str,
        user_id: int,
        actor: Optional[str] = None,
        actor_name: Optional[str] = None,
        acting_user_id: Optional[int] = None,
    ) -> None:
        p = self.paths(study_id, study_name)
        f = p.access_dir / f"user_{int(user_id):09d}.json"
        if f.exists():
            with dataset_lock(LockSpec(dataset_path=p.dataset_path)):
                if f.exists():
                    f.unlink()

                actor_payload = self._build_actor_payload(
                    actor=actor,
                    actor_name=actor_name,
                    user_id=acting_user_id,
                )

                self._append_audit(
                    p,
                    action="access_revoked",
                    study_id=study_id,
                    payload={
                        "target_user_id": user_id,
                        **actor_payload,
                    },
                )

            self.save(p.dataset_path, f"case-e: revoke_access study={study_id} user={user_id}")

    def list_access(self, study_id: int, study_name: str) -> List[Dict[str, Any]]:
        p = self.paths(study_id, study_name)
        out = []
        for f in sorted(p.access_dir.glob("user_*.json")):
            row = _json_load(f)
            if row:
                out.append(row)
        return out

    def save_share_link(
        self,
        *,
        study_id: int,
        study_name: str,
        token: str,
        subject_index: int,
        visit_index: int,
        group_index: int,
        permission: str,
        max_uses: int,
        expires_at: str,
        allowed_section_ids: List[str],
        actor: Optional[str] = None,
        actor_name: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        p = self.ensure_dataset(study_id, study_name)
        row = {
            "token": token,
            "study_id": study_id,
            "subject_index": subject_index,
            "visit_index": visit_index,
            "group_index": group_index,
            "permission": permission,
            "max_uses": max_uses,
            "used_count": 0,
            "expires_at": expires_at,
            "allowed_section_ids": allowed_section_ids or [],
            "created_at": local_now().isoformat(),
        }

        with dataset_lock(LockSpec(dataset_path=p.dataset_path)):
            _json_dump(p.shares_dir / f"{token}.json", row)

            labels = self._resolve_subject_visit_group_labels(
                p,
                subject_index=subject_index,
                visit_index=visit_index,
                group_index=group_index,
            )
            actor_payload = self._build_actor_payload(actor=actor, actor_name=actor_name, user_id=user_id)

            self._append_audit(
                p,
                action="share_link_created",
                study_id=study_id,
                payload={
                    "permission": permission,
                    "max_uses": max_uses,
                    "expires_at": expires_at,
                    "allowed_section_ids": allowed_section_ids or [],
                    "subject_index": subject_index,
                    "visit_index": visit_index,
                    "group_index": group_index,
                    **labels,
                    **actor_payload,
                },
                subject_index=subject_index,
            )

        self.save(p.dataset_path, f"case-e: share_link_created study={study_id}")
        return row

    def read_share_link(self, *, study_id: int, study_name: str, token: str) -> Dict[str, Any]:
        p = self.paths(study_id, study_name)
        row = _json_load(p.shares_dir / f"{token}.json")
        if not row:
            raise FileNotFoundError("Shared link not found")
        return row

    def update_share_link(self, *, study_id: int, study_name: str, token: str, row: Dict[str, Any]) -> None:
        p = self.paths(study_id, study_name)
        with dataset_lock(LockSpec(dataset_path=p.dataset_path)):
            _json_dump(p.shares_dir / f"{token}.json", row)
        self.save(p.dataset_path, f"case-e: shared_link_used study={study_id}")

    # ------------------------------------------------------------------
    # audit helpers
    # ------------------------------------------------------------------

    def _subject_audit_dir(self, p: StudyPaths, subject_index: Optional[int]) -> Optional[Path]:
        if subject_index is None:
            return None

        study_data = self._load_study_content_data(p)
        subject_label = self._resolve_subject_label(study_data, subject_index)
        subdir = p.audit_subject_dir / f"subject_{int(subject_index):05d}_{subject_label}"
        subdir.mkdir(parents=True, exist_ok=True)
        return subdir

    def _write_diff_blob(self, scope_dir: Path, event_id: str, diff_obj: Any) -> str:
        diffs_dir = scope_dir / "diffs"
        diffs_dir.mkdir(parents=True, exist_ok=True)
        diff_file = diffs_dir / f"{event_id}.json"
        _json_dump(diff_file, diff_obj)
        return str(diff_file.relative_to(self.paths_from_scope_dir(scope_dir).canonical_dir))

    def paths_from_scope_dir(self, scope_dir: Path) -> StudyPaths:
        canonical_dir = scope_dir
        while canonical_dir.name != "canonical" and canonical_dir.parent != canonical_dir:
            canonical_dir = canonical_dir.parent
        dataset_path = canonical_dir.parent
        return StudyPaths(
            dataset_path=dataset_path,
            canonical_dir=canonical_dir,
            metadata_json=canonical_dir / "study_metadata.json",
            content_json=canonical_dir / "study_content.json",
            templates_dir=canonical_dir / "templates",
            entries_dir=canonical_dir / "entries",
            files_dir=canonical_dir / "files",
            audit_dir=canonical_dir / "audit",
            audit_system_dir=canonical_dir / "audit" / "system",
            audit_system_study_dir=canonical_dir / "audit" / "system" / "study",
            audit_subject_dir=canonical_dir / "audit" / "subject",
            shares_dir=canonical_dir / "shared_links",
            access_dir=canonical_dir / "access",
        )

    def _append_audit(
        self,
        p: StudyPaths,
        *,
        action: str,
        study_id: int,
        payload: Dict[str, Any],
        subject_index: Optional[int] = None,
    ) -> None:
        now = local_now()
        ts = now.strftime("%Y%m%dT%H%M%S%f")
        scope = "subject" if subject_index is not None else "study"

        if scope == "study":
            scope_dir = p.audit_system_study_dir
            subject_suffix = ""
        else:
            scope_dir = self._subject_audit_dir(p, subject_index)
            subject_suffix = f"_s{int(subject_index):05d}"

        if scope_dir is None:
            raise RuntimeError("Failed to resolve audit scope directory")

        event_id = f"{ts}_{action}{subject_suffix}"
        safe_payload = _deepcopy_json(payload or {})

        diff_obj = None
        if safe_payload.get("diff_payload") is not None:
            diff_obj = safe_payload.pop("diff_payload")
        elif safe_payload.get("old_content") is not None:
            diff_obj = {"old_content": safe_payload.pop("old_content")}
        elif safe_payload.get("old_template_schema") is not None:
            diff_obj = {"old_template_schema": safe_payload.pop("old_template_schema")}

        diff_available = False
        diff_path = None
        if diff_obj is not None:
            diff_available = True
            diff_path = self._write_diff_blob(scope_dir, event_id, diff_obj)

        body = {
            "id": event_id,
            "timestamp": now.isoformat(),
            "study_id": int(study_id),
            "action": action,
            "scope": scope,
            "payload": safe_payload,
            "diff_available": diff_available,
            "diff_path": diff_path,
        }

        _append_jsonl(scope_dir / "events.jsonl", body)

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    def _snapshot_schema(self, study_data: Dict[str, Any], study_id: int, version: int = 1) -> Dict[str, Any]:
        snap = _deepcopy_json(study_data or {})
        snap.setdefault("id", study_id)
        if "study" not in snap or not isinstance(snap.get("study"), dict):
            snap["study"] = {
                "title": snap.get("title", ""),
                "description": snap.get("description", ""),
            }
        snap["created_at"] = local_now().isoformat()
        snap["version"] = int(version)
        return snap

    def _compute_json_diff(self, old: Any, new: Any, path: str = "") -> List[Dict[str, Any]]:
        diffs: List[Dict[str, Any]] = []

        if old is new:
            return diffs

        if isinstance(old, (str, int, float, bool)) or old is None or \
           isinstance(new, (str, int, float, bool)) or new is None:
            if old != new:
                diffs.append({"op": "replace", "path": path or "/", "old": old, "new": new})
            return diffs

        if isinstance(old, dict) and isinstance(new, dict):
            old_keys = set(old.keys())
            new_keys = set(new.keys())

            for k in sorted(old_keys - new_keys):
                p = f"{path}/{k}" if path else f"/{k}"
                diffs.append({"op": "remove", "path": p, "old": old.get(k), "new": None})

            for k in sorted(new_keys - old_keys):
                p = f"{path}/{k}" if path else f"/{k}"
                diffs.append({"op": "add", "path": p, "old": None, "new": new.get(k)})

            for k in sorted(old_keys & new_keys):
                p = f"{path}/{k}" if path else f"/{k}"
                diffs.extend(self._compute_json_diff(old.get(k), new.get(k), p))
            return diffs

        if isinstance(old, list) and isinstance(new, list):
            min_len = min(len(old), len(new))
            for i in range(min_len):
                p = f"{path}/{i}" if path else f"/{i}"
                diffs.extend(self._compute_json_diff(old[i], new[i], p))
            for i in range(len(new), len(old)):
                p = f"{path}/{i}" if path else f"/{i}"
                diffs.append({"op": "remove", "path": p, "old": old[i], "new": None})
            for i in range(len(old), len(new)):
                p = f"{path}/{i}" if path else f"/{i}"
                diffs.append({"op": "add", "path": p, "old": None, "new": new[i]})
            return diffs

        if old != new:
            diffs.append({"op": "replace", "path": path or "/", "old": old, "new": new})
        return diffs
