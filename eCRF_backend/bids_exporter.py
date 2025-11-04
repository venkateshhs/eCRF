# bids_exported.py
import os
import re
import csv
import json
import logging
import pathlib
import shutil
import sys
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from urllib.parse import urlparse

from filelock import FileLock

from .crud import record_event as _db_record_event  # (db, user_id, study_id, subject_id, action, details)

logger = logging.getLogger(__name__)

# -------------------- Config --------------------

def _runtime_base_dir() -> str:
    """
    Where should we put persistent data when running:
      - frozen (PyInstaller): alongside the executable (dist/eCRF)
      - dev: the project root (parent of eCRF_backend)
    """
    try:
        if getattr(sys, "frozen", False):
            return os.path.dirname(os.path.abspath(sys.executable))
        # dev: parent of this file's directory (…/eCRF_backend/..)
        here = os.path.dirname(os.path.abspath(__file__))
        return os.path.abspath(os.path.join(here, ".."))
    except Exception:
        return os.getcwd()

# Default BIDS root = <base>/ecrf_data/bids_datasets
_DEFAULT_BIDS_ROOT = os.path.join(_runtime_base_dir(), "ecrf_data", "bids_datasets")

# Allow override via env var if needed
BIDS_ROOT = os.getenv("BIDS_ROOT", _DEFAULT_BIDS_ROOT)

# Declared BIDS spec version
BIDS_VERSION = os.getenv("BIDS_VERSION", "1.8.0")

# Optional DataLad integration (safe no-op if disabled/not installed)
DATALAD_ENABLED = os.getenv("BIDS_DATALAD_ENABLED", "0") == "1"

AUDIT_SYSTEM_TO_BIDS = os.getenv("AUDIT_SYSTEM_TO_BIDS", "0") == "1"  # default OFF
SYSTEM_BUCKET_DIR = os.path.join(BIDS_ROOT, "_system")
try:
    if DATALAD_ENABLED:
        import datalad.api as dl  # type: ignore
    else:
        dl = None
except Exception:
    dl = None
    DATALAD_ENABLED = False

# Also write CSV mirrors next to TSVs (useful for Excel)
WRITE_CSV_MIRRORS = os.getenv("BIDS_WRITE_CSV_MIRRORS", "0") == "1"

# Mirror per-subject copies under derivatives/ (optional; existing behavior preserved)
MIRROR_DERIV_SUBJECT = os.getenv("BIDS_MIRROR_DERIV_SUBJECT", "0") == "1"

# Mirror eCRF entries under each subject’s own folder as well (default ON)
MIRROR_SUBJECT_FOLDER = os.getenv("BIDS_MIRROR_SUBJECT_FOLDER", "1") == "1"


# Columns we’ll drop from any legacy files we rewrite
LEGACY_DROP = {"group", "group_index", "visit_index", "data.value", "value", "session"}

# Fixed headers for eCRF/entries.tsv (data columns follow afterward)
FIXED_ENTRY_HEADERS = [
    "participant_id",
    "visit_name",
    "group_name",
    "entry_id",
    "form_version",
    "last_updated",
    "status",
]

# -------------------- FS / I/O utils --------------------

def _system_changes_path() -> str:
    _ensure_dir(SYSTEM_BUCKET_DIR)
    return os.path.join(SYSTEM_BUCKET_DIR, "changes.txt")

def _append_system_change_line(action: str, detail: Dict[str, Any]) -> None:
    """
    System-scope append-only changes file (optional, disabled by default).
    Never creates per-study folders.
    """
    path = _system_changes_path()
    payload = {
        "ts": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "action": action,
        "study_name": "",  # system scope
        **detail,
    }
    lock = FileLock(path + ".lock")
    with lock:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

def _safe_name(candidate: str) -> str:
    # keep user’s name; only strip path separators and trim whitespace
    return (candidate or "file").replace("/", "_").replace("\\", "_").strip()

def _choose_candidate_name(source_path: Optional[str], url: Optional[str], filename: Optional[str]) -> str:
    if filename and filename.strip():
        return _safe_name(filename)
    if url:
        return _safe_name(os.path.basename(urlparse(url).path) or "link")
    return _safe_name(os.path.basename(source_path or "file"))

def _ensure_dir(p: str) -> None:
    pathlib.Path(p).mkdir(parents=True, exist_ok=True)

def _alnum(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", s or "")

def _normalize_token(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^A-Za-z0-9_.-]", "", s)
    return s

def _dataset_path(study_id: int, study_name: Optional[str]) -> str:
    slug = _alnum((study_name or f"study{study_id}").replace(" ", ""))[:48]
    folder = f"study_{study_id}_{slug}" if slug else f"study_{study_id}"
    return os.path.join(BIDS_ROOT, folder)

def _safe_write_json(path: str, payload: dict) -> None:
    _ensure_dir(os.path.dirname(path))
    lock = FileLock(path + ".lock")
    with lock:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4)

def _read_tsv_rows(path: str) -> Tuple[List[str], List[Dict[str, str]]]:
    if not os.path.exists(path):
        return [], []
    with open(path, "r", encoding="utf-8") as f:
        r = csv.DictReader(f, delimiter="\t")
        headers = r.fieldnames or []
        rows = [dict(row) for row in r]
    return headers, rows

