# eCRF_backend/versions.py

# --- How structural-change detection works (versions.py) ---
#
# We only bump the template version when the *structure* of a study changes.
# To decide this, we compare a minimal, normalized snapshot of old vs new study_data.
# the snapshot now includes per-model field *shape* (name, type, options, and
# validation-affecting constraints). Display-only props (labels/helpText/placeholders)
# do not trigger a bump.
#
# Structural changes:
#   - Add/remove/rename groups or visits (by name)
#   - Add/remove/reorder models or fields; field name/type change
#   - Option membership changes for select/radio (display-only reordering is ignored)
#   - Validation-affecting constraint changes (required, pattern, min/max…)
#   - Assignments matrix changes (shape or values)
#   - SUBJECTS: removing subjects or changing their group assignment
#
# Non-structural:
#   - Study title/description text
#   - Group/visit descriptions
#   - Field label/description/placeholder
#   - constraints.helpText
#   - SUBJECTS: adding new subjects (id/group)
#
# Decisions:
#   - If structural AND latest has data  => bump to v+1 (clone rows forward)
#   - If structural AND latest has no data => overwrite latest schema in place
#   - If NON-structural => refresh latest schema in place (so UI sees updates)
#


from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_

from . import models
from .datalad_repo import DataladStudyRepo
from .logger import logger

def _normalized_visibility_logic(vl: Any) -> Dict[str, Any]:
    if not isinstance(vl, dict):
        return {"action": "show", "match": "all", "rules": []}

    rules = []
    for r in vl.get("rules") or []:
        if not isinstance(r, dict):
            continue
        rules.append({
            "sourceFieldKey": _norm_str(r.get("sourceFieldKey")),
            "operator": _norm_str(r.get("operator") or "eq"),
            "value": _json_clone(r.get("value")),
            "valueTo": _json_clone(r.get("valueTo")),
        })

    return {
        "action": _norm_str(vl.get("action") or "show"),
        "match": _norm_str(vl.get("match") or "all"),
        "rules": rules,
    }

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


def _is_unassigned_group(g: Any) -> bool:
    gg = _norm_str(g)
    if gg == "":
        return True
    if gg == "-1":
        return True
    return False


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
        if subs and isinstance(subs[0], list):
            return [
                {
                    "id": _norm_str(a[0] if len(a) > 0 else ""),
                    "group": _norm_str(a[1] if len(a) > 1 else ""),
                }
                for a in subs
            ]
        if subs and isinstance(subs[0], str):
            return [{"id": _norm_str(x), "group": ""} for x in subs]
        return [
            {
                **(x or {}),
                "id": _norm_str((x or {}).get("id")),
                "group": _norm_str((x or {}).get("group")),
            }
            for x in subs
        ]
    return []


def _selected_models_list(sd: Dict[str, Any]) -> List[Dict[str, Any]]:
    models_ = sd.get("selectedModels") or sd.get("models") or []
    out: List[Dict[str, Any]] = []
    if isinstance(models_, list):
        for m in models_:
            if isinstance(m, dict):
                title = m.get("title") or m.get("name")
                fields = m.get("fields") or []
                out.append({"title": _norm_str(title), "fields": fields})
            else:
                out.append({"title": _norm_str(m), "fields": []})
    return out


