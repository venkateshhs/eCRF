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
from .versions import VersionManager  # <<— use versioned schemas

from .crud import record_event as _db_record_event  # (db, user_id, study_id, subject_id, action, details)

logger = logging.getLogger(__name__)

# -------------------- Config --------------------
def _runtime_base_dir() -> str:
    """
    Base path used when ECRF_DATA_DIR is not provided:
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


# If server.py set ECRF_DATA_DIR (from the config / GUI),
# we consider that the primary "data root" for everything.
_ECRF_DATA_DIR = os.getenv("ECRF_DATA_DIR")

if _ECRF_DATA_DIR:
    # Default BIDS root = <ECRF_DATA_DIR>/bids_datasets
    _DEFAULT_BIDS_ROOT = os.path.join(_ECRF_DATA_DIR, "bids_datasets")
else:
    # Backward-compatible fallback:
    # Default BIDS root = <base>/ecrf_data/bids_datasets
    _DEFAULT_BIDS_ROOT = os.path.join(_runtime_base_dir(), "ecrf_data", "bids_datasets")

# Allow override via env var if needed
BIDS_ROOT = os.getenv("BIDS_ROOT", _DEFAULT_BIDS_ROOT)


# Declared BIDS spec version
BIDS_VERSION = os.getenv("BIDS_VERSION", "1.8.0")

VERSION_DIR_PREFIX = os.getenv("BIDS_VERSION_DIR_PREFIX", "v")  # 'v' or 'V'
LATEST_POINTER_NAME = "latest"

DATALAD_ENABLED = os.getenv("BIDS_DATALAD_ENABLED", "0") == "1"
try:
    if DATALAD_ENABLED:
        import datalad.api as dl  # type: ignore
    else:
        dl = None
except Exception:
    dl = None
    DATALAD_ENABLED = False

WRITE_CSV_MIRRORS = os.getenv("BIDS_WRITE_CSV_MIRRORS", "1") == "1"
MIRROR_SUBJECT_FOLDER = os.getenv("BIDS_MIRROR_SUBJECT_FOLDER", "1") == "1"

AUDIT_SYSTEM_TO_BIDS = os.getenv("AUDIT_SYSTEM_TO_BIDS", "0") == "1"
SYSTEM_BUCKET_DIR = os.path.join(BIDS_ROOT, "_system")

LEGACY_DROP = {"group", "group_index", "visit_index", "data.value", "value", "session"}

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
    if not os.path.exists(tsv_path) or not WRITE_CSV_MIRRORS:
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

# -------- Versioned directories helpers --------

def _version_dir(dataset_path: str, version: Optional[int]) -> str:
    try:
        v = int(version) if version is not None else 1
    except Exception:
        v = 1
    v = 1 if v < 1 else v
    lower = os.path.join(dataset_path, f"v{v:03d}")
    upper = os.path.join(dataset_path, f"V{v:03d}")
    if os.path.exists(lower):
        return lower
    if os.path.exists(upper):
        return upper
    prefix = VERSION_DIR_PREFIX if VERSION_DIR_PREFIX in ("v", "V") else "v"
    return os.path.join(dataset_path, f"{prefix}{v:03d}")

def _ensure_latest_pointer(dataset_path: str, version: Optional[int]) -> None:
    try:
        target_rel = os.path.relpath(_version_dir(dataset_path, version), dataset_path)
        latest_path = os.path.join(dataset_path, LATEST_POINTER_NAME)
        if os.path.islink(latest_path):
            cur = os.readlink(latest_path)
            if cur == target_rel:
                return
            try:
                os.remove(latest_path)
            except Exception:
                return
        if os.path.exists(latest_path) and not os.path.islink(latest_path):
            return
        os.symlink(target_rel, latest_path)
    except Exception:
        return

def _copy_tree_if_missing(src: str, dst: str) -> None:
    if not os.path.exists(src):
        return
    pathlib.Path(dst).mkdir(parents=True, exist_ok=True)
    for root, dirs, files in os.walk(src):
        rel = os.path.relpath(root, src)
        out_root = os.path.join(dst, rel) if rel != "." else dst
        pathlib.Path(out_root).mkdir(parents=True, exist_ok=True)
        for d in dirs:
            pathlib.Path(os.path.join(out_root, d)).mkdir(parents=True, exist_ok=True)
        for f in files:
            sp = os.path.join(root, f)
            dp = os.path.join(out_root, f)
            if not os.path.exists(dp):
                try:
                    shutil.copy2(sp, dp)
                except Exception:
                    pass

# -------------------- One-time migration: move root → version --------------------

def _migrate_root_contents_into_version(dataset_path: str, version: int) -> None:
    """
    Move any legacy root content into version folder (idempotent).
    Only affects: 'eCRF/', 'participants.tsv/.csv', and 'sub-*' dirs.
    Leaves 'metadata/' and existing vNNN dirs untouched.
    """
    vdir = _version_dir(dataset_path, version)
    _ensure_dir(vdir)

    try:
        for name in os.listdir(dataset_path):
            src = os.path.join(dataset_path, name)
            if name in ("metadata", LATEST_POINTER_NAME):
                continue
            if name.lower().startswith("v") and len(name) == 4 and name[1:].isdigit():
                continue
            if name == os.path.basename(vdir):
                continue

            is_subject = name.startswith("sub-") and os.path.isdir(src)
            is_ecrf = (name == "eCRF") and os.path.isdir(src)
            is_participants = name in ("participants.tsv", "participants.csv")
            if not (is_subject or is_ecrf or is_participants):
                continue

            dst = os.path.join(vdir, name)
            if os.path.isdir(src):
                _copy_tree_if_missing(src, dst)
                try:
                    shutil.rmtree(src)
                except Exception:
                    pass
            else:
                if not os.path.exists(dst):
                    try:
                        shutil.move(src, dst)
                    except Exception:
                        try:
                            _ensure_dir(os.path.dirname(dst))
                            shutil.copy2(src, dst)
                            os.remove(src)
                        except Exception:
                            pass
                else:
                    try:
                        os.remove(src)
                    except Exception:
                        pass
    except FileNotFoundError:
        return
    except Exception as e:
        logger.warning("Root→version migration skipped due to error: %s", e)

# -------------------- Label maps & catalogs --------------------

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
    """
    idempotent: ensure study root + metadata exist, ensure v001 folder exists,
    migrate any legacy root contents into v001, but DO NOT rebuild participants.tsv here.
    """
    dataset_path = _dataset_path(study_id, study_name)
    _ensure_dir(dataset_path)
    _datalad_dataset_init(dataset_path)

    # Root metadata (kept at study root)
    metadata_dir = os.path.join(dataset_path, "metadata")
    _ensure_dir(metadata_dir)

    # dataset_description
    ds_txt_path = os.path.join(metadata_dir, "dataset_description.txt")
    if not os.path.exists(ds_txt_path):
        with open(ds_txt_path, "w", encoding="utf-8") as f:
            f.write(
                "Dataset Description\n"
                f"Name: {study_name or f'Study {study_id}'}\n"
                f"BIDSVersion: {BIDS_VERSION}\n"
                "DatasetType: raw\n"
            )

    # Write (or create once) metadata/changes.txt (instead of root CHANGES)
    changes_txt_path = os.path.join(metadata_dir, "changes.txt")
    if not os.path.exists(changes_txt_path):
        with open(changes_txt_path, "w", encoding="utf-8") as f:
            f.write(
                f"1.0.0 {datetime.utcnow().strftime('%Y-%m-%d')}\n"
                " - Initial BIDS dataset creation.\n"
            )

    # maps & columns for current (do not persist here, just ensure)
    _build_or_load_subject_map(dict(study_data or {}))
    _build_or_load_session_map(dict(study_data or {}))
    _build_or_load_column_catalog(dict(study_data or {}))

    # Ensure version folder exists and migrate legacy root content once
    vdir = _version_dir(dataset_path, 1)
    _ensure_dir(vdir)
    _migrate_root_contents_into_version(dataset_path, 1)
    _ensure_latest_pointer(dataset_path, 1)

    _datalad_save(dataset_path, msg="Ensure BIDS dataset structure (versioned)")
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

def _selected_models(sd: dict) -> List[Dict[str, Any]]:
    return (sd.get("selectedModels") or []) if isinstance(sd, dict) else []

def _sec_title(m: dict) -> str:
    return (m.get("title") or m.get("name") or "").strip()

def _field_keys(f: dict) -> List[str]:
    return [
        str(f.get("name") or "").strip(),
        str(f.get("label") or "").strip(),
        str(f.get("key") or "").strip(),
        str(f.get("id") or "").strip(),
    ]

def _value_from_entry_matrix_like(entry_data: Any, sIdx: int, fIdx: int):
    if not isinstance(entry_data, list):
        return None
    if not (0 <= sIdx < len(entry_data)):
        return None
    row = entry_data[sIdx]
    if not isinstance(row, list):
        return None
    if not (0 <= fIdx < len(row)):
        return None
    return row[fIdx]

def _value_from_entry_dict_like(entry_data: Any, sIdx: int, fIdx: int, study_data: dict):
    if not isinstance(entry_data, dict):
        return None
    models = _selected_models(study_data)
    if not (0 <= sIdx < len(models)):
        return None
    sec = models[sIdx]
    sec_name_candidates = [
        _sec_title(sec),
        _normalize_token(_sec_title(sec)),
    ]
    sec_dict = None
    for cand in sec_name_candidates:
        if cand in entry_data and isinstance(entry_data[cand], dict):
            sec_dict = entry_data[cand]
            break
    if sec_dict is None:
        lower_map = {str(k).strip().lower(): k for k in entry_data.keys()}
        for cand in sec_name_candidates:
            k = lower_map.get(str(cand).lower())
            if k is not None and isinstance(entry_data[k], dict):
                sec_dict = entry_data[k]
                break
    if not isinstance(sec_dict, dict):
        return None
    fields = (sec.get("fields") or [])
    if not (0 <= fIdx < len(fields)):
        return None
    f = fields[fIdx]
    keys = []
    for k in _field_keys(f):
        if k:
            keys.append(k)
            keys.append(_normalize_token(k))
    seen = set()
    key_list = []
    for k in keys:
        lk = k.lower()
        if lk not in seen:
            seen.add(lk)
            key_list.append(k)
    for k in key_list:
        if k in sec_dict:
            return sec_dict[k]
        if _normalize_token(k) in sec_dict:
            return sec_dict[_normalize_token(k)]
    lower_map = {str(k).strip().lower(): k for k in sec_dict.keys()}
    for k in key_list:
        orig = lower_map.get(k.lower())
        if orig is not None:
            return sec_dict[orig]
    return None

def _value_from_entry(entry: dict, sIdx: int, fIdx: int, study_data: dict):
    data = entry.get("data")
    v = _value_from_entry_matrix_like(data, sIdx, fIdx)
    if v is not None:
        return v
    return _value_from_entry_dict_like(data, sIdx, fIdx, study_data)

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

    selected = _selected_models(study_data)
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
            val = _value_from_entry(entry, mIdx, fIdx, study_data)
            if not _is_empty_for_type(val):
                filled += 1

    if total == 0 or filled == 0:
        return "none"
    if filled == total:
        return "complete"
    return "partial"

# -------------------- Unified audit helpers --------------------

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
        "study_id": study_id,
        **detail,
    }
    lock = FileLock(path + ".lock")
    _ensure_dir(os.path.dirname(path))
    with lock:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

def audit_change_both(
    *,
    scope: Optional[str] = None,
    action: str,
    actor: Optional[str] = None,
    study_id: Optional[int] = None,
    study_name: Optional[str] = None,
    subject_index: Optional[int] = None,
    visit_index: Optional[int] = None,
    extra: Optional[Dict[str, Any]] = None,
    db=None,
    actor_id: Optional[int] = None,
    actor_name: Optional[str] = None,
    detail: Optional[Dict[str, Any]] = None,
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

# -------------------- Participants meta (per version) --------------------

def _collect_entries_meta(entries_path: str) -> Dict[str, Dict[str, Any]]:
    meta: Dict[str, Dict[str, Any]] = {}
    if not os.path.exists(entries_path):
        return meta

    headers, rows = _read_tsv_rows(entries_path)

    if "status" not in headers:
        for r in rows:
            r.setdefault("status", "none")

    precedence = {"skipped": 3, "complete": 2, "partial": 1, "none": 0}

    for r in rows:
        pid = r.get("participant_id")
        if not pid:
            continue

        item = meta.setdefault(pid, {
            "_visit_status": {},
            "last_updated": "",
        })

        ru = _parse_iso(r.get("last_updated") or "")
        curr = _parse_iso(item["last_updated"]) if item["last_updated"] else None
        if ru and (curr is None or ru > curr):
            item["last_updated"] = r.get("last_updated")

        vname = (r.get("visit_name") or "").strip()
        if not vname:
            continue
        status = (r.get("status") or "none").strip().lower()
        prev = item["_visit_status"].get(vname, "none")

        if precedence.get(status, 0) >= precedence.get(prev, 0):
            item["_visit_status"][vname] = status

    for _, item in meta.items():
        vc = vp = vs = 0
        for st in item["_visit_status"].values():
            if st == "skipped":
                vs += 1
            elif st == "complete":
                vc += 1
            elif st == "partial":
                vp += 1
        item["visits_completed"] = vc
        item["visits_partial"] = vp
        item["visits_skipped"] = vs

    return meta

def _rebuild_participants_tsv_for_schema(dataset_path: str, study_schema_for_version: dict, version: int) -> None:
    ver_dir = _version_dir(dataset_path, version)

    subjects = study_schema_for_version.get("subjects") or []
    visits   = study_schema_for_version.get("visits") or []
    subj_map = _build_or_load_subject_map(study_schema_for_version)

    entries_path = os.path.join(ver_dir, "eCRF", "entries.tsv")
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

    v_out = os.path.join(ver_dir, "participants.tsv")
    _write_tsv_rows(v_out, headers, rows)
    _write_csv_mirror_from_tsv(v_out)
    _datalad_save(dataset_path, msg=f"Update participants.tsv meta (v={version:03d})")

# -------------------- Version bump helper (FS only) --------------------

def bump_bids_version(study_id: int, study_name: str, from_version: int, to_version: int) -> str:
    dataset_path = _dataset_path(study_id, study_name)
    src = _version_dir(dataset_path, from_version)
    dst = _version_dir(dataset_path, to_version)
    _copy_tree_if_missing(src, dst)
    _ensure_latest_pointer(dataset_path, to_version)
    _datalad_save(dataset_path, msg=f"Bump BIDS version v{from_version:03d} → v{to_version:03d}")
    return dst

# -------------------- Public: write eCRF/entries.tsv (version-aware) --------------------

def write_entry_to_bids(
    study_id: int,
    study_name: str,
    study_description: Optional[str],
    study_data: dict,
    entry: Dict[str, Any],
    actor: Optional[str] = None,
    *,
    db=None,
    actor_id: Optional[int] = None,
    actor_name: Optional[str] = None,
) -> str:
    """
    Upsert entry ONLY inside v<form_version>.
    Uses the *schema of that version* for labels/columns/assignments.
    """
    dataset_path = _dataset_path(study_id, study_name)

    # Decide target version
    form_version = int(entry.get("form_version") or 1)
    ver_dir = _version_dir(dataset_path, form_version)
    _ensure_dir(ver_dir)
    _ensure_latest_pointer(dataset_path, form_version)
    _migrate_root_contents_into_version(dataset_path, form_version if form_version else 1)

    # Pull versioned schema (fallback to provided)
    schema_for_version = None
    if db is not None:
        try:
            schema_for_version = VersionManager.get_version_schema(db, study_id, form_version)
        except Exception:
            schema_for_version = None
    sd = schema_for_version or _json_clone(study_data if isinstance(study_data, dict) else {})

    pheno_dir = os.path.join(ver_dir, "eCRF")
    _ensure_dir(pheno_dir)
    tsv_path = os.path.join(pheno_dir, "entries.tsv")

    # Ensure maps & catalog from the versioned schema
    _build_or_load_subject_map(sd)
    _build_or_load_session_map(sd)
    catalog = _build_or_load_column_catalog(sd)

    # Resolve subject / visit / group against versioned schema
    subject_index = int(entry.get("subject_index", 0) or 0)
    visit_index   = int(entry.get("visit_index", 0) or 0)

    group_index_from_subject = _resolve_group_index_from_subject(sd, subject_index)
    group_index   = group_index_from_subject
    if group_index is None:
        gi_payload = entry.get("group_index", None)
        group_index = int(gi_payload) if (gi_payload is not None and str(gi_payload).isdigit()) else None

    subj_num = _resolve_bids_subject_label(sd, subject_index)
    participant_id = f"sub-{_alnum(subj_num)}"
    visit_name = _get_visit_name(sd, visit_index)
    group_name = _resolve_group_name(sd, subject_index, group_index)

    status = _compute_entry_status(sd, entry)

    base_row = {
        "participant_id": participant_id,
        "visit_name": visit_name,
        "group_name": group_name or "",
        "entry_id": str(entry.get("id")),
        "form_version": str(form_version),
        "last_updated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": status,
    }

    # Data columns
    data_cols: Dict[str, str] = {}
    written_fields: List[str] = []
    for item in catalog:
        sIdx = int(item["sIdx"])
        fIdx = int(item["fIdx"])
        col  = str(item["name"])
        if _is_assigned(sd, sIdx, visit_index, group_index):
            val = _value_from_entry(entry, sIdx, fIdx, sd)
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

    # Read/Upsert
    headers, rows = _read_tsv_rows(tsv_path)
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

    # Rebuild participants.tsv for THIS VERSION ONLY
    _rebuild_participants_tsv_for_schema(dataset_path, sd, version=form_version)

    # Per-subject mirror under version dir
    if MIRROR_SUBJECT_FOLDER:
        ses_folder = _session_folder(sd, visit_index)
        base_dir = os.path.join(ver_dir, participant_id, ses_folder) if ses_folder else os.path.join(ver_dir, participant_id)
        target_dir = os.path.join(base_dir, "eCRF")
        _ensure_dir(target_dir)
        sub_tsv = os.path.join(target_dir, "entries.tsv")

        assigned_cols = [
            str(it["name"])
            for it in catalog
            if _is_assigned(sd, int(it["sIdx"]), visit_index, group_index)
        ]
        s_headers = FIXED_ENTRY_HEADERS + assigned_cols

        s_headers_old, s_rows = _read_tsv_rows(sub_tsv)
        s_union = (set(s_headers_old) | set(s_headers)) - LEGACY_DROP
        s_headers = [h for h in s_headers if h in s_union] + [h for h in s_headers_old if h not in s_headers and h in s_union]

        replaced = False
        for r in s_rows:
            if r.get("entry_id") == entry_id_str:
                for k in FIXED_ENTRY_HEADERS:
                    r[k] = new_row.get(k, r.get(k))
                for col in assigned_cols:
                    r[col] = new_row.get(col, r.get(col))
                keys_to_keep = set(s_headers)
                for k in list(r.keys()):
                    if k not in keys_to_keep:
                        r.pop(k, None)
                replaced = True
                break
        if not replaced:
            filtered_new = {k: v for k, v in new_row.items() if k in s_headers}
            s_rows.append(filtered_new)
        _write_tsv_rows(sub_tsv, s_headers, s_rows)
        _write_csv_mirror_from_tsv(sub_tsv)

    _datalad_save(dataset_path, msg=f"Upsert eCRF entry {entry_id_str} for {participant_id} (visit={visit_name}, status={status}, v={form_version:03d})")

    # diff of touched fields
    if prev_row is None:
        fields_changed = list(written_fields)
    else:
        fields_changed = []
        for col in written_fields:
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
        "BIDS eCRF written: %s (entry_id=%s, participant=%s, visit=%s, status=%s, version=%s)",
        tsv_path, entry_id_str, participant_id, visit_name, status, form_version
    )
    return tsv_path

def bulk_write_entries_to_bids(
    *,
    study_id: int,
    study_name: str,
    study_description: Optional[str],
    study_data: dict,
    entries: List[Dict[str, Any]],           # each: {id, subject_index, visit_index, group_index, form_version, data, skipped_required_flags}
    form_version: int,
    db=None,
    actor: Optional[str] = "Bulk import",
    actor_id: Optional[int] = None,
    actor_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    High-throughput BIDS writer for bulk imports:
      - Ensures dataset + v<form_version> exist once
      - Loads vNNN/eCRF/entries.tsv once, upserts all entries in-memory, writes once
      - Writes per-subject mirrors once per subject (optional, MIRROR_SUBJECT_FOLDER)
      - Rebuilds participants.tsv once
      - Emits a single audit summary
    Returns: {"written": N, "subjects_touched": M}
    """
    dataset_path = _dataset_path(study_id, study_name)
    ver_dir = _version_dir(dataset_path, form_version)
    _ensure_dir(ver_dir)
    _ensure_latest_pointer(dataset_path, form_version)
    _migrate_root_contents_into_version(dataset_path, form_version if form_version else 1)

    # Get versioned schema (fallback to provided)
    schema_for_version = None
    if db is not None and hasattr(VersionManager, "get_version_schema"):
        try:
            schema_for_version = VersionManager.get_version_schema(db, study_id, form_version)
        except Exception:
            schema_for_version = None
    sd = schema_for_version or _json_clone(study_data if isinstance(study_data, dict) else {})

    # Ensure maps & catalog ONCE for this versioned schema
    _build_or_load_subject_map(sd)
    _build_or_load_session_map(sd)
    catalog = _build_or_load_column_catalog(sd)
    catalog_cols = [str(it["name"]) for it in catalog]

    # ---------- Load dataset-level eCRF/entries.tsv once ----------
    pheno_dir = os.path.join(ver_dir, "eCRF")
    _ensure_dir(pheno_dir)
    entries_tsv = os.path.join(pheno_dir, "entries.tsv")
    headers, rows = _read_tsv_rows(entries_tsv)
    # Build quick index by entry_id
    rows_by_id: Dict[str, Dict[str, str]] = {}
    for r in rows:
        key = str(r.get("entry_id", "")).strip()
        if key:
            rows_by_id[key] = r

    # Determine headers union for dataset-level file
    union_cols = (set(headers) | set(FIXED_ENTRY_HEADERS) | set(catalog_cols)) - LEGACY_DROP
    ordered_headers = (
        FIXED_ENTRY_HEADERS +
        [c for c in catalog_cols if c in union_cols] +
        [h for h in headers if h not in FIXED_ENTRY_HEADERS and h not in catalog_cols and h in union_cols]
    )

    # ---------- Per-subject mirror accumulation (lazy read & single write) ----------
    subject_files: Dict[str, Dict[str, Any]] = {}  # path -> {"headers": List[str], "rows_by_id": Dict[str, Dict[str,str]]}

    def _get_subject_store(participant_id: str, visit_index: Optional[int]) -> Tuple[str, Dict[str, Any]]:
        ses_folder = _session_folder(sd, visit_index)
        base_dir = os.path.join(ver_dir, participant_id, ses_folder) if ses_folder else os.path.join(ver_dir, participant_id)
        target_dir = os.path.join(base_dir, "eCRF")
        _ensure_dir(target_dir)
        sub_tsv = os.path.join(target_dir, "entries.tsv")
        if sub_tsv not in subject_files:
            h, r = _read_tsv_rows(sub_tsv)
            subject_files[sub_tsv] = {
                "headers": h[:],
                "rows_by_id": {str(x.get("entry_id","")).strip(): x for x in r if str(x.get("entry_id","")).strip()},
            }
        return sub_tsv, subject_files[sub_tsv]

    # ---------- Process all entries in memory ----------
    subjects_touched = set()
    now_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    for e in entries:
        try:
            entry_id_str   = str(e.get("id"))
            subject_index  = int(e.get("subject_index", 0) or 0)
            visit_index    = int(e.get("visit_index", 0) or 0)

            group_index_from_subject = _resolve_group_index_from_subject(sd, subject_index)
            group_index = group_index_from_subject
            if group_index is None:
                gi_payload = e.get("group_index", None)
                group_index = int(gi_payload) if (gi_payload is not None and str(gi_payload).isdigit()) else None

            subj_num       = _resolve_bids_subject_label(sd, subject_index)
            participant_id = f"sub-{_alnum(subj_num)}"
            visit_name     = _get_visit_name(sd, visit_index)
            group_name     = _resolve_group_name(sd, subject_index, group_index)

            status = _compute_entry_status(sd, {
                "subject_index": subject_index,
                "visit_index": visit_index,
                "group_index": group_index,
                "data": e.get("data"),
                "skipped_required_flags": e.get("skipped_required_flags"),
            })

            base_row = {
                "participant_id": participant_id,
                "visit_name": visit_name,
                "group_name": group_name or "",
                "entry_id": entry_id_str,
                "form_version": str(form_version),
                "last_updated": now_iso,
                "status": status,
            }

            # Data columns (respect assignments)
            data_cols: Dict[str, str] = {}
            assigned_cols_for_subject_row: List[str] = []
            for item in catalog:
                sIdx = int(item["sIdx"])
                fIdx = int(item["fIdx"])
                col  = str(item["name"])
                if _is_assigned(sd, sIdx, visit_index, group_index):
                    val = _value_from_entry({"data": e.get("data")}, sIdx, fIdx, sd)
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
                    assigned_cols_for_subject_row.append(col)

            new_row = {**base_row, **data_cols}

            # ---- upsert into dataset-level entries.tsv map ----
            if entry_id_str in rows_by_id:
                row = rows_by_id[entry_id_str]
                for k in FIXED_ENTRY_HEADERS:
                    row[k] = new_row.get(k, row.get(k))
                for col in catalog_cols:
                    if col in new_row:
                        row[col] = new_row[col]
                for legacy in LEGACY_DROP:
                    row.pop(legacy, None)
            else:
                for legacy in LEGACY_DROP:
                    new_row.pop(legacy, None)
                rows_by_id[entry_id_str] = new_row

            # ---- per-subject mirror (optional) ----
            if MIRROR_SUBJECT_FOLDER:
                sub_path, store = _get_subject_store(participant_id, visit_index)
                s_headers_old = store["headers"]
                s_rows_map = store["rows_by_id"]

                # Subject headers = FIXED + union(assigned cols across writes), preserve old extras
                s_headers_desired = FIXED_ENTRY_HEADERS + assigned_cols_for_subject_row
                s_union = (set(s_headers_old) | set(s_headers_desired)) - LEGACY_DROP
                # Keep FIXED order, then keep old order for the rest
                s_headers_new = (
                    [h for h in FIXED_ENTRY_HEADERS if h in s_union] +
                    [h for h in s_headers_old if h not in FIXED_ENTRY_HEADERS and h in s_union] +
                    [h for h in s_headers_desired if h not in s_headers_old and h in s_union]
                )
                store["headers"] = s_headers_new

                if entry_id_str in s_rows_map:
                    r = s_rows_map[entry_id_str]
                    for k in FIXED_ENTRY_HEADERS:
                        r[k] = new_row.get(k, r.get(k))
                    for col in assigned_cols_for_subject_row:
                        r[col] = new_row.get(col, r.get(col))
                    # drop anything not in headers
                    for k in list(r.keys()):
                        if k not in s_headers_new:
                            r.pop(k, None)
                else:
                    filtered = {k: v for k, v in new_row.items() if k in s_headers_new}
                    s_rows_map[entry_id_str] = filtered

            subjects_touched.add(participant_id)
        except Exception as ex:
            # Keep bulk robust: continue other rows; single-row issues won’t abort all
            logger.warning("bulk_write_entries_to_bids: skip one row due to %s", ex)
            continue

    # ---------- Write dataset-level entries.tsv once ----------
    out_rows = list(rows_by_id.values())
    _write_tsv_rows(entries_tsv, ordered_headers, out_rows)
    _write_csv_mirror_from_tsv(entries_tsv)

    # ---------- Write per-subject files once ----------
    if MIRROR_SUBJECT_FOLDER:
        for sub_tsv, store in subject_files.items():
            s_rows = list(store["rows_by_id"].values())
            _write_tsv_rows(sub_tsv, store["headers"], s_rows)
            _write_csv_mirror_from_tsv(sub_tsv)

    # ---------- Rebuild participants.tsv ONCE for this version ----------
    _rebuild_participants_tsv_for_schema(dataset_path, sd, version=form_version)

    # One save & one audit summary
    _datalad_save(dataset_path, msg=f"Bulk upsert {len(entries)} entries (v={form_version:03d})")
    try:
        audit_change_both(
            db=db,
            study_id=study_id,
            study_name=study_name,
            action="bulk_entry_upsert",
            actor_id=actor_id,
            actor_name=actor_name or actor,
            detail={
                "count": len(entries),
                "version": form_version,
                "subjects_touched": sorted(subjects_touched),
            },
        )
    except Exception:
        pass

    return {"written": len(entries), "subjects_touched": len(subjects_touched)}