def _write_tsv_rows(path: str, headers: List[str], rows: List[Dict[str, str]]) -> None:
    _ensure_dir(os.path.dirname(path))
    lock = FileLock(path + ".lock")
    with lock:
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, delimiter="\t", fieldnames=headers, extrasaction="ignore")
            w.writeheader()
            for row in rows:
                safe = {h: ("" if h not in row or row[h] is None else row[h]) for h in headers}
                w.writerow(safe)

def _write_csv_mirror_from_tsv(tsv_path: str) -> None:
    if not WRITE_CSV_MIRRORS or not os.path.exists(tsv_path):
        return
    csv_path = os.path.splitext(tsv_path)[0] + ".csv"
    headers, rows = _read_tsv_rows(tsv_path)
    _ensure_dir(os.path.dirname(csv_path))
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for r in rows:
            w.writerow(r)

def _datalad_dataset_init(path: str):
    if not DATALAD_ENABLED or dl is None:
        return None
    ds = dl.Dataset(path)
    if not ds.is_installed():
        ds.create(cfg_proc="text2git")
    return ds

def _datalad_save(path: str, msg: str):
    if not DATALAD_ENABLED or dl is None:
        return
    ds = dl.Dataset(path)
    if ds.is_installed():
        ds.save(message=msg)

def _parse_iso(ts: str) -> Optional[datetime]:
    if not ts:
        return None
    try:
        # Expect "YYYY-MM-DDTHH:MM:SSZ"
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return datetime.fromisoformat(ts)
    except Exception:
        return None

# -------------------- Label maps --------------------

def _build_or_load_subject_map(study_data: dict) -> Dict[str, str]:
    bids = study_data.setdefault("bids", {})
    existing: Dict[str, str] = bids.get("subject_label_map") or {}
    subjects = study_data.get("subjects") or []
    keys = [str(s.get("id") or s.get("subjectId") or s.get("label") or "").strip() for s in subjects]
    keys = [k for k in keys if k]
    next_index = 1 if not existing else max(int(v) for v in existing.values()) + 1
    for k in sorted(keys):
        if k not in existing:
            existing[k] = f"{next_index:03d}"
            next_index += 1
    bids["subject_label_map"] = existing
    return existing

def _build_or_load_session_map(study_data: dict) -> Dict[str, str]:
    # Kept for completeness; not written to files directly
    bids = study_data.setdefault("bids", {})
    visits = study_data.get("visits") or []
    if len(visits) <= 1:
        bids["session_label_map"] = {}
        return {}
    existing: Dict[str, str] = bids.get("session_label_map") or {}
    raw_keys = []
    for i, v in enumerate(visits):
        key = str(v.get("name") or v.get("label") or v.get("code") or v.get("id") or i + 1)
        raw_keys.append(key)
    next_index = 1 if not existing else max(int(v) for v in existing.values()) + 1
    for k in sorted(_alnum(s) for s in raw_keys):
        if k not in existing:
            existing[k] = f"{next_index:02d}"
            next_index += 1
    bids["session_label_map"] = existing
    return existing

# -------------------- Column catalog (SectionTitle.FieldLabel) --------------------

def _build_or_load_column_catalog(study_data: dict) -> List[Dict[str, Any]]:
    """
    Stable column list like the dashboard grid: SectionTitle.FieldLabel
    Persisted at study_data['bids']['column_catalog'] as:
      [{"sIdx": 0, "fIdx": 0, "name": "Demographics.Age"}, ...]
    """
    bids = study_data.setdefault("bids", {})
    catalog: List[Dict[str, Any]] = bids.get("column_catalog") or []

    models = study_data.get("selectedModels") or []
    current: List[Dict[str, Any]] = []
    used_names = set(n.get("name") for n in catalog)

    def sec_title(m: dict) -> str:
        return _normalize_token(m.get("title") or m.get("name") or "Section")

    def fld_label(f: dict) -> str:
        nm = f.get("label") or f.get("name") or f.get("field") or f.get("id") or "field"
        return _normalize_token(nm)

    for sIdx, m in enumerate(models):
        sec = sec_title(m)
        for fIdx, f in enumerate(m.get("fields") or []):
            base = f"{sec}.{fld_label(f)}"
            name = base
            suffix = 2
            while name in used_names:
                name = f"{base}_{sIdx}_{fIdx}" if suffix == 2 else f"{base}_{sIdx}_{fIdx}_{suffix}"
                suffix += 1
            current.append({"sIdx": sIdx, "fIdx": fIdx, "name": name})
            used_names.add(name)

    have = {(int(it["sIdx"]), int(it["fIdx"])) for it in catalog}
    for it in current:
        key = (int(it["sIdx"]), int(it["fIdx"]))
        if key not in have:
            catalog.append(it)
            have.add(key)

    bids["column_catalog"] = catalog
    return catalog

# -------------------- Dataset structure --------------------

