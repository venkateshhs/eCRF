from __future__ import annotations

import math
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple


def _field_keys(field: Dict[str, Any], index: int) -> List[str]:
    keys = [
        field.get("id"),
        field.get("_id"),
        field.get("name"),
        field.get("field_id"),
        field.get("uid"),
        field.get("key"),
        field.get("label"),
        field.get("title"),
        f"f{index}",
    ]
    return [str(key) for key in keys if key not in (None, "")]


def _field_value(
    data: Dict[str, Any],
    section: Dict[str, Any],
    field: Dict[str, Any],
    field_index: int,
) -> Any:
    section_data = data.get(str(section.get("title") or ""))
    if not isinstance(section_data, dict):
        return None
    for key in _field_keys(field, field_index):
        if key in section_data:
            return section_data[key]
    return None


def _is_blank(value: Any, field_type: str = "") -> bool:
    if field_type == "checkbox":
        return value is not True
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, tuple, set)):
        return len(value) == 0
    if field_type == "file" and isinstance(value, dict):
        if value.get("source") == "url":
            return not str(value.get("url") or "").strip()
        file_value = value.get("file") if isinstance(value.get("file"), dict) else value
        return not str(file_value.get("name") or file_value.get("file_name") or "").strip()
    return False


def _assigned(assignments: Any, section_index: int, visit_index: int, group_index: int) -> bool:
    try:
        return bool(assignments[section_index][visit_index][group_index])
    except (IndexError, KeyError, TypeError):
        return False


def _calculated_target_ids(study_data: Dict[str, Any]) -> Set[str]:
    forms = study_data.get("forms") or []
    if not forms or not isinstance(forms[0], dict):
        return set()
    rules = (((forms[0].get("logic") or {}).get("calculations")) or [])
    return {
        str(rule.get("target"))
        for rule in rules
        if isinstance(rule, dict)
        and rule.get("target")
        and rule.get("enabled", True) is not False
        and rule.get("kind") in {"calc", "calc_expr"}
    }


def _is_calculated(field: Dict[str, Any], calculated_targets: Set[str]) -> bool:
    if field.get("computed") or field.get("isCalculatedField"):
        return True
    return any(key in calculated_targets for key in _field_keys(field, -1))


