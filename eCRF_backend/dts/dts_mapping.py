from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
def study_template_snapshot_pid(study_id: int, version: int) -> str:
    return f"casee:study:{study_id}:template:v{version}"
def study_template_snapshot_to_dts_record(study_id: int, version_row) -> Dict[str, Any]:
    return _thing(
        study_template_snapshot_pid(study_id, int(version_row.version)),
        "CaseeStudyTemplateSnapshot",
        {
            "study_pid": study_pid(study_id),
            "study_id": study_id,
            "version": int(version_row.version),
            "created_at": _safe_iso(getattr(version_row, "created_at", None)),
            "schema_json": _safe_json_string(getattr(version_row, "schema", {}) or {}),
            "extra_json": _safe_json_string({}),
        },
    )
def study_file_pid(study_id: int, file_id: int) -> str:
    return f"casee:study:{study_id}:file:{file_id}"
def study_file_to_dts_record(study, content, db_file) -> Dict[str, Any]:
    study_data = (content.study_data or {}) if content else {}

    subject_id = _lookup_subject_id(study_data, getattr(db_file, "subject_index", None))
    visit_name = _lookup_visit_name(study_data, getattr(db_file, "visit_index", None))
    group_name = _lookup_group_name(study_data, getattr(db_file, "group_index", None))

    return _thing(
        study_file_pid(study.id, db_file.id),
        "CaseeStudyFile",
        {
            "study_pid": study_pid(study.id),
            "study_id": study.id,
            "file_id": db_file.id,
            "file_name": db_file.file_name,
            "file_path": db_file.file_path,
            "description": getattr(db_file, "description", None),
            "storage_option": getattr(db_file, "storage_option", None),
            "created_at": _safe_iso(getattr(db_file, "created_at", None)),
            "subject_index": getattr(db_file, "subject_index", None),
            "visit_index": getattr(db_file, "visit_index", None),
            "group_index": getattr(db_file, "group_index", None),
            "subject_id": subject_id,
            "visit_key": _slug(visit_name) if visit_name else None,
            "group_key": _slug(group_name) if group_name else None,
            "extra_json": _safe_json_string({}),
        },
    )
def study_entry_pid(study_id: int, form_version: int, subject_index: int, visit_index: int, group_index: int) -> str:
    return f"casee:study:{study_id}:entry:v{form_version}:s{subject_index}:vi{visit_index}:g{group_index}"
def _safe_list(value: Any) -> list:
    return value if isinstance(value, list) else []
def _lookup_group_name(study_data: Dict[str, Any], group_index: Optional[int]) -> Optional[str]:
    groups = _safe_list((study_data or {}).get("groups"))
    if group_index is None:
        return None
    if 0 <= group_index < len(groups):
        g = groups[group_index]
        if isinstance(g, dict):
            return g.get("name")
    return None
def _lookup_visit_name(study_data: Dict[str, Any], visit_index: Optional[int]) -> Optional[str]:
    visits = _safe_list((study_data or {}).get("visits"))
    if visit_index is None:
        return None
    if 0 <= visit_index < len(visits):
        v = visits[visit_index]
        if isinstance(v, dict):
            return v.get("name")
    return None

def _lookup_subject_id(study_data: Dict[str, Any], subject_index: Optional[int]) -> Optional[str]:
    subjects = _safe_list((study_data or {}).get("subjects"))
    if subject_index is None:
        return None
    if 0 <= subject_index < len(subjects):
        s = subjects[subject_index]
        if isinstance(s, dict):
            return s.get("id")
    return None