def upsert_bids_dataset(
    study_id: int,
    study_name: str,
    study_description: Optional[str],
    study_data: dict,
) -> str:
    dataset_path = _dataset_path(study_id, study_name)
    _ensure_dir(dataset_path)
    _datalad_dataset_init(dataset_path)

    metadata_dir = os.path.join(dataset_path, "metadata")
    _ensure_dir(metadata_dir)

    # Compose dataset description data (used for metadata text)
    ds_json = {
        "Name": study_name or f"Study {study_id}",
        "BIDSVersion": BIDS_VERSION,
        "DatasetType": "raw",
    }

    # Write (or create once) metadata/dataset_description.txt
    ds_txt_path = os.path.join(metadata_dir, "dataset_description.txt")
    if not os.path.exists(ds_txt_path):
        with open(ds_txt_path, "w", encoding="utf-8") as f:
            f.write(
                "Dataset Description\n"
                f"Name: {ds_json['Name']}\n"
                f"BIDSVersion: {ds_json['BIDSVersion']}\n"
                f"DatasetType: {ds_json['DatasetType']}\n"
            )

    # Write (or create once) metadata/changes.txt (instead of root CHANGES)
    changes_txt_path = os.path.join(metadata_dir, "changes.txt")
    if not os.path.exists(changes_txt_path):
        with open(changes_txt_path, "w", encoding="utf-8") as f:
            f.write(
                f"1.0.0 {datetime.utcnow().strftime('%Y-%m-%d')}\n"
                " - Initial BIDS dataset creation.\n"
            )

    # maps & columns
    _build_or_load_subject_map(study_data)
    _build_or_load_session_map(study_data)
    _build_or_load_column_catalog(study_data)

    # base directories
    _ensure_dir(os.path.join(dataset_path, "eCRF"))

    # optional: subject/session dirs
    bids = study_data.get("bids") or {}
    subj_map = bids.get("subject_label_map") or {}
    ses_map = bids.get("session_label_map") or {}
    subjects = study_data.get("subjects") or []
    visits = study_data.get("visits") or []
    have_sessions = len(ses_map) > 0

    for s in subjects:
        raw_id = str(s.get("id") or s.get("subjectId") or s.get("label") or "").strip()
        if not raw_id:
            continue
        bids_numeric = subj_map.get(raw_id) or "999"
        sub_dir = os.path.join(dataset_path, f"sub-{_alnum(bids_numeric)}")
        _ensure_dir(sub_dir)
        if have_sessions:
            for v in visits:
                vkey = _alnum(str(v.get("name") or v.get("label") or v.get("code") or v.get("id") or "1"))
                ses_label = f"ses-{ses_map.get(vkey, '01')}"
                _ensure_dir(os.path.join(sub_dir, ses_label))

    # participants.tsv constructed from eCRF/entries.tsv
    _rebuild_participants_tsv(dataset_path, study_data)
    _datalad_save(dataset_path, msg="Initialize/Update BIDS dataset structure")
    return dataset_path

# -------------------- helpers: study structure --------------------

def _get_visit_name(study_data: dict, visit_index: int) -> str:
    visits = study_data.get("visits") or []
    if 0 <= visit_index < len(visits):
        v = visits[visit_index]
        return str(v.get("name") or v.get("label") or v.get("code") or v.get("id") or f"Visit_{visit_index+1}")
    return f"Visit_{visit_index+1}"

def _resolve_bids_subject_label(study_data: dict, subject_index: int) -> str:
    subjects = study_data.get("subjects") or []
    bids = study_data.setdefault("bids", {})
    subj_map = bids.get("subject_label_map") or _build_or_load_subject_map(study_data)
    label_num = None
    if 0 <= subject_index < len(subjects):
        subj = subjects[subject_index]
        raw_id = str(subj.get("id") or subj.get("subjectId") or subj.get("label") or "").strip()
        if raw_id:
            label_num = subj_map.get(raw_id)
    if not label_num:
        raw_key = str(subject_index + 1)
        if raw_key not in subj_map:
            next_index = 1 if not subj_map else max(int(v) for v in subj_map.values()) + 1
            subj_map[raw_key] = f"{next_index:03d}"
        label_num = subj_map[raw_key]
    bids["subject_label_map"] = subj_map
    return label_num

def _resolve_group_name(study_data: dict, subject_index: int, group_index: Optional[int]) -> str:
    subjects = study_data.get("subjects") or []
    if 0 <= subject_index < len(subjects):
        grp = (subjects[subject_index].get("group") or "").strip()
        if grp:
            return grp
    groups = study_data.get("groups") or []
    if group_index is not None and 0 <= group_index < len(groups):
        return (groups[group_index].get("name") or groups[group_index].get("label") or "n/a")
    return ""

def _resolve_group_index_from_subject(study_data: dict, subject_index: int) -> Optional[int]:
    subjects = study_data.get("subjects") or []
    groups = study_data.get("groups") or []
    if not (0 <= subject_index < len(subjects)) or not groups:
        return None
    subj_group = (subjects[subject_index].get("group") or "").strip().lower()
    if not subj_group:
        return None
    for gi, g in enumerate(groups):
        name = (g.get("name") or g.get("label") or "").strip().lower()
        if name and name == subj_group:
            return gi
    return None

def _is_assigned(study_data: dict, section_idx: int, visit_idx: int, group_idx: Optional[int]) -> bool:
    assigns = study_data.get("assignments")
    if not isinstance(assigns, list):
        return True
    try:
        if group_idx is None:
            return any(assigns[section_idx][visit_idx] or [])
        return bool(assigns[section_idx][visit_idx][group_idx])
    except Exception:
        return False