def _to_number(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def _to_date(value: Any) -> Optional[datetime]:
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _to_time_seconds(value: Any) -> Optional[int]:
    match = re.match(r"^(\d{2}):(\d{2})(?::(\d{2}))?$", str(value or "").strip())
    if not match:
        return None
    return int(match.group(1)) * 3600 + int(match.group(2)) * 60 + int(match.group(3) or 0)


def _evaluate_rule(rule: Dict[str, Any], source_value: Any, source_field: Dict[str, Any]) -> bool:
    operator = str(rule.get("operator") or "eq").lower()
    field_type = str(source_field.get("type") or "").lower()
    compare_value = rule.get("value")
    compare_to = rule.get("valueTo")

    if operator in {"empty", "is_empty"}:
        return _is_blank(source_value, field_type)
    if operator in {"not_empty", "is_not_empty"}:
        return not _is_blank(source_value, field_type)

    if field_type in {"select", "radio"}:
        if isinstance(source_value, list):
            right = compare_value if isinstance(compare_value, list) else [compare_value]
            matched = any(item in source_value for item in right)
            if operator == "eq":
                return matched
            if operator == "neq":
                return bool(source_value) and not matched
        else:
            right = compare_value if isinstance(compare_value, list) else [compare_value]
            matched = str(source_value or "") in {str(item or "") for item in right}
            if operator == "eq":
                return matched
            if operator == "neq":
                return not _is_blank(source_value, field_type) and not matched

    if field_type == "checkbox":
        left = bool(source_value)
        right = compare_value in (True, "true", 1, "1")
        if operator == "eq":
            return left == right
        if operator == "neq":
            return left != right

    if field_type in {"number", "slider"}:
        left, right, right_to = (
            _to_number(source_value),
            _to_number(compare_value),
            _to_number(compare_to),
        )
    elif field_type == "date":
        left, right, right_to = _to_date(source_value), _to_date(compare_value), _to_date(compare_to)
    elif field_type == "time":
        left, right, right_to = (
            _to_time_seconds(source_value),
            _to_time_seconds(compare_value),
            _to_time_seconds(compare_to),
        )
    else:
        left, right, right_to = str(source_value or ""), str(compare_value or ""), str(compare_to or "")

    if operator == "eq":
        return left is not None and right is not None and left == right
    if operator == "neq":
        return left is not None and right is not None and left != right
    if operator == "lt":
        return left is not None and right is not None and left < right
    if operator == "lte":
        return left is not None and right is not None and left <= right
    if operator == "gt":
        return left is not None and right is not None and left > right
    if operator == "gte":
        return left is not None and right is not None and left >= right
    if operator == "between":
        return left is not None and right is not None and right_to is not None and right <= left <= right_to
    if operator == "contains":
        return str(right) in str(left)
    if operator == "starts_with":
        return str(left).startswith(str(right))
    if operator == "ends_with":
        return str(left).endswith(str(right))
    if operator == "regex":
        try:
            return re.search(str(right), str(left)) is not None
        except re.error:
            return False
    return False


def _build_field_context(
    selected_models: List[Dict[str, Any]],
    data: Dict[str, Any],
) -> Tuple[Dict[str, Tuple[int, int, Dict[str, Any]]], Dict[Tuple[int, int], Any]]:
    lookup: Dict[str, Tuple[int, int, Dict[str, Any]]] = {}
    values: Dict[Tuple[int, int], Any] = {}
    for section_index, section in enumerate(selected_models):
        for field_index, field in enumerate(section.get("fields") or []):
            values[(section_index, field_index)] = _field_value(data, section, field, field_index)
            for key in _field_keys(field, field_index):
                lookup.setdefault(key, (section_index, field_index, field))
    return lookup, values


def _field_visible(
    selected_models: List[Dict[str, Any]],
    field_lookup: Dict[str, Tuple[int, int, Dict[str, Any]]],
    values: Dict[Tuple[int, int], Any],
    section_index: int,
    field_index: int,
    visiting: Optional[Set[Tuple[int, int]]] = None,
) -> bool:
    field = selected_models[section_index].get("fields", [])[field_index]
    logic = ((field.get("constraints") or {}).get("visibilityLogic")) or {}
    rules = logic.get("rules") if isinstance(logic.get("rules"), list) else []
    if not rules:
        return True

    visiting = set(visiting or set())
    target = (section_index, field_index)
    if target in visiting:
        return False
    visiting.add(target)

    results = []
    for rule in rules:
        source = field_lookup.get(str((rule or {}).get("sourceFieldKey") or ""))
        if not source:
            results.append(False)
            continue
        source_section, source_field_index, source_field = source
        if not _field_visible(
            selected_models,
            field_lookup,
            values,
            source_section,
            source_field_index,
            visiting,
        ):
            results.append(False)
            continue
        results.append(
            _evaluate_rule(
                rule or {},
                values.get((source_section, source_field_index)),
                source_field,
            )
        )

    matched = any(results) if str(logic.get("match") or "all").lower() == "any" else all(results)
    return not matched if str(logic.get("action") or "show").lower() == "hide" else matched


def _table_column_key(column: Dict[str, Any], index: int) -> str:
    direct = column.get("id") or column.get("key")
    if direct:
        return str(direct)
    return (
        re.sub(
            r"[^a-z0-9]+",
            "_",
            str(column.get("label") or f"column_{index + 1}").strip().lower(),
        ).strip("_")
        or f"column_{index + 1}"
    )


def _table_column_visible(
    column: Dict[str, Any],
    row: Dict[str, Any],
    columns: List[Dict[str, Any]],
) -> bool:
    logic = ((column.get("constraints") or {}).get("visibilityLogic")) or {}
    rules = logic.get("rules") if isinstance(logic.get("rules"), list) else []
    if not rules:
        return True

    results = []
    for rule in rules:
        source_key = str((rule or {}).get("sourceFieldKey") or "")
        source_index = next(
            (
                index
                for index, source_column in enumerate(columns)
                if source_key
                in {
                    str(source_column.get("id") or ""),
                    str(source_column.get("key") or ""),
                    str(source_column.get("label") or ""),
                    _table_column_key(source_column, index),
                }
            ),
            -1,
        )
        if source_index < 0:
            results.append(False)
            continue
        source_column = columns[source_index]
        results.append(
            _evaluate_rule(
                rule or {},
                row.get(_table_column_key(source_column, source_index)),
                source_column,
            )
        )

    matched = any(results) if str(logic.get("match") or "all").lower() == "any" else all(results)
    return not matched if str(logic.get("action") or "show").lower() == "hide" else matched


def _table_progress(field: Dict[str, Any], value: Any, skipped: bool, system_managed: bool) -> Tuple[int, int]:
    rows = value.get("rows") if isinstance(value, dict) and isinstance(value.get("rows"), list) else []
    columns = ((field.get("tableConfig") or {}).get("columns")) or []
    total = completed = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        for index, column in enumerate(columns):
            if not _table_column_visible(column, row, columns):
                continue
            key = _table_column_key(column, index)
            cell = row.get(key)
            blank = _is_blank(cell, str(column.get("type") or "").lower())
            if (system_managed or (column.get("constraints") or {}).get("readonly")) and blank:
                continue
            total += 1
            if not skipped and not blank:
                completed += 1
    return total, completed


def calculate_overall_entry_progress(
    *,
    study_data: Dict[str, Any],
    data: Dict[str, Any],
    skipped_required_flags: Any,
    visit_index: int,
    group_index: int,
) -> Dict[str, Any]:
    selected_models = study_data.get("selectedModels") or []
    assignments = study_data.get("assignments") or []
    skips = skipped_required_flags if isinstance(skipped_required_flags, list) else []
    calculated_targets = _calculated_target_ids(study_data)
    field_lookup, values = _build_field_context(selected_models, data or {})
    total = completed = skipped = 0

    for section_index, section in enumerate(selected_models):
        if not _assigned(assignments, section_index, visit_index, group_index):
            continue
        fields = section.get("fields") or []
        for field_index, field in enumerate(fields):
            if not _field_visible(
                selected_models,
                field_lookup,
                values,
                section_index,
                field_index,
            ):
                continue

            value = values.get((section_index, field_index))
            is_skipped = bool(
                section_index < len(skips)
                and isinstance(skips[section_index], list)
                and field_index < len(skips[section_index])
                and skips[section_index][field_index]
            )
            if is_skipped:
                skipped += 1

            field_type = str(field.get("type") or "").lower()
            system_managed = bool((field.get("constraints") or {}).get("readonly")) or _is_calculated(
                field,
                calculated_targets,
            )
            blank = _is_blank(value, field_type)

            if field_type == "table":
                if system_managed and blank:
                    continue
                field_total, field_completed = _table_progress(
                    field,
                    value,
                    is_skipped,
                    system_managed,
                )
                total += field_total
                completed += field_completed
                continue

            if system_managed and blank:
                continue
            total += 1
            if not is_skipped and not blank:
                completed += 1

    percentage = int(math.floor((completed / total) * 100 + 0.5)) if total else 0
    if total <= 0 or completed <= 0:
        status = "none"
    elif skipped > 0:
        status = "skipped"
    elif percentage >= 100:
        status = "complete"
    else:
        status = "partial"

    return {
        "progress_status": status,
        "progress_percentage": percentage,
        "progress_completed": completed,
        "progress_total": total,
        "progress_skipped": skipped,
    }