def _build_field_catalog(study_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Build a catalog from selectedModels and forms so entry values can carry context.
    Key preference:
      1. field _id
      2. field name
    """
    catalog: Dict[str, Dict[str, Any]] = {}

    selected_models = _safe_list((study_data or {}).get("selectedModels"))
    for model in selected_models:
        if not isinstance(model, dict):
            continue
        model_title = model.get("title")
        for field in _safe_list(model.get("fields")):
            if not isinstance(field, dict):
                continue
            key = field.get("_id") or field.get("name")
            if not key:
                continue
            catalog[str(key)] = {
                "field_key": field.get("_id") or field.get("name"),
                "field_name": field.get("name"),
                "field_label": field.get("label"),
                "field_type": field.get("type"),
                "model_title": model_title,
                "section_title": None,
                "raw": field,
            }

    forms = _safe_list((study_data or {}).get("forms"))
    for form in forms:
        if not isinstance(form, dict):
            continue
        for section in _safe_list(form.get("sections")):
            if not isinstance(section, dict):
                continue
            section_title = section.get("title")
            for field in _safe_list(section.get("fields")):
                if not isinstance(field, dict):
                    continue
                key = field.get("_id") or field.get("name")
                if not key:
                    continue
                key = str(key)
                if key not in catalog:
                    catalog[key] = {
                        "field_key": field.get("_id") or field.get("name"),
                        "field_name": field.get("name"),
                        "field_label": field.get("label"),
                        "field_type": field.get("type"),
                        "model_title": None,
                        "section_title": section_title,
                        "raw": field,
                    }
                else:
                    catalog[key]["section_title"] = section_title

    return catalog
def _entry_field_values(study_data: Dict[str, Any], data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Flatten a saved entry into a list of field/value objects.
    We primarily match by field name, because your entry payload uses field names as keys.
    """
    data = data or {}
    catalog = _build_field_catalog(study_data)

    # secondary catalog by field_name
    by_name: Dict[str, Dict[str, Any]] = {}
    for item in catalog.values():
        fname = item.get("field_name")
        if fname:
            by_name[str(fname)] = item

    out: List[Dict[str, Any]] = []
    for key, value in data.items():
        meta = by_name.get(str(key)) or catalog.get(str(key)) or {}
        out.append({
            "field_key": meta.get("field_key") or str(key),
            "field_name": meta.get("field_name") or str(key),
            "field_label": meta.get("field_label"),
            "field_type": meta.get("field_type"),
            "section_title": meta.get("section_title"),
            "model_title": meta.get("model_title"),
            "value_json": _safe_json_string(value),
            "extra_json": _safe_json_string({}),
        })
    return out
def study_entry_to_dts_record(
    study,
    content,
    entry,
    actor_id: Optional[int] = None,
    actor_name: Optional[str] = None,
) -> Dict[str, Any]:
    study_data = (content.study_data or {}) if content else {}

    subject_id = _lookup_subject_id(study_data, getattr(entry, "subject_index", None))
    visit_name = _lookup_visit_name(study_data, getattr(entry, "visit_index", None))
    group_name = _lookup_group_name(study_data, getattr(entry, "group_index", None))

    return _thing(
        study_entry_pid(
            study.id,
            int(getattr(entry, "form_version", 1) or 1),
            int(getattr(entry, "subject_index", 0) or 0),
            int(getattr(entry, "visit_index", 0) or 0),
            int(getattr(entry, "group_index", 0) or 0),
        ),
        "CaseeStudyEntry",
        {
            "study_pid": study_pid(study.id),
            "study_id": study.id,
            "entry_id": getattr(entry, "id", None),
            "form_version": int(getattr(entry, "form_version", 1) or 1),

            "subject_index": int(getattr(entry, "subject_index", 0) or 0),
            "visit_index": int(getattr(entry, "visit_index", 0) or 0),
            "group_index": int(getattr(entry, "group_index", 0) or 0),

            "subject_id": subject_id,
            "visit_key": _slug(visit_name) if visit_name else None,
            "group_key": _slug(group_name) if group_name else None,

            "created_at": _safe_iso(getattr(entry, "created_at", None)),
            "actor_id": actor_id,
            "actor_name": actor_name,

            "data_json": _safe_json_string(getattr(entry, "data", {}) or {}),
            "skipped_required_flags_json": _safe_json_string(getattr(entry, "skipped_required_flags", None)),
            "field_values": _entry_field_values(study_data, getattr(entry, "data", {}) or {}),
            "extra_json": _safe_json_string({}),
        },
    )
def _assignment_matrix_back(protocol: Dict[str, Any]) -> Any:
    matrix = protocol.get("assignment_matrix") or {}
    rows = matrix.get("rows") or []
    out = []
    for row in rows:
        row_out = []
        for cell in (row.get("cells") or []):
            row_out.append(cell.get("values") or [])
        out.append(row_out)

    if out:
        return out

    return _json_loads_safe(matrix.get("raw_json"))

def _bids_metadata_back(protocol: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    bids = protocol.get("bids_metadata") or {}
    if not bids:
        return None

    subject_label_map = {}
    for item in (bids.get("subject_label_map") or []):
        k = item.get("key")
        if k is not None:
            subject_label_map[k] = item.get("value")

    session_label_map = {}
    for item in (bids.get("session_label_map") or []):
        k = item.get("key")
        if k is not None:
            session_label_map[k] = item.get("value")

    column_catalog = []
    for item in (bids.get("column_catalog") or []):
        column_catalog.append({
            "sIdx": item.get("section_index"),
            "fIdx": item.get("field_index"),
            "name": item.get("name"),
        })

    if subject_label_map or session_label_map or column_catalog:
        return {
            "subject_label_map": subject_label_map,
            "session_label_map": session_label_map,
            "column_catalog": column_catalog,
        }

    return _json_loads_safe(bids.get("raw_json"))

def _to_int_or_none(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        return int(value)
    except Exception:
        return None

def _map_assignment_matrix(assignments: Any) -> Dict[str, Any]:
    assignments = assignments or []
    rows = []

    groups_count = len(assignments) if isinstance(assignments, list) else 0
    visits_count = 0
    models_count = 0

    if isinstance(assignments, list) and assignments:
        first_row = assignments[0] if isinstance(assignments[0], list) else []
        visits_count = len(first_row)
        if first_row and isinstance(first_row[0], list):
            models_count = len(first_row[0])

    for row_idx, row in enumerate(assignments if isinstance(assignments, list) else []):
        cell_groups = []
        for cell_idx, cell in enumerate(row if isinstance(row, list) else []):
            values = []
            if isinstance(cell, list):
                values = [bool(v) for v in cell]
            cell_groups.append({
                "cell_index": row_idx * 10000 + cell_idx,
                "values": values,
            })

        rows.append({
            "row_index": row_idx,
            "cells": cell_groups,
        })

    return {
        "groups_count": groups_count,
        "visits_count": visits_count,
        "models_count": models_count,
        "rows": rows,
        "raw_json": _safe_json_string(assignments),
    }
def _map_key_value_dict(obj: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    if not isinstance(obj, dict):
        return out
    for k, v in obj.items():
        out.append({
            "key": str(k),
            "value": None if v is None else str(v),
        })
    return out
def _map_bids_metadata(study_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    bids = study_data.get("bids")
    if not isinstance(bids, dict):
        return None

    column_catalog = []
    for item in bids.get("column_catalog", []) or []:
        if isinstance(item, dict):
            column_catalog.append({
                "section_index": _to_int_or_none(item.get("sIdx")),
                "field_index": _to_int_or_none(item.get("fIdx")),
                "name": item.get("name"),
                "raw_json": _safe_json_string({
                    k: v for k, v in item.items() if k not in {"sIdx", "fIdx", "name"}
                }),
            })

    return {
        "subject_label_map": _map_key_value_dict(bids.get("subject_label_map")),
        "session_label_map": _map_key_value_dict(bids.get("session_label_map")),
        "column_catalog": column_catalog,
        "raw_json": _safe_json_string(bids),
    }

def study_pid(study_id: int) -> str:
    return f"casee:study:{study_id}"


def _safe_json_string(value: Any) -> str:
    try:
        return json.dumps(value if value is not None else {}, ensure_ascii=False)
    except Exception:
        return "{}"


def _safe_iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    try:
        return str(value)
    except Exception:
        return None


def _slug(value: str) -> str:
    s = (value or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "item"


def _thing(pid: str, schema_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "pid": pid,
        "schema_type": schema_type,
        **payload,
    }


def _field_pid(study_id: int, field_obj: Dict[str, Any], fallback_name: str) -> str:
    fid = field_obj.get("_id") or fallback_name
    return f"casee:study:{study_id}:field:{fid}"


def _section_pid(study_id: int, section_obj: Dict[str, Any], idx: int) -> str:
    sid = section_obj.get("_id") or f"section-{idx}"
    return f"casee:study:{study_id}:section:{sid}"


def _model_pid(study_id: int, model_obj: Dict[str, Any], idx: int) -> str:
    title = model_obj.get("title") or f"model-{idx}"
    return f"casee:study:{study_id}:model:{_slug(title)}"


def _group_pid(study_id: int, group_name: str) -> str:
    return f"casee:study:{study_id}:group:{_slug(group_name)}"


def _visit_pid(study_id: int, visit_name: str) -> str:
    return f"casee:study:{study_id}:visit:{_slug(visit_name)}"


def _subject_pid(study_id: int, subject_id: str) -> str:
    return f"casee:study:{study_id}:subject:{subject_id}"


def _map_options(options: List[Any]) -> List[Dict[str, Any]]:
    out = []
    for opt in options or []:
        if isinstance(opt, dict):
            out.append({
                "value": str(opt.get("value", "")),
                "label": opt.get("label"),
                "description": opt.get("description"),
                "extra_json": _safe_json_string({k: v for k, v in opt.items() if k not in {"value", "label", "description"}}),
            })
        else:
            out.append({
                "value": str(opt),
                "label": str(opt),
                "description": None,
                "extra_json": _safe_json_string({}),
            })
    return out


def _map_visibility_logic(value: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(value, dict):
        return None

    rules = []
    for r in value.get("rules", []) or []:
        if isinstance(r, dict):
            rules.append({
                "source_field_key": r.get("sourceFieldKey"),
                "operator": r.get("operator"),
                "value_json": _safe_json_string(r.get("value")),
                "extra_json": _safe_json_string({k: v for k, v in r.items() if k not in {"sourceFieldKey", "operator", "value"}}),
            })

    return {
        "action": value.get("action"),
        "match": value.get("match"),
        "rules": rules,
        "extra_json": _safe_json_string({k: v for k, v in value.items() if k not in {"action", "match", "rules"}}),
    }


def _map_constraints(value: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    value = value or {}
    return {
        "required": value.get("required"),
        "readonly": value.get("readonly"),
        "pattern": _none_if_blank(value.get("pattern")),
        "placeholder": _none_if_blank(value.get("placeholder")),
        "help_text": _none_if_blank(value.get("helpText")),
        "transform": _none_if_blank(value.get("transform")),
        "default_value_json": _safe_json_string(value.get("defaultValue")),
        "visibility_logic": _map_visibility_logic(value.get("visibilityLogic")),
        "extra_json": _safe_json_string({
            k: v for k, v in value.items()
            if k not in {
                "required", "readonly", "pattern", "placeholder",
                "defaultValue", "helpText", "transform", "visibilityLogic"
            }
        }),
    }


def _map_field(study_id: int, field_obj: Dict[str, Any]) -> Dict[str, Any]:
    field_name = field_obj.get("name") or field_obj.get("label") or "field"
    return _thing(
        _field_pid(study_id, field_obj, field_name),
        "CaseeFieldDefinition",
        {
            "field_key": field_obj.get("_id") or field_name,
            "name": field_obj.get("name") or field_name,
            "label": _none_if_blank(field_obj.get("label")),
            "description": _none_if_blank(field_obj.get("description")),
            "placeholder": _none_if_blank(field_obj.get("placeholder")),
            "field_type": field_obj.get("type") or "text",
            "value_json": _safe_json_string(field_obj.get("value")),
            "options": _map_options(field_obj.get("options") or []),
            "constraints": _map_constraints(field_obj.get("constraints") or {}),
            "extra_json": _safe_json_string({
                k: v for k, v in field_obj.items()
                if k not in {
                    "_id", "name", "label", "description", "type", "placeholder",
                    "value", "options", "constraints"
                }
            }),
        },
    )


def _map_model(study_id: int, model_obj: Dict[str, Any], idx: int) -> Dict[str, Any]:
    fields = [_map_field(study_id, f) for f in (model_obj.get("fields") or [])]
    return _thing(
        _model_pid(study_id, model_obj, idx),
        "CaseeModelDefinition",
        {
            "title": model_obj.get("title") or f"Model {idx + 1}",
            "description": _none_if_blank(model_obj.get("description")),
            "fields": fields,
            "source": _none_if_blank(model_obj.get("source")),
            "collapsed": model_obj.get("collapsed"),
            "extra_json": _safe_json_string({
                k: v for k, v in model_obj.items()
                if k not in {"title", "description", "fields", "source", "collapsed"}
            }),
        },
    )


def _map_section(study_id: int, section_obj: Dict[str, Any], idx: int) -> Dict[str, Any]:
    fields = [_map_field(study_id, f) for f in (section_obj.get("fields") or [])]
    return _thing(
        _section_pid(study_id, section_obj, idx),
        "CaseeSectionDefinition",
        {
            "title": section_obj.get("title") or f"Section {idx + 1}",
            "description": _none_if_blank(section_obj.get("description")),
            "source": _none_if_blank(section_obj.get("source")),
            "collapsed": section_obj.get("collapsed"),
            "fields": fields,
            "extra_json": _safe_json_string({
                k: v for k, v in section_obj.items()
                if k not in {"_id", "title", "description", "source", "collapsed", "fields"}
            }),
        },
    )


def _map_calculation(calc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "rule_id": calc.get("id") or "",
        "kind": calc.get("kind"),
        "version": calc.get("version"),
        "op": calc.get("op"),
        "sources": [str(x) for x in (calc.get("sources") or [])],
        "target": calc.get("target"),
        "target_mode": calc.get("targetMode"),
        "enabled": calc.get("enabled"),
        "updated_at": calc.get("updatedAt"),
        "extra_json": _safe_json_string({
            k: v for k, v in calc.items()
            if k not in {"id", "kind", "version", "op", "sources", "target", "targetMode", "enabled", "updatedAt"}
        }),
    }


def _map_condition(cond: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "rule_id": cond.get("id") or "",
        "kind": cond.get("kind"),
        "when_json": _safe_json_string(cond.get("when")),
        "then_json": _safe_json_string(cond.get("then")),
        "else_json": _safe_json_string(cond.get("else")),
        "enabled": cond.get("enabled"),
        "extra_json": _safe_json_string({
            k: v for k, v in cond.items()
            if k not in {"id", "kind", "when", "then", "else", "enabled"}
        }),
    }


def _map_logic(logic_obj: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    logic_obj = logic_obj or {}
    return {
        "version": logic_obj.get("version"),
        "calculations": [_map_calculation(x) for x in (logic_obj.get("calculations") or [])],
        "conditions": [_map_condition(x) for x in (logic_obj.get("conditions") or [])],
        "extra_json": _safe_json_string({
            k: v for k, v in logic_obj.items()
            if k not in {"version", "calculations", "conditions"}
        }),
    }


def _map_form(study_id: int, form_obj: Dict[str, Any], idx: int) -> Dict[str, Any]:
    return _thing(
        f"casee:study:{study_id}:form:{idx + 1}",
        "CaseeFormDefinition",
        {
            "sections": [_map_section(study_id, s, s_idx) for s_idx, s in enumerate(form_obj.get("sections") or [])],
            "logic": _map_logic(form_obj.get("logic")),
            "extra_json": _safe_json_string({
                k: v for k, v in form_obj.items()
                if k not in {"sections", "logic"}
            }),
        },
    )


def _map_groups(study_id: int, groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for idx, g in enumerate(groups or []):
        name = g.get("name") or f"Group {idx + 1}"
        out.append(_thing(
            _group_pid(study_id, name),
            "CaseeGroup",
            {
                "key": _slug(name),
                "name": name,
                "description": _none_if_blank(g.get("description")),
                "order": idx,
                "extra_json": _safe_json_string({k: v for k, v in g.items() if k not in {"name", "description"}}),
            }
        ))
    return out


def _map_visits(study_id: int, visits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for idx, v in enumerate(visits or []):
        name = v.get("name") or f"Visit {idx + 1}"
        out.append(_thing(
            _visit_pid(study_id, name),
            "CaseeVisit",
            {
                "key": _slug(name),
                "name": name,
                "description": _none_if_blank(v.get("description")),
                "order": idx,
                "extra_json": _safe_json_string({k: v for k, v in v.items() if k not in {"name", "description"}}),
            }
        ))
    return out


def _map_subjects(study_id: int, subjects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for s in subjects or []:
        sid = s.get("id") or "UNKNOWN"
        out.append(_thing(
            _subject_pid(study_id, sid),
            "CaseeSubject",
            {
                "subject_id": sid,
                "display_label": sid,
                "group_key": _slug(s.get("group") or "") if s.get("group") else None,
                "extra_json": _safe_json_string({k: v for k, v in s.items() if k not in {"id", "group"}}),
            }
        ))
    return out


def _map_subject_assignments(subjects: List[Dict[str, Any]], assignment_method: Optional[str]) -> List[Dict[str, Any]]:
    out = []
    for s in subjects or []:
        out.append({
            "subject_id": s.get("id"),
            "group_key": _slug(s.get("group") or "") if s.get("group") else None,
            "assignment_method": assignment_method,
            "extra_json": _safe_json_string({}),
        })
    return out


def study_to_dts_record(metadata, content, current_template_version: Optional[int] = None, template_snapshot_created_at: Optional[Any] = None) -> Dict[str, Any]:
    study_data = (content.study_data or {}) if content else {}

    study_meta = study_data.get("study", {}) or {}
    groups = study_data.get("groups", []) or []
    visits = study_data.get("visits", []) or []
    subjects = study_data.get("subjects", []) or []
    selected_models = study_data.get("selectedModels", []) or []
    forms = study_data.get("forms", []) or []
    assignment_method = study_data.get("assignmentMethod")
    logic_obj = (forms[0].get("logic") if forms and isinstance(forms[0], dict) else None) or study_data.get("logic") or {}

    record = _thing(
        study_pid(metadata.id),
        "CaseeStudy",
        {
            "study_id": metadata.id,
            "study_name": metadata.study_name,
            "study_description": metadata.study_description,
            "workflow_status": getattr(metadata, "status", None) or "PUBLISHED",
            "created_by": metadata.created_by,
            "created_at": _safe_iso(getattr(metadata, "created_at", None)),
            "updated_at": _safe_iso(getattr(metadata, "updated_at", None)),
            "draft_of_study_id": getattr(metadata, "draft_of_study_id", None),
            "last_completed_step": getattr(metadata, "last_completed_step", None),

            "metadata": {
                "source_study_id": _none_if_blank(study_meta.get("id")),
                "title": _none_if_blank(study_meta.get("title")),
                "short_name": _none_if_blank(study_meta.get("short_name")),
                "description": _none_if_blank(study_meta.get("description")),
                "study_type": _none_if_blank(study_meta.get("type")),
                "study_phase_status": _none_if_blank(study_meta.get("status")),
                "creator": _none_if_blank(study_meta.get("creator")),
                "publisher": _none_if_blank(study_meta.get("publisher")),
                "start_date": _none_if_blank(study_meta.get("start date")),
                "end_date": _none_if_blank(study_meta.get("End date")),
                "location": _none_if_blank(study_meta.get("Location")),
                "extra_json": _safe_json_string({
                    k: v for k, v in study_meta.items()
                    if k not in {
                        "title", "short_name", "description", "type", "status",
                        "creator", "publisher", "start date", "End date", "Location"
                    }
                }),
            },

            "groups": _map_groups(metadata.id, groups),
            "visits": _map_visits(metadata.id, visits),
            "subjects": _map_subjects(metadata.id, subjects),
            "subject_assignments": _map_subject_assignments(subjects, assignment_method),
            "selected_models": [_map_model(metadata.id, m, i) for i, m in enumerate(selected_models)],
            "forms": [_map_form(metadata.id, f, i) for i, f in enumerate(forms)],

            "protocol": {
            "subject_count": study_data.get("subjectCount"),
            "assignment_method": assignment_method,
            "skip_subject_creation_now": study_data.get("skipSubjectCreationNow"),
            "assignment_matrix": _map_assignment_matrix(study_data.get("assignments")),
            "bids_metadata": _map_bids_metadata(study_data),
            "extra_json": _safe_json_string({
                k: v for k, v in study_data.items()
                if k not in {
                    "study", "groups", "visits", "subjects", "selectedModels",
                    "forms", "assignments", "subjectCount", "assignmentMethod",
                    "skipSubjectCreationNow", "logic", "bids"
                }
            }),
        },

            "template_logic": _map_logic(logic_obj),
            "current_template_version": current_template_version,
            "template_snapshot_created_at": _safe_iso(template_snapshot_created_at),
            "raw_template_json": _safe_json_string(study_data),
            "extra_json": _safe_json_string({}),
        }
    )

    return record


class DTSMetadataShim:
    def __init__(self, record: Dict[str, Any]):
        self.id = record["study_id"]
        self.created_by = record["created_by"]
        self.study_name = record["study_name"]
        self.study_description = record.get("study_description")
        self.status = record.get("workflow_status")
        self.draft_of_study_id = record.get("draft_of_study_id")
        self.last_completed_step = record.get("last_completed_step")
        self.created_at = _parse_dt(record.get("created_at"))
        self.updated_at = _parse_dt(record.get("updated_at"))
        self.permissions = None


class DTSContentShim:
    def __init__(self, record: Dict[str, Any]):
        self.id = None
        self.study_id = record["study_id"]
        self.study_data = record_to_legacy_study_data(record)


def _parse_dt(value: Optional[str]):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def record_to_legacy_study_data(record: Dict[str, Any]) -> Dict[str, Any]:
    metadata = record.get("metadata") or {}
    groups = record.get("groups") or []
    visits = record.get("visits") or []
    subjects = record.get("subjects") or []
    selected_models = record.get("selected_models") or []
    forms = record.get("forms") or []
    protocol = record.get("protocol") or {}
    template_logic = record.get("template_logic") or {}

    def field_back(f: Dict[str, Any]) -> Dict[str, Any]:
        constraints = f.get("constraints") or {}
        visibility_logic = constraints.get("visibility_logic") or None
        back_constraints = {
            "required": constraints.get("required"),
            "readonly": constraints.get("readonly"),
            "pattern": constraints.get("pattern"),
            "placeholder": constraints.get("placeholder"),
            "defaultValue": _json_loads_safe(constraints.get("default_value_json")),
            "helpText": constraints.get("help_text"),
            "transform": constraints.get("transform"),
        }
        if visibility_logic:
            back_constraints["visibilityLogic"] = {
                "action": visibility_logic.get("action"),
                "match": visibility_logic.get("match"),
                "rules": [
                    {
                        "sourceFieldKey": r.get("source_field_key"),
                        "operator": r.get("operator"),
                        "value": _json_loads_safe(r.get("value_json")),
                    }
                    for r in (visibility_logic.get("rules") or [])
                ]
            }

        return {
            "_id": f.get("field_key"),
            "name": f.get("name"),
            "label": f.get("label"),
            "description": f.get("description"),
            "type": f.get("field_type"),
            "placeholder": f.get("placeholder"),
            "value": _json_loads_safe(f.get("value_json")),
            "options": [{"value": o.get("value"), "label": o.get("label"), "description": o.get("description")} for o in (f.get("options") or [])],
            "constraints": {k: v for k, v in back_constraints.items() if v is not None},
        }

    out = {
        "study": {
            "id": metadata.get("source_study_id") or "",
            "title": metadata.get("title"),
            "short_name": metadata.get("short_name"),
            "description": metadata.get("description"),
            "type": metadata.get("study_type"),
            "status": metadata.get("study_phase_status"),
            "creator": metadata.get("creator"),
            "publisher": metadata.get("publisher"),
            "start date": metadata.get("start_date"),
            "End date": metadata.get("end_date"),
            "Location": metadata.get("location"),
        },
        "groups": [
            {"name": g.get("name"), "description": g.get("description")}
            for g in groups
        ],
        "visits": [
            {"name": v.get("name"), "description": v.get("description")}
            for v in visits
        ],
        "subjects": [
            {"id": s.get("subject_id"), "group": _find_group_name_from_key(groups, s.get("group_key"))}
            for s in subjects
        ],
        "selectedModels": [
            {
                "title": m.get("title"),
                "description": m.get("description"),
                "fields": [field_back(f) for f in (m.get("fields") or [])],
            }
            for m in selected_models
        ],
        "forms": [
            {
                "sections": [
                    {
                        "_id": sec.get("pid", "").split(":")[-1],
                        "title": sec.get("title"),
                        "description": sec.get("description"),
                        "source": sec.get("source"),
                        "collapsed": sec.get("collapsed"),
                        "fields": [field_back(f) for f in (sec.get("fields") or [])],
                    }
                    for sec in (frm.get("sections") or [])
                ],
                "logic": {
                    "version": (frm.get("logic") or {}).get("version"),
                    "calculations": [
                        {
                            "id": c.get("rule_id"),
                            "kind": c.get("kind"),
                            "version": c.get("version"),
                            "op": c.get("op"),
                            "sources": c.get("sources") or [],
                            "target": c.get("target"),
                            "targetMode": c.get("target_mode"),
                            "enabled": c.get("enabled"),
                            "updatedAt": c.get("updated_at"),
                        }
                        for c in ((frm.get("logic") or {}).get("calculations") or [])
                    ],
                    "conditions": [
                        {
                            "id": c.get("rule_id"),
                            "kind": c.get("kind"),
                            "when": _json_loads_safe(c.get("when_json")),
                            "then": _json_loads_safe(c.get("then_json")),
                            "else": _json_loads_safe(c.get("else_json")),
                            "enabled": c.get("enabled"),
                        }
                        for c in ((frm.get("logic") or {}).get("conditions") or [])
                    ],
                }
            }
            for frm in forms
        ],
        "assignments": _assignment_matrix_back(protocol),
        "subjectCount": protocol.get("subject_count"),
        "assignmentMethod": protocol.get("assignment_method"),
        "skipSubjectCreationNow": protocol.get("skip_subject_creation_now"),
    }

    if not out["forms"] and template_logic:
        out["logic"] = {
            "version": template_logic.get("version"),
            "calculations": template_logic.get("calculations") or [],
            "conditions": template_logic.get("conditions") or [],
        }
    bids_back = _bids_metadata_back(protocol)
    if bids_back is not None:
        out["bids"] = bids_back

    return out


def _json_loads_safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list, int, float, bool)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return value


def _find_group_name_from_key(groups: List[Dict[str, Any]], key: Optional[str]) -> Optional[str]:
    if not key:
        return None
    for g in groups:
        if g.get("key") == key:
            return g.get("name")
    return key

def _none_if_blank(value: Any) -> Optional[Any]:
    if value is None:
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    return value


class DTSEntryShim:
    def __init__(self, record: Dict[str, Any]):
        self.id = record.get("entry_id")
        self.study_id = record["study_id"]
        self.form_version = record["form_version"]
        self.subject_index = record["subject_index"]
        self.visit_index = record["visit_index"]
        self.group_index = record["group_index"]
        self.data = _json_loads_safe(record.get("data_json")) or {}
        self.skipped_required_flags = _json_loads_safe(record.get("skipped_required_flags_json"))
        self.created_at = _parse_dt(record.get("created_at"))

def dts_entry_record_to_out(record: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": record.get("entry_id"),
        "study_id": record["study_id"],
        "form_version": record["form_version"],
        "subject_index": record["subject_index"],
        "visit_index": record["visit_index"],
        "group_index": record["group_index"],
        "data": _json_loads_safe(record.get("data_json")) or {},
        "skipped_required_flags": _json_loads_safe(record.get("skipped_required_flags_json")),
        "created_at": record.get("created_at"),
    }

def parse_entry_pid_components(pid: str) -> Optional[Dict[str, int]]:
    # casee:study:119:entry:v1:s0:vi0:g0
    try:
        parts = pid.split(":")
        return {
            "study_id": int(parts[2]),
            "form_version": int(parts[4].lstrip("v")),
            "subject_index": int(parts[5].lstrip("s")),
            "visit_index": int(parts[6].lstrip("vi")),
            "group_index": int(parts[7].lstrip("g")),
        }
    except Exception:
        return None