def _value_from_entry(entry: dict, sIdx: int, fIdx: int):
    data = entry.get("data")
    if not isinstance(data, list):
        return None
    if not (0 <= sIdx < len(data)):
        return None
    row = data[sIdx]
    if not isinstance(row, list):
        return None
    if not (0 <= fIdx < len(row)):
        return None
    return row[fIdx]

def _is_empty_for_type(val: Any) -> bool:
    if val is True:
        return False
    if val is False:
        return True
    if val is None:
        return True
    if isinstance(val, str):
        return val.strip() == ""
    if isinstance(val, (list, tuple, set, dict)):
        return len(val) == 0
    return False  # numbers etc. count as filled

# -------------------- Status engine (mirrors UI) --------------------

def _compute_entry_status(study_data: dict, entry: Dict[str, Any]) -> str:
    """
    Status per your color scheme:
      - 'skipped'  : any skipped_required_flags on assigned fields
      - 'complete' : all assigned fields filled (no skips)
      - 'partial'  : some assigned fields filled but not all
      - 'none'     : nothing entered on assigned fields
    """
    subject_index = int(entry.get("subject_index", 0) or 0)
    visit_index   = int(entry.get("visit_index", 0) or 0)
    group_index   = _resolve_group_index_from_subject(study_data, subject_index)
    if group_index is None:
        gi_payload = entry.get("group_index")
        group_index = int(gi_payload) if (gi_payload is not None and str(gi_payload).isdigit()) else None

    selected = study_data.get("selectedModels") or []
    # gather assigned section indices
    assigned_sections = [mIdx for mIdx in range(len(selected)) if _is_assigned(study_data, mIdx, visit_index, group_index)]

    # any skip on assigned fields?
    skips = entry.get("skipped_required_flags")
    if isinstance(skips, list):
        for mIdx in assigned_sections:
            row = skips[mIdx] if mIdx < len(skips) else None
            if isinstance(row, list) and any(bool(x) for x in row):
                return "skipped"

    # total/filled across assigned fields
    total = 0
    filled = 0
    for mIdx in assigned_sections:
        fields = (selected[mIdx].get("fields") or [])
        for fIdx, _ in enumerate(fields):
            total += 1
            val = _value_from_entry(entry, mIdx, fIdx)
            if not _is_empty_for_type(val):
                filled += 1

    if total == 0 or filled == 0:
        return "none"
    if filled == total:
        return "complete"
    return "partial"

# -------------------- NEW: Unified audit helpers (DB + BIDS) --------------------

def _changes_file_path(study_id: int, study_name: Optional[str]) -> str:
    dataset_path = _dataset_path(study_id, study_name)
    metadata_dir = os.path.join(dataset_path, "metadata")
    _ensure_dir(metadata_dir)
    return os.path.join(metadata_dir, "changes.txt")

def _study_access_csv_path(study_id: int, study_name: Optional[str]) -> str:
    dataset_path = _dataset_path(study_id, study_name)
    metadata_dir = os.path.join(dataset_path, "metadata")
    _ensure_dir(metadata_dir)
    return os.path.join(metadata_dir, "Study Access.csv")

def _append_change_line(study_id: int, study_name: Optional[str], action: str, detail: Dict[str, Any]) -> None:
    path = _changes_file_path(study_id, study_name)
    payload = {
        "ts": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "action": action,
        "study_name": (study_name or ""),
        **detail,
    }
    lock = FileLock(path + ".lock")
    _ensure_dir(os.path.dirname(path))
    with lock:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

# ---- UNIFIED AUDIT ENTRYPOINT (flexible signature; DB + BIDS) ----
def audit_change_both(
    *,
    # canonical fields
    scope: Optional[str] = None,                # "study" | "system" (auto-infers if omitted)
    action: str,                                # e.g., "list_data_entries", "user_login_success", ...
    actor: Optional[str] = None,                # preformatted display string
    study_id: Optional[int] = None,
    study_name: Optional[str] = None,
    subject_index: Optional[int] = None,
    visit_index: Optional[int] = None,
    extra: Optional[Dict[str, Any]] = None,     # generic payload (legacy name)
    # compatibility kwargs expected by callers elsewhere
    db=None,
    actor_id: Optional[int] = None,
    actor_name: Optional[str] = None,
    detail: Optional[Dict[str, Any]] = None,    # generic payload (newer name)
) -> None:
    """
    Unified auditor:
      1) Always tries to write to DB provenance if `db` and `_db_record_event` are available.
      2) Writes to BIDS `metadata/changes.txt` only when we have a real study context
         (study_id > 0 and non-empty study_name). System-scope never creates study_0_*.
      3) If AUDIT_SYSTEM_TO_BIDS=1, system events also go to BIDS_ROOT/_system/changes.txt.
    """

    # ---- normalize scope -----------------------------------------------------
    # If not provided, infer: study if we have a real study_id, else system.
    if not scope:
        scope = "study" if (isinstance(study_id, int) and study_id > 0) else "system"

    # ---- build detail payload ------------------------------------------------
    # merge both naming styles; `detail` wins over `extra` for overlapping keys.
    payload: Dict[str, Any] = {}
    if isinstance(extra, dict):
        payload.update(extra)
    if isinstance(detail, dict):
        payload.update(detail)

    # add subject/visit hints if provided
    if subject_index is not None and "subject_index" not in payload:
        payload["subject_index"] = subject_index
    if visit_index is not None and "visit_index" not in payload:
        payload["visit_index"] = visit_index

    # actor precedence: explicit `actor` string > (actor_name + id) > nothing
    if not actor and actor_name:
        actor = f"{actor_name} (id={actor_id})" if actor_id is not None else actor_name
    if actor:
        payload["actor"] = actor

    # ---- 1) DB provenance (best-effort) -------------------------------------
    # If your project wires _db_record_event(db, user_id, study_id, subject_id, action, details)
    # this will capture the audit in the database.
    if _db_record_event and db is not None:
        try:
            _db_record_event(
                db=db,
                user_id=actor_id,
                study_id=(study_id if isinstance(study_id, int) else None),
                subject_id=None,
                action=action,
                details=payload,
            )
        except Exception as e:  # keep audit non-fatal
            logger.error("audit_change_both: DB provenance write failed: %s", e)

    # ---- 2) BIDS changes.txt (study scope only) ------------------------------
    write_study_bids = (
        scope == "study"
        and isinstance(study_id, int) and study_id > 0
        and isinstance(study_name, str) and study_name.strip() != ""
    )
    if write_study_bids:
        try:
            _append_change_line(
                study_id=study_id,
                study_name=study_name,
                action=action,
                detail=payload,
            )
        except Exception as e:
            logger.error("audit_change_both: failed to write study changes.txt: %s", e)
        return

    # ---- 3) Optional system bucket (never creates study_0_*) -----------------
    if scope == "system" and AUDIT_SYSTEM_TO_BIDS:
        try:
            _append_system_change_line(action=action, detail=payload)
        except Exception as e:
            logger.error("audit_change_both: failed to write system changes.txt: %s", e)


