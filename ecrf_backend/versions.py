# ecrf_backend/versions.py

# --- How structural-change detection works (versions.py) ---
#
# We only bump the template version when the *structure* of a study changes.
# To decide this, we compare a minimal, normalized snapshot of the old and
# new study_data. Non-structural edits (e.g., study title/description text)
# do not trigger a bump.
#
# 1) Build "structural snapshots"
#    We convert both old_sd and new_sd into a compact dict via _snapshot_structural():
#      {
#        "groups": [ "<group-name>", ... ],
#        "visits": [ "<visit-name>", ... ],
#        "models": [ "<selected-model-title>", ... ],
#        "subjects": [ ("<subject-id>", "<group-name>"), ... ]  # sorted
#        "assignments": [[[bool,...],...], ...]  # M × V × G matrix
#      }
#
#    Normalization details:
#      - groups/visits: accept lists of dicts or strings; extract `name`/`title`,
#        trim whitespace, and keep names in order.
#      - selected models: accept dicts or strings; use `title` (or `name`) trimmed.
#      - subjects: accept modern [{id, group}], legacy [["ID","Group"]], or list of strings;
#        we normalize to dicts, then to a sorted list of (id, group) tuples for stable compare.
#      - assignments: included as-is (the 3D boolean matrix).
#
# 2) Equality check
#    We compare the two snapshots with JSON string equality using sorted keys:
#      structural_change = not _schemas_equal(snapshot_old, snapshot_new)
#    If they differ → structural_change = True; otherwise False.
#
# 3) What counts as “structural”
#    - Adding/removing/renaming groups or visits (by name)
#    - Changing the selected models set (by model titles)
#    - Adding/removing subjects (by subject id, and their mapped group)
#    - Any change to the assignments matrix shape or values (M × V × G)
#
# 4) What does NOT count
#    - Study metadata like title/description/owner/timestamps
#    - Descriptions on groups/visits
#    - Field label/placeholder text inside models (unless the model set itself changes)
#
# 5) Where it’s used
#    - VersionManager.preview_decision(): computes structural_change and decides whether
#      to bump the version (only if the current latest version already has data).
#    - VersionManager.apply_on_update(): applies that decision after the study is saved,
#      creating a new StudyTemplateVersion on bump and cloning existing data forward.

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_
from . import models
from .logger import logger


class VersionDecision(dict):
    """Small convenience type for returning decision details."""

def _json_clone(obj: Any) -> Any:
    import json
    try:
        return json.loads(json.dumps(obj, ensure_ascii=False))
    except Exception:
        return {}

def _norm_str(s: Any) -> str:
    return ("" if s is None else str(s)).strip()

def _names_from_objs(arr: Any, key: str = "name") -> List[str]:
    out: List[str] = []
    if isinstance(arr, list):
        for it in arr:
            if isinstance(it, dict):
                name = it.get(key) or it.get("title")
                out.append(_norm_str(name))
            elif isinstance(it, str):
                out.append(_norm_str(it))
            else:
                out.append(_norm_str(it))
    return out

def _subjects_as_objs(sd: Dict[str, Any]) -> List[Dict[str, Any]]:
    subs = sd.get("subjects") or []
    if isinstance(subs, list):
        # Support legacy [["SUBJ","Group"], ...]
        if subs and isinstance(subs[0], list):
            return [{"id": _norm_str(a[0] if len(a) > 0 else ""), "group": _norm_str(a[1] if len(a) > 1 else "")} for a in subs]
        # Support list of strings (rare)
        if subs and isinstance(subs[0], str):
            return [{"id": _norm_str(x), "group": ""} for x in subs]
        # Already dicts
        return [{**x, "id": _norm_str((x or {}).get("id")), "group": _norm_str((x or {}).get("group"))} for x in subs]
    return []

def _selected_models_titles(sd: Dict[str, Any]) -> List[str]:
    models = sd.get("selectedModels") or sd.get("models") or []
    out: List[str] = []
    if isinstance(models, list):
        for m in models:
            if isinstance(m, dict):
                out.append(_norm_str(m.get("title") or m.get("name")))
            else:
                out.append(_norm_str(m))
    return out

def _snapshot_structural(sd: Dict[str, Any]) -> Dict[str, Any]:
    """Minimal structure used for equality checks & versioning decisions."""
    return {
        "groups": _names_from_objs(sd.get("groups") or []),
        "visits": _names_from_objs(sd.get("visits") or []),
        "models": _selected_models_titles(sd),
        "subjects": sorted([(x.get("id",""), x.get("group","")) for x in _subjects_as_objs(sd)]),
        "assignments": sd.get("assignments") or [],
    }