def _ensure_section_and_field_ids(study_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Guarantee every selectedModels section and every field has a stable _id.
    Used for:
      - new studies
      - edited studies
      - version snapshots
    """
    sd = _json_clone(study_data or {})

    selected_models = sd.get("selectedModels") or []
    if not isinstance(selected_models, list):
        return sd

    for sec in selected_models:
        if not isinstance(sec, dict):
            continue

        sec_id = str(sec.get("_id") or sec.get("id") or sec.get("uuid") or "").strip()
        if not sec_id:
            sec["_id"] = str(uuid.uuid4())

        fields = sec.get("fields") or []
        if not isinstance(fields, list):
            continue

        for f in fields:
            if not isinstance(f, dict):
                continue
            field_id = str(f.get("_id") or f.get("id") or f.get("uuid") or "").strip()
            if not field_id:
                f["_id"] = str(uuid.uuid4())

    sd["selectedModels"] = selected_models
    return sd


_STRUCTURAL_CONSTRAINT_KEYS = {
    "required",
    "pattern",
    "min",
    "max",
    "minLength",
    "maxLength",
    "step",
    "allowMultiple",
    "dominantOptions",
    "integerOnly",
    "dateFormat",
    "minDate",
    "maxDate",
}
_TABLE_STRUCTURAL_CONSTRAINT_KEYS = _STRUCTURAL_CONSTRAINT_KEYS | {
    "minTime",
    "maxTime",
    "hourCycle",
    "minDigits",
    "maxDigits",
}

def _field_signature(f: Dict[str, Any]) -> Dict[str, Any]:
    name = f.get("name") or f.get("label") or f.get("key") or f.get("title")
    ftype = f.get("type") or ""
    sig: Dict[str, Any] = {
        "name": _norm_str(name),
        "type": _norm_str(ftype),
    }

    cons = f.get("constraints") or {}
    cons_sig = {k: cons.get(k) for k in sorted(_STRUCTURAL_CONSTRAINT_KEYS) if k in cons}
    if "visibilityLogic" in cons:
        cons_sig["visibilityLogic"] = _normalized_visibility_logic(cons.get("visibilityLogic"))

    if cons_sig:
        sig["constraints"] = cons_sig

    if ftype in ("select", "radio"):
        opts = f.get("options") or []
        if isinstance(opts, list):
            norm_opts: List[str] = []
            for o in opts:
                if isinstance(o, dict):
                    val = o.get("value") or o.get("label") or o.get("name") or o.get("title") or str(o)
                    norm_opts.append(_norm_str(val))
                else:
                    norm_opts.append(_norm_str(o))
            sig["options"] = sorted(norm_opts)
    if ftype == "table":
        sig["table"] = _table_signature(f)

    return sig


def _model_signature(m: Dict[str, Any]) -> Dict[str, Any]:
    title = _norm_str(m.get("title") or m.get("name"))
    fields = m.get("fields") or []
    field_sigs = [_field_signature(f) for f in fields if isinstance(f, dict)]
    return {"title": title, "fields": field_sigs}

def _table_column_signature(col: Dict[str, Any]) -> Dict[str, Any]:
    label = _norm_str(col.get("label") or col.get("name") or col.get("key") or col.get("title"))
    ctype = _norm_str(col.get("type") or "")

    sig: Dict[str, Any] = {
        "label": label,
        "type": ctype,
    }

    cons = col.get("constraints") or {}
    cons_sig = {
        k: cons.get(k)
        for k in sorted(_TABLE_STRUCTURAL_CONSTRAINT_KEYS)
        if k in cons
    }
    if "visibilityLogic" in cons:
        cons_sig["visibilityLogic"] = _normalized_visibility_logic(cons.get("visibilityLogic"))

    if cons_sig:
        sig["constraints"] = cons_sig

    if ctype in ("select", "radio"):
        opts = col.get("options") or []
        if isinstance(opts, list):
            norm_opts: List[str] = []
            for o in opts:
                if isinstance(o, dict):
                    val = (
                        o.get("value")
                        or o.get("label")
                        or o.get("name")
                        or o.get("title")
                        or str(o)
                    )
                    norm_opts.append(_norm_str(val))
                else:
                    norm_opts.append(_norm_str(o))
            sig["options"] = sorted(norm_opts)

    return sig


def _table_signature(f: Dict[str, Any]) -> Dict[str, Any]:
    tc = f.get("tableConfig") or {}

    columns = tc.get("columns") or []
    col_sigs = [
        _table_column_signature(col)
        for col in columns
        if isinstance(col, dict)
    ]

    return {
        "mode": _norm_str(tc.get("mode") or "2d"),
        "initialRows": int(tc.get("initialRows") or 1),
        "allowAddRows": bool(tc.get("allowAddRows", True)),
        "showRowNumbers": bool(tc.get("showRowNumbers", True)),
        "columns": col_sigs,
    }

def _snapshot_structural_core(sd: Dict[str, Any]) -> Dict[str, Any]:
    model_sigs = [_model_signature(m) for m in _selected_models_list(sd)]
    return {
        "groups": _names_from_objs(sd.get("groups") or []),
        "visits": _names_from_objs(sd.get("visits") or []),
        "models": model_sigs,
        "assignments": sd.get("assignments") or [],
    }


def _subjects_diff(old_sd: Dict[str, Any], new_sd: Dict[str, Any]) -> Dict[str, List[str]]:
    old_subs = _subjects_as_objs(old_sd)
    new_subs = _subjects_as_objs(new_sd)

    old_by_id = {s.get("id", ""): s.get("group", "") for s in old_subs}
    new_by_id = {s.get("id", ""): s.get("group", "") for s in new_subs}

    old_ids = set(old_by_id.keys())
    new_ids = set(new_by_id.keys())

    added = sorted(new_ids - old_ids)
    removed = sorted(old_ids - new_ids)

    group_changed = []
    for sid in (old_ids & new_ids):
        og = old_by_id.get(sid, "")
        ng = new_by_id.get(sid, "")
        if og == ng:
            continue

        if _is_unassigned_group(og) and not _is_unassigned_group(ng):
            continue

        group_changed.append(sid)

    return {
        "added": added,
        "removed": sorted(removed),
        "group_changed": sorted(group_changed),
    }


def _subjects_change_is_structural(old_sd: Dict[str, Any], new_sd: Dict[str, Any]) -> bool:
    diff = _subjects_diff(old_sd, new_sd)
    return bool(diff["removed"] or diff["group_changed"])


def _snapshot_structural(sd: Dict[str, Any]) -> Dict[str, Any]:
    base = _snapshot_structural_core(sd)
    base["subjects"] = sorted(
        [(x.get("id", ""), x.get("group", "")) for x in _subjects_as_objs(sd)]
    )
    return base


def _schemas_equal(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    import json
    return json.dumps(a or {}, sort_keys=True) == json.dumps(b or {}, sort_keys=True)


def _coerce_rich_snapshot(sd: Dict[str, Any]) -> Dict[str, Any]:
    snap = _ensure_section_and_field_ids(_json_clone(sd if isinstance(sd, dict) else {}))

    if "study" not in snap or not isinstance(snap.get("study"), dict):
        title = _norm_str(snap.get("title"))
        description = _norm_str(snap.get("description"))
        snap["study"] = {"id": _norm_str(snap.get("id")), "title": title, "description": description}

    def _to_objs(key: str):
        arr = snap.get(key) or []
        out = []
        for it in arr if isinstance(arr, list) else []:
            if isinstance(it, dict):
                name = it.get("name") or it.get("title")
                out.append({"name": _norm_str(name), **{k: v for k, v in it.items() if k != "name"}})
            else:
                out.append({"name": _norm_str(it)})
        snap[key] = out

    _to_objs("groups")
    _to_objs("visits")

    models_ = snap.get("selectedModels") or snap.get("models") or []
    norm_models = []
    for m in models_ if isinstance(models_, list) else []:
        if isinstance(m, dict):
            title = m.get("title") or m.get("name")
            mm = {"title": _norm_str(title), **{k: v for k, v in m.items() if k != "title"}}
            if not str(mm.get("_id") or mm.get("id") or "").strip():
                mm["_id"] = str(uuid.uuid4())

            fields = mm.get("fields") or []
            norm_fields = []
            for f in fields if isinstance(fields, list) else []:
                if isinstance(f, dict):
                    ff = dict(f)
                    if not str(ff.get("_id") or ff.get("id") or "").strip():
                        ff["_id"] = str(uuid.uuid4())
                    norm_fields.append(ff)
            mm["fields"] = norm_fields
            norm_models.append(mm)
        else:
            norm_models.append({"title": _norm_str(m), "fields": [], "_id": str(uuid.uuid4())})

    snap["selectedModels"] = norm_models
    snap["subjects"] = _subjects_as_objs(snap)
    return snap


def _index_map_by_name(old_names: List[str], new_names: List[str]) -> Dict[int, int]:
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
    new_by_id = {s.get("id", ""): idx for idx, s in enumerate(new_subs)}
    out: Dict[int, int] = {}
    for i, s in enumerate(old_subs):
        sid = s.get("id", "")
        if sid in new_by_id:
            out[i] = new_by_id[sid]
    return out


def _safe_idx(idx: int, limit: int) -> Optional[int]:
    return idx if 0 <= idx < limit else None


def _choice_options(field_or_col: Dict[str, Any]) -> List[str]:
    opts = field_or_col.get("options") or []
    if not isinstance(opts, list):
        return []

    out: List[str] = []
    for opt in opts:
        if isinstance(opt, dict):
            val = (
                opt.get("value")
                or opt.get("label")
                or opt.get("name")
                or opt.get("title")
                or str(opt)
            )
        else:
            val = opt
        s = _norm_str(val)
        if s:
            out.append(s)
    return out


def _choice_options_changed(old_obj: Dict[str, Any], new_obj: Dict[str, Any]) -> bool:
    return sorted(_choice_options(old_obj)) != sorted(_choice_options(new_obj))


def _dominant_options(field_or_col: Dict[str, Any]) -> List[str]:
    cons = field_or_col.get("constraints") or {}
    raw = cons.get("dominantOptions") or []
    if not isinstance(raw, list):
        return []
    return [_norm_str(value) for value in raw if _norm_str(value)]


def _choice_definition_changed(old_obj: Dict[str, Any], new_obj: Dict[str, Any]) -> bool:
    return (
        _choice_options_changed(old_obj, new_obj)
        or _dominant_options(old_obj) != _dominant_options(new_obj)
    )


def _is_multi_choice(field_or_col: Dict[str, Any], value: Any) -> bool:
    cons = field_or_col.get("constraints") or {}
    return bool(cons.get("allowMultiple")) or isinstance(value, list)


def _empty_choice_value(field_or_col: Dict[str, Any], previous_value: Any) -> Any:
    return [] if _is_multi_choice(field_or_col, previous_value) else ""


def _sanitize_choice_value_for_new_options(
    value: Any,
    new_field_or_col: Dict[str, Any],
) -> Tuple[Any, bool]:
    if value is None or value == "":
        return value, False

    valid = set(_choice_options(new_field_or_col))
    if not valid:
        return _empty_choice_value(new_field_or_col, value), value not in (None, "", [])

    if isinstance(value, list):
        kept = [v for v in value if _norm_str(v) in valid]
        dominant = set(_dominant_options(new_field_or_col))
        selected_dominant = next(
            (v for v in kept if _norm_str(v) in dominant),
            None,
        )
        if selected_dominant is not None:
            kept = [selected_dominant]
        changed = kept != value
        return kept, changed

    if _norm_str(value) in valid:
        return value, False

    return _empty_choice_value(new_field_or_col, value), True


def _identity_values(obj: Dict[str, Any], *, include_label: bool = True) -> List[str]:
    keys = ["id", "_id", "field_id", "uid", "key", "name", "title"]
    if include_label:
        keys.append("label")

    vals: List[str] = []
    for key in keys:
        v = _norm_str(obj.get(key))
        if v:
            vals.append(v)
    return vals


def _identity_key(obj: Dict[str, Any], *, include_label: bool = True) -> str:
    vals = _identity_values(obj, include_label=include_label)
    return vals[0].lower() if vals else ""


def _section_data_key(section: Dict[str, Any]) -> str:
    return section.get("title") or section.get("name") or ""


def _field_data_keys(field: Dict[str, Any], fallback_index: int) -> List[str]:
    keys = _identity_values(field, include_label=True)
    keys.append(f"f{fallback_index}")

    out: List[str] = []
    seen = set()
    for key in keys:
        s = _norm_str(key)
        if not s:
            continue
        lower = s.lower()
        if lower in seen:
            continue
        seen.add(lower)
        out.append(s)
    return out


def _find_existing_key(container: Dict[str, Any], candidates: List[str]) -> Optional[str]:
    for cand in candidates:
        if cand in container:
            return cand

    lower_map = {_norm_str(k).lower(): k for k in container.keys()}
    for cand in candidates:
        found = lower_map.get(_norm_str(cand).lower())
        if found is not None:
            return found
    return None


def _index_fields(fields: Any) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    if not isinstance(fields, list):
        return out

    for idx, field in enumerate(fields):
        if not isinstance(field, dict):
            continue
        key = _identity_key(field)
        if key:
            out[key] = {"field": field, "index": idx}
    return out


def _column_data_key(col: Dict[str, Any], fallback_index: int) -> str:
    return (
        _norm_str(col.get("id"))
        or _norm_str(col.get("key"))
        or _norm_str(col.get("label"))
        or _norm_str(col.get("name"))
        or f"column_{fallback_index + 1}"
    )


def _index_table_columns(columns: Any) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    if not isinstance(columns, list):
        return out

    for idx, col in enumerate(columns):
        if not isinstance(col, dict):
            continue
        key = _identity_key(col)
        if key:
            out[key] = {"column": col, "index": idx}
    return out


def _sanitize_table_choice_values(
    table_value: Any,
    old_field: Dict[str, Any],
    new_field: Dict[str, Any],
) -> Tuple[Any, int]:
    if not isinstance(table_value, dict):
        return table_value, 0

    rows = table_value.get("rows")
    if not isinstance(rows, list):
        return table_value, 0

    old_cols = (old_field.get("tableConfig") or {}).get("columns") or []
    new_cols = (new_field.get("tableConfig") or {}).get("columns") or []
    old_by_key = _index_table_columns(old_cols)
    changed_count = 0

    next_value = _json_clone(table_value)
    next_rows = next_value.get("rows")
    if not isinstance(next_rows, list):
        return table_value, 0

    for new_idx, new_col in enumerate(new_cols if isinstance(new_cols, list) else []):
        if not isinstance(new_col, dict):
            continue

        new_type = _norm_str(new_col.get("type")).lower()
        if new_type not in ("select", "radio"):
            continue

        match = old_by_key.get(_identity_key(new_col))
        if not match:
            continue

        old_col = match["column"]
        old_type = _norm_str(old_col.get("type")).lower()
        if old_type not in ("select", "radio"):
            continue
        if not _choice_definition_changed(old_col, new_col):
            continue

        old_data_key = _column_data_key(old_col, int(match["index"]))
        new_data_key = _column_data_key(new_col, new_idx)

        for row in next_rows:
            if not isinstance(row, dict):
                continue

            data_key = old_data_key if old_data_key in row else new_data_key
            if data_key not in row:
                continue

            sanitized, changed = _sanitize_choice_value_for_new_options(row.get(data_key), new_col)
            if changed:
                row[data_key] = sanitized
                changed_count += 1

    return next_value, changed_count


def _sanitize_entry_data_for_new_options(
    data: Any,
    old_sd: Dict[str, Any],
    new_sd: Dict[str, Any],
) -> Tuple[Any, int]:
    sanitized = _json_clone(data or {})
    changed_count = 0

    old_models = _selected_models_list(old_sd)
    new_models = _selected_models_list(new_sd)
    old_sections_by_key = {
        _identity_key(sec): sec
        for sec in old_models
        if _identity_key(sec)
    }

    for new_sec_idx, new_sec in enumerate(new_models):
        sec_key = _identity_key(new_sec)
        old_sec = old_sections_by_key.get(sec_key)
        if not old_sec:
            continue

        old_fields_by_key = _index_fields(old_sec.get("fields") or [])
        new_fields = new_sec.get("fields") or []

        for new_field_idx, new_field in enumerate(new_fields if isinstance(new_fields, list) else []):
            if not isinstance(new_field, dict):
                continue

            match = old_fields_by_key.get(_identity_key(new_field))
            if not match:
                continue

            old_field = match["field"]
            new_type = _norm_str(new_field.get("type")).lower()
            old_type = _norm_str(old_field.get("type")).lower()

            if new_type == "table" and old_type == "table":
                changed_count += _sanitize_table_field_in_entry_data(
                    sanitized,
                    new_sec_idx,
                    old_sec,
                    new_sec,
                    old_field,
                    new_field,
                    int(match["index"]),
                    new_field_idx,
                )
                continue

            if new_type not in ("select", "radio") or old_type not in ("select", "radio"):
                continue
            if not _choice_definition_changed(old_field, new_field):
                continue

            changed_count += _sanitize_regular_choice_field_in_entry_data(
                sanitized,
                new_sec_idx,
                old_sec,
                new_sec,
                old_field,
                new_field,
                int(match["index"]),
                new_field_idx,
            )

    return sanitized, changed_count


def _sanitize_regular_choice_field_in_entry_data(
    data: Any,
    sec_idx: int,
    old_sec: Dict[str, Any],
    new_sec: Dict[str, Any],
    old_field: Dict[str, Any],
    new_field: Dict[str, Any],
    old_field_idx: int,
    new_field_idx: int,
) -> int:
    if isinstance(data, list):
        if not (0 <= sec_idx < len(data)):
            return 0
        row = data[sec_idx]
        if not isinstance(row, list) or not (0 <= new_field_idx < len(row)):
            return 0
        sanitized, changed = _sanitize_choice_value_for_new_options(row[new_field_idx], new_field)
        if changed:
            row[new_field_idx] = sanitized
            return 1
        return 0

    if not isinstance(data, dict):
        return 0

    sec_key = _find_existing_key(data, [_section_data_key(new_sec), _section_data_key(old_sec)])
    sec_data = data.get(sec_key) if sec_key is not None else None
    if not isinstance(sec_data, dict):
        return 0

    field_key = _find_existing_key(
        sec_data,
        _field_data_keys(new_field, new_field_idx) + _field_data_keys(old_field, old_field_idx),
    )
    if field_key is None:
        return 0

    sanitized, changed = _sanitize_choice_value_for_new_options(sec_data.get(field_key), new_field)
    if changed:
        sec_data[field_key] = sanitized
        return 1
    return 0


def _sanitize_table_field_in_entry_data(
    data: Any,
    sec_idx: int,
    old_sec: Dict[str, Any],
    new_sec: Dict[str, Any],
    old_field: Dict[str, Any],
    new_field: Dict[str, Any],
    old_field_idx: int,
    new_field_idx: int,
) -> int:
    if isinstance(data, list):
        if not (0 <= sec_idx < len(data)):
            return 0
        row = data[sec_idx]
        if not isinstance(row, list) or not (0 <= new_field_idx < len(row)):
            return 0
        sanitized, changed_count = _sanitize_table_choice_values(row[new_field_idx], old_field, new_field)
        if changed_count:
            row[new_field_idx] = sanitized
        return changed_count

    if not isinstance(data, dict):
        return 0

    sec_key = _find_existing_key(data, [_section_data_key(new_sec), _section_data_key(old_sec)])
    sec_data = data.get(sec_key) if sec_key is not None else None
    if not isinstance(sec_data, dict):
        return 0

    field_key = _find_existing_key(
        sec_data,
        _field_data_keys(new_field, new_field_idx) + _field_data_keys(old_field, old_field_idx),
    )
    if field_key is None:
        return 0

    sanitized, changed_count = _sanitize_table_choice_values(sec_data.get(field_key), old_field, new_field)
    if changed_count:
        sec_data[field_key] = sanitized
    return changed_count


class VersionManager:
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
        meta = (
            db.query(models.StudyMetadata)
            .filter(models.StudyMetadata.id == study_id)
            .first()
        )
        if not meta:
            return False

        try:
            repo = DataladStudyRepo()
            return repo.version_has_entries(study_id, meta.study_name, version)
        except Exception:
            return False

    @staticmethod
    def ensure_initial_version(db: Session, study_id: int, study_data: Dict[str, Any]) -> int:
        v = VersionManager.latest(db, study_id)
        if v:
            return v.version

        normalized = _ensure_section_and_field_ids(study_data or {})
        snap_rich = _coerce_rich_snapshot(normalized)

        v = models.StudyTemplateVersion(
            study_id=study_id,
            version=1,
            schema=snap_rich,
        )
        db.add(v)
        db.commit()
        db.refresh(v)
        logger.info("Initialized template version v1 for study_id=%s", study_id)
        return v.version

    @staticmethod
    def preview_decision(
        db: Session,
        study_id: int,
        old_sd: Dict[str, Any],
        new_sd: Dict[str, Any],
    ) -> VersionDecision:
        old_sd = _ensure_section_and_field_ids(old_sd or {})
        new_sd = _ensure_section_and_field_ids(new_sd or {})

        latest = VersionManager.latest(db, study_id)
        latest_version = latest.version if latest else 0
        has_data = VersionManager.version_has_data(db, study_id, latest_version) if latest else False

        core_old = _snapshot_structural_core(old_sd)
        core_new = _snapshot_structural_core(new_sd)
        base_structural_change = not _schemas_equal(core_old, core_new)

        subject_structural_change = _subjects_change_is_structural(old_sd, new_sd)
        structural_change = base_structural_change or subject_structural_change

        if not structural_change:
            return VersionDecision(
                structural_change=False,
                base_structural_change=base_structural_change,
                subject_structural_change=subject_structural_change,
                latest_version=latest_version,
                latest_version_has_data=has_data,
                will_bump=False,
                decision_version_after=latest_version or 1,
            )

        will_bump = bool(latest and has_data)
        decision_after = (latest_version + 1) if will_bump else (latest_version or 1)

        return VersionDecision(
            structural_change=True,
            base_structural_change=base_structural_change,
            subject_structural_change=subject_structural_change,
            latest_version=latest_version,
            latest_version_has_data=has_data,
            will_bump=will_bump,
            decision_version_after=decision_after,
        )

    @staticmethod
    def apply_on_update(
        db: Session,
        study_id: int,
        old_sd: Dict[str, Any],
        new_sd: Dict[str, Any],
        audit_callback=None,
    ) -> VersionDecision:
        old_sd = _ensure_section_and_field_ids(old_sd or {})
        new_sd = _ensure_section_and_field_ids(new_sd or {})

        decision = VersionManager.preview_decision(db, study_id, old_sd, new_sd)
        latest = VersionManager.latest(db, study_id)
        latest_version = latest.version if latest else 0
        rich_snap = _coerce_rich_snapshot(new_sd)

        subj_diff = _subjects_diff(old_sd, new_sd)
        added_subject_ids = subj_diff["added"]

        if not decision["structural_change"]:
            if latest:
                latest.schema = rich_snap
                db.commit()
                db.refresh(latest)

                if audit_callback and added_subject_ids:
                    audit_callback(
                        "subjects_added",
                        {
                            "version": latest.version,
                            "count": len(added_subject_ids),
                            "subject_ids": added_subject_ids,
                        },
                    )

                logger.info(
                    "Refreshed template v%s in place for study_id=%s (non-structural)",
                    latest.version,
                    study_id,
                )
                decision["decision_version_after"] = latest.version
                return decision

            v1 = models.StudyTemplateVersion(
                study_id=study_id,
                version=1,
                schema=rich_snap,
            )
            db.add(v1)
            db.commit()
            db.refresh(v1)

            if audit_callback:
                audit_callback("template_initialized", {"version": v1.version})

            logger.info("Initialized template v1 on update for study_id=%s", study_id)
            decision["decision_version_after"] = v1.version
            return decision

        if decision["will_bump"]:
            new_v = models.StudyTemplateVersion(
                study_id=study_id,
                version=latest_version + 1,
                schema=rich_snap,
            )
            db.add(new_v)
            db.commit()
            db.refresh(new_v)

            VersionManager._clone_entries_forward(
                db,
                study_id,
                latest_version,
                new_v.version,
                old_sd,
                new_sd,
            )

            if audit_callback:
                audit_callback(
                    "template_version_bumped",
                    {"from_version": latest_version, "to_version": new_v.version},
                )
                if added_subject_ids:
                    audit_callback(
                        "subjects_added",
                        {
                            "version": new_v.version,
                            "count": len(added_subject_ids),
                            "subject_ids": added_subject_ids,
                        },
                    )

            logger.info(
                "Bumped study_id=%s template from v%s to v%s",
                study_id,
                latest_version,
                new_v.version,
            )
            decision["decision_version_after"] = new_v.version
            return decision

        if latest:
            latest.schema = rich_snap
            db.commit()
            db.refresh(latest)

            if audit_callback:
                audit_callback("template_overwritten_before_data", {"version": latest.version})
                if added_subject_ids:
                    audit_callback(
                        "subjects_added",
                        {
                            "version": latest.version,
                            "count": len(added_subject_ids),
                            "subject_ids": added_subject_ids,
                        },
                    )

            logger.info(
                "Overwrote template v%s in place (no data yet) for study_id=%s",
                latest.version,
                study_id,
            )
            decision["decision_version_after"] = latest.version
            return decision

        v1 = models.StudyTemplateVersion(
            study_id=study_id,
            version=1,
            schema=rich_snap,
        )
        db.add(v1)
        db.commit()
        db.refresh(v1)

        if audit_callback:
            audit_callback("template_initialized", {"version": v1.version})
            if added_subject_ids:
                audit_callback(
                    "subjects_added",
                    {
                        "version": v1.version,
                        "count": len(added_subject_ids),
                        "subject_ids": added_subject_ids,
                    },
                )

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
        meta = (
            db.query(models.StudyMetadata)
            .filter(models.StudyMetadata.id == study_id)
            .first()
        )
        if not meta:
            logger.warning("clone_entries_forward: study metadata not found for study_id=%s", study_id)
            return

        repo = DataladStudyRepo()
        all_rows = repo.list_entries(study_id, meta.study_name)

        rows = []
        for r in all_rows:
            try:
                if int(r.get("form_version") or 0) == int(from_version):
                    rows.append(r)
            except Exception:
                continue

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

        clones: List[Dict[str, Any]] = []
        skipped = 0
        cleaned_choice_values = 0

        for r in rows:
            try:
                old_subject_index = int(r.get("subject_index"))
                old_visit_index = int(r.get("visit_index"))
                old_group_index = int(r.get("group_index"))
            except Exception:
                skipped += 1
                continue

            s_new = map_s.get(old_subject_index, old_subject_index)
            v_new = map_v.get(old_visit_index, old_visit_index)
            g_new = map_g.get(old_group_index, old_group_index)

            s_new = s_new if _safe_idx(s_new, new_subs_len) is not None else None
            v_new = v_new if _safe_idx(v_new, new_vis_len) is not None else None
            g_new = g_new if _safe_idx(g_new, new_grp_len) is not None else None

            if s_new is None or v_new is None or g_new is None:
                skipped += 1
                continue

            cloned_data, cleaned_count = _sanitize_entry_data_for_new_options(
                r.get("data") or {},
                old_sd,
                new_sd,
            )
            cleaned_choice_values += cleaned_count

            clones.append({
                "subject_index": s_new,
                "visit_index": v_new,
                "group_index": g_new,
                "data": cloned_data,
                "skipped_required_flags": _json_clone(r.get("skipped_required_flags") or []),
                "subject_raw": None,
                "visit_raw": None,
                "group_raw": None,
            })

        result = repo.bulk_clone_entries_to_version(
            study_id=study_id,
            study_name=meta.study_name,
            source_version=from_version,
            target_version=to_version,
            clones=clones,
            actor="system",
            actor_name="System clone forward",
            audit_label=f"Clone entries forward v{from_version}→v{to_version}",
        )

        inserted = int(result.get("written_count") or 0)

        if skipped:
            logger.warning(
                "clone_entries_forward: study_id=%s from v%s→v%s inserted=%s skipped=%s cleaned_choice_values=%s (mapping miss)",
                study_id,
                from_version,
                to_version,
                inserted,
                skipped,
                cleaned_choice_values,
            )
        else:
            logger.info(
                "clone_entries_forward: study_id=%s from v%s→v%s inserted=%s cleaned_choice_values=%s",
                study_id,
                from_version,
                to_version,
                inserted,
                cleaned_choice_values,
            )

    @staticmethod
    def latest_writable_version(db: Session, study_id: int) -> int:
        v = VersionManager.latest(db, study_id)
        if not v:
            raise ValueError(f"No template version found for study_id={study_id}")
        return v.version

    @staticmethod
    def assert_latest_is_used(db: Session, study_id: int, requested: Optional[int]) -> int:
        latest = VersionManager.latest_writable_version(db, study_id)
        if requested is not None and int(requested) != int(latest):
            raise ValueError(f"Only latest template version ({latest}) can accept new data")
        return latest