def audit_access_change_both(
    *,
    db=None,
    study_id: int,
    study_name: Optional[str],
    action: str,  # "access_granted" | "access_updated" | "access_revoked"
    actor_id: int,
    actor_name: str,
    target_user_id: int,
    target_user_email: str,
    target_user_display: str,
    permissions: Dict[str, Any],
) -> None:
    """
    Unified access audit: writes to Study Access.csv, study changes.txt, and DB.
    """
    # 1) CSV line
    path = _study_access_csv_path(study_id, study_name)
    headers = [
        "timestamp",
        "action",
        "actor_id",
        "actor_name",
        "target_user_id",
        "target_user_display",
        "target_user_email",
        "permissions_view",
        "permissions_add_data",
        "permissions_edit_study",
    ]
    _ensure_dir(os.path.dirname(path))
    lock = FileLock(path + ".lock")
    with lock:
        write_header = not os.path.exists(path)
        with open(path, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=headers)
            if write_header:
                w.writeheader()
            w.writerow({
                "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "action": action,
                "actor_id": actor_id,
                "actor_name": actor_name or "",
                "target_user_id": target_user_id,
                "target_user_display": target_user_display or "",
                "target_user_email": target_user_email or "",
                "permissions_view": bool((permissions or {}).get("view", True)),
                "permissions_add_data": bool((permissions or {}).get("add_data", True)),
                "permissions_edit_study": bool((permissions or {}).get("edit_study", False)),
            })

    # 2) changes.txt + DB via the unified helper (scope auto-infers to "study")
    audit_change_both(
        db=db,
        study_id=study_id,
        study_name=study_name,
        action=action,
        actor_id=actor_id,
        actor_name=actor_name,
        detail={
            "target_user_id": target_user_id,
            "target_user_display": target_user_display,
            "target_user_email": target_user_email,
            "permissions": {
                "view": bool((permissions or {}).get("view", True)),
                "add_data": bool((permissions or {}).get("add_data", True)),
                "edit_study": bool((permissions or {}).get("edit_study", False)),
            },
        },
    )

# -------------------- Public: write eCRF/entries.tsv --------------------

