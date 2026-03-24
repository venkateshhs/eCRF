# eCRF_backend/datalad_repo.py
from __future__ import annotations

import copy
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .logger import logger
from .bids_exporter_datalad import _dataset_path, latest_writable_version, get_version_schema
try:
    from datalad.api import Dataset  # type: ignore
except Exception:
    Dataset = None  # type: ignore


ALLOWED_STUDY_STATUS = {"DRAFT", "PUBLISHED", "ARCHIVED"}


def local_now() -> datetime:
    return datetime.now(timezone.utc)


def _slugify(value: str) -> str:
    s = (value or "").strip()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^A-Za-z0-9_\-]+", "", s)
    return s[:120] or "study"


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
    lines = []
    if gitignore.exists():
        lines = gitignore.read_text(encoding="utf-8").splitlines()
    wanted = {".DS_Store", "*.lock"}
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


def _git_show_json(ds_path: Path, rev: str, rel_path: str, default: Any = None) -> Any:
    try:
        raw = _run_git(ds_path, ["show", f"{rev}:{rel_path}"])
        return json.loads(raw)
    except Exception:
        return default


def _safe_status(s: Optional[str]) -> str:
    s2 = (s or "PUBLISHED").strip().upper()
    return s2 if s2 in ALLOWED_STUDY_STATUS else "PUBLISHED"


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
    shares_dir: Path
    access_dir: Path