# -------------------- File staging (version-aware) --------------------

def _session_folder(study_data: dict, visit_index: Optional[int]) -> Optional[str]:
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
    db=None,
    actor_id: Optional[int] = None,
    actor_name: Optional[str] = None,
    form_version: Optional[int] = None,
) -> List[str]:
    """
    Version-aware file staging:
      - study-level docs → /metadata
      - subject/visit files → /vNNN/sub-XXX[/ses-YY]/<mod>/
        (vNNN = form_version if provided else latest writable)
    """
    dataset_path = upsert_bids_dataset(
        study_id=study_id,
        study_name=study_name,
        study_description=study_description,
        study_data=study_data,
    )

    written: List[str] = []

    # Study-level: keep at root/metadata
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
                detail={"targets": [os.path.relpath(p, dataset_path) for p in written],
                        "filename": filename or ""},
            )
        logger.info("BIDS mirror (study-level) written: %s", written)
        return written

    # Subject/visit: decide version
    if form_version is not None:
        target_version = int(form_version)
    elif db is not None:
        try:
            target_version = VersionManager.latest_writable_version(db, study_id)
        except Exception:
            target_version = 1
    else:
        target_version = 1

    schema_for_version = None
    if db is not None:
        try:
            schema_for_version = VersionManager.get_version_schema(db, study_id, target_version)
        except Exception:
            schema_for_version = None
    sd = schema_for_version or _json_clone(study_data if isinstance(study_data, dict) else {})

    modalities = modalities or ["misc"]
    try:
        s_idx = int(subject_index) if subject_index is not None else 0
    except Exception:
        s_idx = 0

    sub_label_num = _resolve_bids_subject_label(sd, s_idx)

    ver_dir = _version_dir(dataset_path, target_version)
    _ensure_dir(ver_dir)
    _ensure_latest_pointer(dataset_path, target_version)
    _migrate_root_contents_into_version(dataset_path, target_version)

    ses_folder = _session_folder(sd, visit_index)
    base_dir = os.path.join(ver_dir, f"sub-{_alnum(sub_label_num)}", ses_folder) if ses_folder else \
               os.path.join(ver_dir, f"sub-{_alnum(sub_label_num)}")

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
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(url.strip() + "\n")
                written.append(target_path)
            except Exception as e:
                logger.error("BIDS mirror write-url failed: %s (%s)", target_path, e)

    if written:
        _datalad_save(dataset_path, msg=f"Mirror files/links for sub-{_alnum(sub_label_num)} (visit={visit_index}, v={target_version:03d})")
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
                "session": _session_folder(sd, visit_index),
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

# small local helper to clone JSON (used above)
def _json_clone(obj: Any) -> Any:
    try:
        return json.loads(json.dumps(obj, ensure_ascii=False))
    except Exception:
        return {}