def write_entry_to_bids(
    study_id: int,
    study_name: str,
    study_description: Optional[str],
    study_data: dict,
    entry: Dict[str, Any],
    actor: Optional[str] = None,
    *,
    db=None,               # NEW optional DB session for unified audit
    actor_id: Optional[int] = None,
    actor_name: Optional[str] = None,
) -> str:
    """
    Upsert a row for a saved data entry into eCRF/entries.tsv with:
      - fixed columns: participant_id, visit_name, group_name, entry_id, form_version, last_updated, status
      - data columns: SectionTitle.FieldLabel (stable catalog)
    """
    dataset_path = _dataset_path(study_id, study_name)
    pheno_dir = os.path.join(dataset_path, "eCRF")
    _ensure_dir(pheno_dir)
    tsv_path = os.path.join(pheno_dir, "entries.tsv")

    # Ensure maps & catalog are ready
    _build_or_load_subject_map(study_data)
    _build_or_load_session_map(study_data)
    catalog = _build_or_load_column_catalog(study_data)

    # Resolve subject / visit / group
    subject_index = int(entry.get("subject_index", 0) or 0)
    visit_index   = int(entry.get("visit_index", 0) or 0)

    group_index_from_subject = _resolve_group_index_from_subject(study_data, subject_index)
    group_index   = group_index_from_subject
    if group_index is None:
        gi_payload = entry.get("group_index", None)
        group_index = int(gi_payload) if (gi_payload is not None and str(gi_payload).isdigit()) else None

    subj_num = _resolve_bids_subject_label(study_data, subject_index)
    participant_id = f"sub-{_alnum(subj_num)}"
    visit_name = _get_visit_name(study_data, visit_index)
    group_name = _resolve_group_name(study_data, subject_index, group_index)

    status = _compute_entry_status(study_data, entry)

    base_row = {
        "participant_id": participant_id,
        "visit_name": visit_name,
        "group_name": group_name or "",
        "entry_id": str(entry.get("id")),
        "form_version": str(entry.get("form_version") or "1"),
        "last_updated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": status,
    }

    # Data columns from catalog
    data_cols: Dict[str, str] = {}
    written_fields: List[str] = []  # names written this call (no values)
    for item in catalog:
        sIdx = int(item["sIdx"])
        fIdx = int(item["fIdx"])
        col  = str(item["name"])
        if _is_assigned(study_data, sIdx, visit_index, group_index):
            val = _value_from_entry(entry, sIdx, fIdx)
            if val is None:
                continue
            if isinstance(val, (list, dict)):
                data_cols[col] = json.dumps(val, ensure_ascii=False)
            elif val is True:
                data_cols[col] = "Yes"
            elif val is False:
                data_cols[col] = "No"
            else:
                data_cols[col] = str(val)
            # record field name only (no values) for changes.txt
            written_fields.append(col)

    new_row = {**base_row, **data_cols}

    # Read existing file
    headers, rows = _read_tsv_rows(tsv_path)

    # Compose headers: FIXED + catalog + (any historic extras except legacy)
    catalog_cols = [str(it["name"]) for it in catalog]
    union = (set(headers) | set(FIXED_ENTRY_HEADERS) | set(catalog_cols)) - LEGACY_DROP
    ordered_headers = FIXED_ENTRY_HEADERS + [c for c in catalog_cols if c in union] + \
        [h for h in headers if h not in FIXED_ENTRY_HEADERS and h not in catalog_cols and h in union]

    # Upsert by entry_id
    entry_id_str = str(entry.get("id"))
    updated = False

    # snapshot previous row BEFORE mutation to detect actual changes ---
    prev_row = None
    for row in rows:
        if row.get("entry_id") == entry_id_str:
            prev_row = dict(row)  # snapshot for diffing later
            # refresh fixed, then all catalog cols; drop legacy
            for k in FIXED_ENTRY_HEADERS:
                row[k] = new_row.get(k, row.get(k))
            for col in catalog_cols:
                row[col] = new_row.get(col, row.get(col))
            for legacy in LEGACY_DROP:
                row.pop(legacy, None)
            updated = True
            break

    if not updated:
        for legacy in LEGACY_DROP:
            new_row.pop(legacy, None)
        rows.append(new_row)

    # Write back
    _write_tsv_rows(tsv_path, ordered_headers, rows)
    _write_csv_mirror_from_tsv(tsv_path)

    # Update participants meta
    _rebuild_participants_tsv(dataset_path, study_data)

    # Optional subject-level mirror in derivatives/ (existing behavior preserved)
    if MIRROR_DERIV_SUBJECT:
        target_dir = os.path.join(dataset_path, "derivatives", "crf-tsv", participant_id)
        _ensure_dir(target_dir)
        sub_tsv = os.path.join(target_dir, "entries.tsv")
        s_headers, s_rows = _read_tsv_rows(sub_tsv)
        s_union = (set(s_headers) | set(ordered_headers)) - LEGACY_DROP
        s_headers = [h for h in ordered_headers if h in s_union] + [h for h in s_headers if h not in ordered_headers]
        replaced = False
        for r in s_rows:
            if r.get("entry_id") == entry_id_str:
                for k in FIXED_ENTRY_HEADERS:
                    r[k] = new_row.get(k, r.get(k))
                for col in catalog_cols:
                    r[col] = new_row.get(col, r.get(col))
                for legacy in LEGACY_DROP:
                    r.pop(legacy, None)
                replaced = True
                break
        if not replaced:
            s_rows.append(new_row)
        _write_tsv_rows(sub_tsv, s_headers, s_rows)
        _write_csv_mirror_from_tsv(sub_tsv)

    # Per-subject mirror under the subject’s own folder (default ON)
    if MIRROR_SUBJECT_FOLDER:
        # sub-XXX[/ses-YY]/eCRF/entries.tsv
        ses_folder = _session_folder(study_data, visit_index)
        base_dir = os.path.join(dataset_path, participant_id, ses_folder) if ses_folder else os.path.join(dataset_path, participant_id)
        target_dir = os.path.join(base_dir, "eCRF")
        _ensure_dir(target_dir)
        sub_tsv = os.path.join(target_dir, "entries.tsv")
        s_headers, s_rows = _read_tsv_rows(sub_tsv)
        s_union = (set(s_headers) | set(ordered_headers)) - LEGACY_DROP
        s_headers = [h for h in ordered_headers if h in s_union] + [h for h in s_headers if h not in ordered_headers]
        replaced = False
        for r in s_rows:
            if r.get("entry_id") == entry_id_str:
                for k in FIXED_ENTRY_HEADERS:
                    r[k] = new_row.get(k, r.get(k))
                for col in catalog_cols:
                    r[col] = new_row.get(col, r.get(col))
                for legacy in LEGACY_DROP:
                    r.pop(legacy, None)
                replaced = True
                break
        if not replaced:
            s_rows.append(new_row)
        _write_tsv_rows(sub_tsv, s_headers, s_rows)
        _write_csv_mirror_from_tsv(sub_tsv)

    _datalad_save(dataset_path, msg=f"Upsert eCRF entry {entry_id_str} for {participant_id} (visit={visit_name}, status={status})")

    # compute actual changed fields (vs. merely written)
    if prev_row is None:
        fields_changed = list(written_fields)  # brand new entry: everything we wrote is a change
    else:
        fields_changed = []
        for col in written_fields:  # compare only the form fields we touched in this call
            prev_val = "" if prev_row.get(col) is None else str(prev_row.get(col))
            new_val  = "" if new_row.get(col)  is None else str(new_row.get(col))
            if prev_val != new_val:
                fields_changed.append(col)

    # Unified audit (BIDS + DB)
    audit_change_both(
        db=db,
        study_id=study_id,
        study_name=study_name,
        action="entry_upsert",
        actor_id=actor_id,
        actor_name=actor_name or actor,  # keep legacy 'actor' param
        subject_index=subject_index,
        visit_index=visit_index,
        detail={
            "participant_id": participant_id,
            "visit_name": visit_name,
            "group_name": group_name or "",
            "entry_id": entry_id_str,
            "status": status,
            "fields_count": len(fields_changed),
            "fields": fields_changed,  # names only; no values
        },
    )

    logger.info(
        "BIDS eCRF written: %s (entry_id=%s, participant=%s, visit=%s, status=%s)",
        tsv_path, entry_id_str, participant_id, visit_name, status
    )
    return tsv_path