class DataladStudyRepo:
    def __init__(self, root: Optional[str] = None) -> None:
        base = root or os.environ.get("BIDS_ROOT") or str(Path(os.environ["ECRF_DATA_DIR"]) / "bids_datasets")
        self.root = Path(base)
        self.root.mkdir(parents=True, exist_ok=True)

    def next_study_id(self) -> int:
        max_id = 0
        for ds in self.root.glob("study_*"):
            m = re.match(r"study_(\d+)_?.*$", ds.name)
            if m:
                max_id = max(max_id, int(m.group(1)))
        return max_id + 1
    def get_study_name_by_id(self, study_id: int) -> str:
        for ds in sorted(self.root.glob("study_*")):
            meta = _json_load(ds / "canonical" / "study_metadata.json")
            if meta and int(meta.get("id", -1)) == int(study_id):
                return str(meta.get("study_name") or "")
        raise FileNotFoundError("Study not found")
    # ---------- dataset layout ----------

    def study_dataset_path(self, study_id: int, study_name: str) -> Path:
        return Path(_dataset_path(study_id, study_name))

    def paths(self, study_id: int, study_name: str) -> StudyPaths:
        ds = self.study_dataset_path(study_id, study_name)
        c = ds / "canonical"
        return StudyPaths(
            dataset_path=ds,
            canonical_dir=c,
            metadata_json=c / "study_metadata.json",
            content_json=c / "study_content.json",
            templates_dir=c / "templates",
            entries_dir=c / "entries",
            files_dir=c / "files",
            audit_dir=c / "audit",
            shares_dir=c / "shared_links",
            access_dir=c / "access",
        )

    def ensure_dataset(self, study_id: int, study_name: str) -> StudyPaths:
        p = self.paths(study_id, study_name)
        p.dataset_path.mkdir(parents=True, exist_ok=True)

        if Dataset is None:
            raise RuntimeError("DataLad is not installed")

        ds = Dataset(str(p.dataset_path))
        if not ds.is_installed():
            ds.create(force=True, cfg_proc="text2git")

        _ensure_gitignore(p.dataset_path)

        for d in [
            p.canonical_dir,
            p.templates_dir,
            p.entries_dir,
            p.files_dir,
            p.audit_dir,
            p.shares_dir,
            p.access_dir,
        ]:
            d.mkdir(parents=True, exist_ok=True)

        return p

    # ---------- git / datalad history ----------

    def save(self, ds_path: Path, message: str) -> None:
        if Dataset is None:
            raise RuntimeError("DataLad is not installed")
        Dataset(str(ds_path)).save(message=message)
        logger.info("Saved dataset: %s msg=%s", ds_path, message)

    def previous_study_content(self, ds_path: Path) -> Dict[str, Any]:
        return _git_show_json(ds_path, "HEAD~1", "canonical/study_content.json", default={}) or {}

    def previous_template_schema(self, ds_path: Path, version: int) -> Dict[str, Any]:
        rel = f"canonical/templates/v{int(version):03d}/schema.json"
        return _git_show_json(ds_path, "HEAD~1", rel, default={}) or {}

    # ---------- study CRUD ----------

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

        _json_dump(p.metadata_json, metadata)
        _json_dump(p.content_json, content)

        v1_dir = p.templates_dir / "v001"
        v1_dir.mkdir(parents=True, exist_ok=True)
        _json_dump(v1_dir / "schema.json", self._snapshot_schema(study_data or {}, study_id))

        self._append_audit(
            p.audit_dir,
            action="study_created",
            study_id=study_id,
            payload={"study_name": study_name},
        )

        self.save(p.dataset_path, f"case-e: create_study study={study_id}")

        return {"metadata": metadata, "content": content}

    def read_study(self, study_id: int, study_name: str) -> Dict[str, Any]:
        p = self.paths(study_id, study_name)
        metadata = _json_load(p.metadata_json)
        content = _json_load(p.content_json)
        if not metadata or not content:
            raise FileNotFoundError("Study not found")
        if "id" not in content:
            content["id"] = int(study_id)
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
        content["study_data"] = _deepcopy_json(study_data or {})

        _json_dump(p.metadata_json, metadata)
        _json_dump(p.content_json, content)

        latest_version = latest_writable_version(study_id, current_study_name)
        latest_schema_path = p.templates_dir / f"v{latest_version:03d}" / "schema.json"
        latest_schema_path.parent.mkdir(parents=True, exist_ok=True)
        old_schema = get_version_schema(study_id, current_study_name, latest_version) or {}

        new_schema = self._snapshot_schema(content["study_data"], study_id)
        _json_dump(latest_schema_path, new_schema)

        diffs = self._compute_json_diff(
            old_content.get("study_data", {}) if isinstance(old_content, dict) else {},
            content["study_data"],
        )

        self._append_audit(
            p.audit_dir,
            action="study_edited",
            study_id=study_id,
            payload={
                "ui_label": audit_label,
                "diff_kind": "study_template",
                "diff_payload": diffs,
                "old_template_schema": old_schema,
            },
        )

        final_name = metadata["study_name"]
        new_ds_path = self.study_dataset_path(study_id, final_name)

        if new_ds_path != p.dataset_path and not new_ds_path.exists():
            shutil.move(str(p.dataset_path), str(new_ds_path))
            p = self.paths(study_id, final_name)

        self.save(p.dataset_path, f"case-e: update_study study={study_id}")
        content["id"] = int(study_id)
        return {"metadata": metadata, "content": content}

    def delete_study(self, study_id: int, study_name: str) -> None:
        ds = self.study_dataset_path(study_id, study_name)
        if ds.exists():
            shutil.rmtree(ds, ignore_errors=True)

    # ---------- templates ----------

    def latest_template_version(self, study_id: int, study_name: str) -> int:
        return latest_writable_version(study_id, study_name)

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
        v = int(version) if version is not None else latest_writable_version(study_id, study_name)
        schema = get_version_schema(study_id, study_name, v)
        if not schema:
            raise FileNotFoundError("Template version not found")
        return {
            "study_id": study_id,
            "version": v,
            "schema": schema,
            "created_at": schema.get("created_at"),
        }

    # ---------- entries ----------

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
        return (
            p.entries_dir
            / f"v{int(form_version):03d}"
            / f"subject_{int(subject_index):05d}"
            / f"visit_{int(visit_index):05d}"
            / f"group_{int(group_index):05d}"
            / f"entry_{int(entry_id):09d}.json"
        )

    def _next_entry_id(self, p: StudyPaths) -> int:
        max_id = 0
        for f in p.entries_dir.rglob("entry_*.json"):
            m = re.match(r"entry_(\d+)\.json$", f.name)
            if m:
                max_id = max(max_id, int(m.group(1)))
        return max_id + 1

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
    ) -> Dict[str, Any]:
        p = self.ensure_dataset(study_id, study_name)
        entry_id = self._next_entry_id(p)
        (p.templates_dir / f"v{int(form_version):03d}").mkdir(parents=True, exist_ok=True)

        entry = {
            "id": entry_id,
            "study_id": study_id,
            "subject_index": int(subject_index),
            "visit_index": int(visit_index),
            "group_index": int(group_index),
            "form_version": int(form_version),
            "data": _deepcopy_json(data or {}),
            "skipped_required_flags": _deepcopy_json(skipped_required_flags or []),
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

        self._append_audit(
            p.audit_dir,
            action="entry_upserted",
            study_id=study_id,
            payload={
                "entry_id": entry_id,
                "subject_index": subject_index,
                "visit_index": visit_index,
                "group_index": group_index,
                "form_version": form_version,
                "ui_label": audit_label,
                "actor": actor,
            },
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
    ) -> Dict[str, Any]:
        p = self.paths(study_id, study_name)
        target = None
        for f in p.entries_dir.rglob(f"entry_{int(entry_id):09d}.json"):
            target = f
            break
        if target is None:
            raise FileNotFoundError("Entry not found")

        old_entry = _json_load(target, {})
        new_entry = _deepcopy_json(old_entry)
        new_entry.update({
            "subject_index": int(payload["subject_index"]),
            "visit_index": int(payload["visit_index"]),
            "group_index": int(payload["group_index"]),
            "data": _deepcopy_json(payload.get("data") or {}),
            "skipped_required_flags": _deepcopy_json(payload.get("skipped_required_flags") or []),
            "updated_at": local_now().isoformat(),
        })

        diffs = self._compute_json_diff(old_entry.get("data", {}), new_entry.get("data", {}))
        _json_dump(target, new_entry)

        self._append_audit(
            p.audit_dir,
            action="entry_upserted",
            study_id=study_id,
            payload={
                "entry_id": entry_id,
                "ui_label": audit_label,
                "actor": actor,
                "diff_kind": "entry_data",
                "diff_payload": diffs,
            },
        )

        self.save(p.dataset_path, f"case-e: update_entry study={study_id} entry={entry_id}")
        return new_entry

    def list_entries(self, study_id: int, study_name: str) -> List[Dict[str, Any]]:
        p = self.paths(study_id, study_name)
        out = []
        for f in sorted(p.entries_dir.rglob("entry_*.json")):
            row = _json_load(f)
            if row:
                out.append(row)
        return out

    # ---------- files ----------

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
        actor: str,
        audit_label: Optional[str] = None,
    ) -> Dict[str, Any]:
        p = self.ensure_dataset(study_id, study_name)
        file_id = self._next_file_id(p)
        ext = Path(filename).suffix
        dest = p.files_dir / f"file_{file_id:09d}{ext}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, dest)

        record = {
            "id": file_id,
            "study_id": study_id,
            "file_name": filename,
            "file_path": str(dest.relative_to(p.dataset_path)),
            "description": description or "",
            "storage_option": "bids",
            "subject_index": subject_index,
            "visit_index": visit_index,
            "group_index": group_index,
            "created_at": local_now().isoformat(),
        }
        _json_dump(p.files_dir / f"file_{file_id:09d}.json", record)

        self._append_audit(
            p.audit_dir,
            action="file_added",
            study_id=study_id,
            payload={
                "file_id": file_id,
                "file_name": filename,
                "ui_label": audit_label,
                "actor": actor,
            },
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
        actor: str,
        audit_label: Optional[str] = None,
    ) -> Dict[str, Any]:
        p = self.ensure_dataset(study_id, study_name)
        file_id = self._next_file_id(p)
        name = os.path.basename(url) or "link"

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
            "created_at": local_now().isoformat(),
        }
        _json_dump(p.files_dir / f"file_{file_id:09d}.json", record)

        self._append_audit(
            p.audit_dir,
            action="file_added",
            study_id=study_id,
            payload={
                "file_id": file_id,
                "url": url,
                "ui_label": audit_label,
                "actor": actor,
            },
        )

        self.save(p.dataset_path, f"case-e: create_url_file study={study_id} file={file_id}")
        return record

    def list_files(self, study_id: int, study_name: str) -> List[Dict[str, Any]]:
        p = self.paths(study_id, study_name)
        out = []
        for f in sorted(p.files_dir.glob("file_*.json")):
            if re.match(r"file_\d+\.json$", f.name):
                row = _json_load(f)
                if row:
                    out.append(row)
        return out

    def _next_file_id(self, p: StudyPaths) -> int:
        max_id = 0
        for f in p.files_dir.glob("file_*.json"):
            m = re.match(r"file_(\d+)\.json$", f.name)
            if m:
                max_id = max(max_id, int(m.group(1)))
        return max_id + 1

    # ---------- access / shares ----------

    def save_access_grant(
        self,
        *,
        study_id: int,
        study_name: str,
        user_id: int,
        permissions: Dict[str, Any],
        created_by: int,
    ) -> Dict[str, Any]:
        p = self.ensure_dataset(study_id, study_name)
        row = {
            "study_id": study_id,
            "user_id": user_id,
            "permissions": permissions or {"view": True, "add_data": True, "edit_study": False},
            "created_by": created_by,
            "created_at": local_now().isoformat(),
        }
        _json_dump(p.access_dir / f"user_{int(user_id):09d}.json", row)
        self.save(p.dataset_path, f"case-e: access_change study={study_id} user={user_id}")
        return row

    def revoke_access_grant(self, *, study_id: int, study_name: str, user_id: int) -> None:
        p = self.paths(study_id, study_name)
        f = p.access_dir / f"user_{int(user_id):09d}.json"
        if f.exists():
            f.unlink()
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
        _json_dump(p.shares_dir / f"{token}.json", row)
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
        _json_dump(p.shares_dir / f"{token}.json", row)
        self.save(p.dataset_path, f"case-e: shared_link_used study={study_id}")

    # ---------- internal helpers ----------

    def _snapshot_schema(self, study_data: Dict[str, Any], study_id: int) -> Dict[str, Any]:
        snap = _deepcopy_json(study_data or {})
        snap.setdefault("id", study_id)
        if "study" not in snap or not isinstance(snap.get("study"), dict):
            snap["study"] = {
                "title": snap.get("title", ""),
                "description": snap.get("description", ""),
            }
        snap["created_at"] = local_now().isoformat()
        return snap

    def _append_audit(self, audit_dir: Path, *, action: str, study_id: int, payload: Dict[str, Any]) -> None:
        ts = local_now().strftime("%Y%m%dT%H%M%S")
        file = audit_dir / f"{ts}_{action}.json"
        _json_dump(file, {
            "timestamp": local_now().isoformat(),
            "study_id": study_id,
            "action": action,
            "payload": payload or {},
        })

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