def _schemas_equal(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    import json
    return json.dumps(a or {}, sort_keys=True) == json.dumps(b or {}, sort_keys=True)

def _coerce_rich_snapshot(sd: Dict[str, Any]) -> Dict[str, Any]:
    """
    Snapshot that preserves rich metadata for UI diffs:
    study, groups (with descriptions), visits (with descriptions),
    subjects {id, group}, selectedModels {title, fields}, assignments …
    """
    snap = _json_clone(sd if isinstance(sd, dict) else {})
    # Ensure `study` object exists
    if "study" not in snap or not isinstance(snap.get("study"), dict):
        title = _norm_str(snap.get("title"))
        description = _norm_str(snap.get("description"))
        snap["study"] = {"id": _norm_str(snap.get("id")), "title": title, "description": description}

    # Normalize groups/visits to array of dicts with `name`
    def _to_objs(key: str):
        arr = snap.get(key) or []
        out = []
        for it in arr if isinstance(arr, list) else []:
            if isinstance(it, dict):
                name = it.get("name") or it.get("title")
                out.append({"name": _norm_str(name), **{k: v for k, v in it.items() if k not in ("name",)}})
            else:
                out.append({"name": _norm_str(it)})
        snap[key] = out
    _to_objs("groups")
    _to_objs("visits")

    # Normalize selectedModels
    models = snap.get("selectedModels") or snap.get("models") or []
    norm_models = []
    for m in models if isinstance(models, list) else []:
        if isinstance(m, dict):
            title = m.get("title") or m.get("name")
            norm_models.append({"title": _norm_str(title), **{k: v for k, v in m.items() if k not in ("title",)}})
        else:
            norm_models.append({"title": _norm_str(m), "fields": []})
    snap["selectedModels"] = norm_models

    # Normalize subjects → [{id, group}]
    snap["subjects"] = _subjects_as_objs(snap)
    return snap

def _index_map_by_name(old_names: List[str], new_names: List[str]) -> Dict[int, int]:
    """Map old index → new index by exact (case-insensitive) name match."""
    new_lookup = {n.lower(): i for i, n in enumerate(new_names)}
    out: Dict[int, int] = {}
    for i, n in enumerate(old_names):
        j = new_lookup.get(n.lower())
        if j is not None:
            out[i] = j
    return out

def _index_map_subjects_by_id(old_sd: Dict[str, Any], new_sd: Dict[str, Any]) -> Dict[int, int]:
    old_subs = _subjects_as_objs(old_sd)
    new_subs = _subjects_as_objs(new_sd)
    new_by_id = {s.get("id",""): idx for idx, s in enumerate(new_subs)}
    out: Dict[int, int] = {}
    for i, s in enumerate(old_subs):
        sid = s.get("id","")
        if sid in new_by_id:
            out[i] = new_by_id[sid]
    return out

def _safe_idx(idx: int, limit: int) -> Optional[int]:
    return idx if 0 <= idx < limit else None

class VersionManager:
    """Encapsulates all versioning decisions & data cloning."""

    # ----- Queries -----

    @staticmethod
    def latest(db: Session, study_id: int) -> Optional[models.StudyTemplateVersion]:
        return (
            db.query(models.StudyTemplateVersion)
              .filter(models.StudyTemplateVersion.study_id == study_id)
              .order_by(models.StudyTemplateVersion.version.desc())
              .first()
        )

    @staticmethod
    def version_has_data(db: Session, study_id: int, version: int) -> bool:
        return db.query(models.StudyEntryData)\
                 .filter(and_(models.StudyEntryData.study_id == study_id,
                              models.StudyEntryData.form_version == version))\
                 .limit(1).count() > 0

    # ----- Decisions -----

    @staticmethod
    def ensure_initial_version(db: Session, study_id: int, study_data: Dict[str, Any]) -> int:
        v = VersionManager.latest(db, study_id)
        if v:
            return v.version
        snap_rich = _coerce_rich_snapshot(study_data or {})
        v = models.StudyTemplateVersion(study_id=study_id, version=1, schema=snap_rich)
        db.add(v)
        db.commit()
        db.refresh(v)
        logger.info("Initialized template version v1 for study_id=%s", study_id)
        return v.version

    @staticmethod
    def preview_decision(db: Session, study_id: int, old_sd: Dict[str, Any], new_sd: Dict[str, Any]) -> VersionDecision:
        latest = VersionManager.latest(db, study_id)
        latest_version = latest.version if latest else 0
        has_data = VersionManager.version_has_data(db, study_id, latest_version) if latest else False
        structural_change = not _schemas_equal(_snapshot_structural(old_sd or {}), _snapshot_structural(new_sd or {}))
        if not structural_change:
            return VersionDecision(
                structural_change=False,
                latest_version=latest_version,
                latest_version_has_data=has_data,
                will_bump=False,
                decision_version_after=latest_version or 1,
            )
        will_bump = bool(latest and has_data)
        decision_after = (latest_version + 1) if will_bump else (latest_version or 1)
        return VersionDecision(
            structural_change=True,
            latest_version=latest_version,
            latest_version_has_data=has_data,
            will_bump=will_bump,
            decision_version_after=decision_after,
        )

    # ----- Apply (possibly with cloning) -----

    @staticmethod
    def apply_on_update(
        db: Session,
        study_id: int,
        old_sd: Dict[str, Any],
        new_sd: Dict[str, Any],
        audit_callback=None,  # (action:str, extra:dict) -> None
    ) -> VersionDecision:
        """
        Called AFTER StudyContent has been updated. Creates/overwrites
        StudyTemplateVersion and clones data forward if needed.
        """
        decision = VersionManager.preview_decision(db, study_id, old_sd, new_sd)

        # No structural change → nothing else to do (still audit metadata edits upstream)
        if not decision["structural_change"]:
            return decision

        latest = VersionManager.latest(db, study_id)
        latest_version = latest.version if latest else 0
        rich_snap = _coerce_rich_snapshot(new_sd or {})

        if decision["will_bump"]:
            # Create new version
            new_v = models.StudyTemplateVersion(
                study_id=study_id,
                version=latest_version + 1,
                schema=rich_snap,
            )
            db.add(new_v)
            db.commit()
            db.refresh(new_v)

            # Clone data rows from latest_version → new_v.version
            VersionManager._clone_entries_forward(db, study_id, latest_version, new_v.version, old_sd, new_sd)

            if audit_callback:
                audit_callback("template_version_bumped", {"from_version": latest_version, "to_version": new_v.version})
            logger.info("Bumped study_id=%s template from v%s to v%s", study_id, latest_version, new_v.version)
            decision["decision_version_after"] = new_v.version
            return decision

        # Overwrite latest in-place (no data yet)
        if latest:
            latest.schema = rich_snap
            db.commit()
            db.refresh(latest)
            if audit_callback:
                audit_callback("template_overwritten_before_data", {"version": latest.version})
            logger.info("Overwrote template v%s in place (no data yet) for study_id=%s", latest.version, study_id)
            decision["decision_version_after"] = latest.version
            return decision

        # No latest → initialize v1
        v1 = models.StudyTemplateVersion(study_id=study_id, version=1, schema=rich_snap)
        db.add(v1)
        db.commit()
        db.refresh(v1)
        if audit_callback:
            audit_callback("template_initialized", {"version": v1.version})
        logger.info("Initialized template v1 on update for study_id=%s", study_id)
        decision["decision_version_after"] = v1.version
        return decision

    @staticmethod
    def _clone_entries_forward(
        db: Session,
        study_id: int,
        from_version: int,
        to_version: int,
        old_sd: Dict[str, Any],
        new_sd: Dict[str, Any],
    ) -> None:
        """
        Copy ALL StudyEntryData rows from from_version → to_version with
        best-effort index mapping: subjects by ID, visits/groups by name.
        """
        # Build mapping tables
        old_groups = _names_from_objs(old_sd.get("groups") or [])
        new_groups = _names_from_objs(new_sd.get("groups") or [])
        map_g = _index_map_by_name(old_groups, new_groups)

        old_visits = _names_from_objs(old_sd.get("visits") or [])
        new_visits = _names_from_objs(new_sd.get("visits") or [])
        map_v = _index_map_by_name(old_visits, new_visits)

        map_s = _index_map_subjects_by_id(old_sd, new_sd)
        new_subs_len = len(_subjects_as_objs(new_sd))
        new_vis_len = len(new_visits)
        new_grp_len = len(new_groups)

        rows = (
            db.query(models.StudyEntryData)
              .filter(and_(models.StudyEntryData.study_id == study_id,
                           models.StudyEntryData.form_version == from_version))
              .all()
        )
        inserted = 0
        skipped = 0
        for r in rows:
            s_new = map_s.get(r.subject_index, r.subject_index)
            v_new = map_v.get(r.visit_index, r.visit_index)
            g_new = map_g.get(r.group_index, r.group_index)

            s_new = s_new if _safe_idx(s_new, new_subs_len) is not None else None
            v_new = v_new if _safe_idx(v_new, new_vis_len)  is not None else None
            g_new = g_new if _safe_idx(g_new, new_grp_len)  is not None else None

            if s_new is None or v_new is None or g_new is None:
                skipped += 1
                continue

            clone = models.StudyEntryData(
                study_id=study_id,
                subject_index=s_new,
                visit_index=v_new,
                group_index=g_new,
                data=_json_clone(r.data or {}),
                skipped_required_flags=_json_clone(r.skipped_required_flags or []),
                form_version=to_version,
            )
            db.add(clone)
            inserted += 1

        db.commit()
        if skipped:
            logger.warning(
                "clone_entries_forward: study_id=%s from v%s→v%s inserted=%s skipped=%s (mapping miss)",
                study_id, from_version, to_version, inserted, skipped
            )

    # ----- Guards for write paths -----

    @staticmethod
    def latest_writable_version(db: Session, study_id: int) -> int:
        """
        Only latest is writable. Raise if missing.
        """
        v = VersionManager.latest(db, study_id)
        if not v:
            raise ValueError(f"No template version found for study_id={study_id}")
        return v.version

    @staticmethod
    def assert_latest_is_used(db: Session, study_id: int, requested: Optional[int]) -> int:
        """
        Enforce 'latest only' writes. If requested is provided and != latest → raise.
        Returns the latest version to write against.
        """
        latest = VersionManager.latest_writable_version(db, study_id)
        if requested is not None and int(requested) != int(latest):
            raise ValueError(f"Only latest template version ({latest}) can accept new data")
        return latest