# -------------------- Participants meta --------------------

def _collect_entries_meta(entries_path: str) -> Dict[str, Dict[str, Any]]:
    """
    Aggregate per participant across eCRF/entries.tsv into:
      {
        participant_id: {
          "visits_planned": <filled later>,
          "visits_completed": n_green,
          "visits_partial": n_yellow,
          "visits_skipped": n_red,
          "last_updated": ISO,
          "_visit_names": set([...]),
        },
        ...
      }
    """
    meta: Dict[str, Dict[str, Any]] = {}
    if not os.path.exists(entries_path):
        return meta

    headers, rows = _read_tsv_rows(entries_path)

    for r in rows:
        pid = r.get("participant_id")
        if not pid:
            continue

        # init
        item = meta.setdefault(pid, {
            "_visit_names": set(),
            "visits_completed": 0,
            "visits_partial": 0,
            "visits_skipped": 0,
            "last_updated": "",  # ISO string
        })

        # last_updated: keep latest timestamp
        ru = _parse_iso(r.get("last_updated") or "")
        curr = _parse_iso(item["last_updated"]) if item["last_updated"] else None
        if ru and (curr is None or ru > curr):
            item["last_updated"] = r.get("last_updated")

        # visit names for planned/completed logic
        vname = (r.get("visit_name") or "").strip()
        if vname:
            item["_visit_names"].add(vname)

        # status counting
        status = (r.get("status") or "").strip().lower()
        if status == "complete":
            item["visits_completed"] += 1
        elif status == "partial":
            item["visits_partial"] += 1
        elif status == "skipped":
            item["visits_skipped"] += 1
        else:
            # 'none' or unknowns do not count as completed/partial/skipped
            pass

    return meta

def _rebuild_participants_tsv(dataset_path: str, study_data: dict) -> None:
    subjects = study_data.get("subjects") or []
    visits   = study_data.get("visits") or []
    subj_map = _build_or_load_subject_map(study_data)

    entries_path = os.path.join(dataset_path, "eCRF", "entries.tsv")
    per_pid_meta = _collect_entries_meta(entries_path)

    headers = ["participant_id", "visits_planned", "visits_completed", "visits_partial", "visits_skipped", "last_updated"]
    rows: List[Dict[str, str]] = []
    visits_planned = str(len(visits)) if visits else "0"
    now_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    for idx, subj in enumerate(subjects):
        raw_id = str(subj.get("id") or subj.get("subjectId") or subj.get("label") or "").strip() or str(idx+1)
        label_num = subj_map.get(raw_id)
        if not label_num:
            next_index = 1 if not subj_map else max(int(v) for v in subj_map.values()) + 1
            label_num = f"{next_index:03d}"
            subj_map[raw_id] = label_num
        participant_id = f"sub-{_alnum(label_num)}"

        m = per_pid_meta.get(participant_id, {})
        rows.append({
            "participant_id": participant_id,
            "visits_planned": visits_planned,
            "visits_completed": str(m.get("visits_completed", 0)),
            "visits_partial": str(m.get("visits_partial", 0)),
            "visits_skipped": str(m.get("visits_skipped", 0)),
            "last_updated": m.get("last_updated", now_iso),
        })

    tsv_path = os.path.join(dataset_path, "participants.tsv")
    _write_tsv_rows(tsv_path, headers, rows)
    _write_csv_mirror_from_tsv(tsv_path)
    _datalad_save(dataset_path, msg="Update participants.tsv meta")

def _session_folder(study_data: dict, visit_index: Optional[int]) -> Optional[str]:
    """
    Returns 'ses-XX' if multiple sessions/visits exist, else None.
    Uses visit_index + 1 to build a stable two-digit label.
    """
    visits = study_data.get("visits") or []
    if len(visits) <= 1 or visit_index is None:
        return None
    try:
        idx = int(visit_index)
    except Exception:
        idx = 0
    return f"ses-{idx + 1:02d}"

def _normalize_modality(mod: str) -> str:
    m = (mod or "").strip().lower()
    m = _normalize_token(m)
    return m or "misc"

def stage_file_for_modalities(
    study_id: int,
    study_name: str,
    study_description: Optional[str],
    study_data: dict,
    subject_index: Optional[int],
    visit_index: Optional[int],
    modalities: Optional[List[str]],
    source_path: Optional[str],
    url: Optional[str],
    filename: Optional[str] = None,
    actor: Optional[str] = None,
    *,
    db=None,                      # NEW optional DB session for unified audit
    actor_id: Optional[int] = None,
    actor_name: Optional[str] = None,
) -> List[str]:
    """
    Mirror a local upload or URL into the BIDS dataset.
    Also emits unified audit records (BIDS + DB).
    """
    dataset_path = upsert_bids_dataset(
        study_id=study_id,
        study_name=study_name,
        study_description=study_description,
        study_data=study_data,
    )

    written: List[str] = []

    # ---------- STUDY-LEVEL DOCS ----------
    if subject_index is None and visit_index is None:
        target_dir = os.path.join(dataset_path, "metadata")
        _ensure_dir(target_dir)
        candidate = _choose_candidate_name(source_path, url, filename)

        if source_path:
            target_path = os.path.join(target_dir, candidate)
            try:
                shutil.copy2(source_path, target_path)
                written.append(target_path)
            except Exception as e:
                logger.error("BIDS mirror (study-level) copy failed: %s -> %s (%s)", source_path, target_path, e)

        elif url:
            stem = os.path.splitext(candidate)[0]
            target_path = os.path.join(target_dir, f"{stem}.txt")
            try:
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(url.strip() + "\n")
                written.append(target_path)
            except Exception as e:
                logger.error("BIDS mirror (study-level) write-url failed: %s (%s)", target_path, e)

        if written:
            _datalad_save(dataset_path, msg="Mirror study-level document(s) into metadata/")
            audit_change_both(
                db=db,
                study_id=study_id,
                study_name=study_name,
                action="file_mirrored_study_level",
                actor_id=actor_id,
                actor_name=actor_name or actor,
                detail={
                    "targets": [os.path.relpath(p, dataset_path) for p in written],
                    "filename": filename or "",
                },
            )
        logger.info("BIDS mirror (study-level) written: %s", written)
        return written

    # ---------- PER-SUBJECT/PER-VISIT ----------
    modalities = modalities or []
    if not modalities:
        modalities = ["misc"]

    try:
        s_idx = int(subject_index) if subject_index is not None else 0
    except Exception:
        s_idx = 0

    sub_label_num = _resolve_bids_subject_label(study_data, s_idx)
    sub_dir = os.path.join(dataset_path, f"sub-{_alnum(sub_label_num)}")

    ses_folder = _session_folder(study_data, visit_index)
    base_dir = os.path.join(sub_dir, ses_folder) if ses_folder else sub_dir

    written = []

    for mod in modalities:
        mod_folder = _normalize_modality(mod)
        target_dir = os.path.join(base_dir, mod_folder)
        _ensure_dir(target_dir)

        candidate = _choose_candidate_name(source_path, url, filename)

        if source_path:
            target_path = os.path.join(target_dir, candidate)
            try:
                shutil.copy2(source_path, target_path)
                written.append(target_path)
            except Exception as e:
                logger.error("BIDS mirror copy failed: %s -> %s (%s)", source_path, target_path, e)

        elif url:
            stem = os.path.splitext(candidate)[0]
            target_path = os.path.join(target_dir, f"{stem}.txt")
            try:
                _ensure_dir(os.path.dirname(target_path))
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(url.strip() + "\n")
                written.append(target_path)
            except Exception as e:
                logger.error("BIDS mirror write-url failed: %s (%s)", target_path, e)

    if written:
        _datalad_save(dataset_path, msg=f"Mirror files/links for sub-{_alnum(sub_label_num)} (visit={visit_index})")
        audit_change_both(
            db=db,
            study_id=study_id,
            study_name=study_name,
            action="file_mirrored",
            actor_id=actor_id,
            actor_name=actor_name or actor,
            subject_index=s_idx,
            visit_index=(int(visit_index) if visit_index is not None else None),
            detail={
                "participant_id": f"sub-{_alnum(sub_label_num)}",
                "session": _session_folder(study_data, visit_index),
                "modalities": modalities,
                "targets": [os.path.relpath(p, dataset_path) for p in written],
                "filename": filename or "",
            },
        )

    logger.info("BIDS mirror written: %s", written)
    return written


def log_dataset_change_to_changes(
    study_id: int,
    study_name: Optional[str],
    action: str,
    actor_id: Optional[int] = None,
    actor_name: Optional[str] = None,
    detail: Optional[str] = None,
    *,
    db=None,
):
    audit_change_both(
        db=db,
        study_id=study_id,
        study_name=study_name,
        action=action,
        actor_id=actor_id,
        actor_name=actor_name,
        detail={"detail": detail or ""},
    )
