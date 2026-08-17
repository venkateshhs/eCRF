from __future__ import annotations

import csv
import json
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .datalad_repo import DataladStudyRepo


def _slug(value: Any, fallback: str) -> str:
    text = re.sub(r"[^A-Za-z0-9]+", "-", str(value or "").strip()).strip("-").lower()
    return text[:80] or fallback


def _display(obj: Dict[str, Any], fallback: str) -> str:
    for key in ("label", "title", "name", "short_name", "id"):
        value = str(obj.get(key) or "").strip()
        if value:
            return value
    return fallback


def _candidate_keys(obj: Dict[str, Any], index: int, prefix: str) -> List[str]:
    values = [obj.get("_id"), obj.get("id"), obj.get("name"), obj.get("key"), obj.get("label"), obj.get("title"), f"{prefix}{index}"]
    return [str(value).strip() for value in values if value is not None and str(value).strip()]


def _read_key(data: Dict[str, Any], candidates: Sequence[str]) -> Any:
    for key in candidates:
        if key in data:
            return data[key]
    normalized = {str(key).strip().lower(): key for key in data}
    for key in candidates:
        match = normalized.get(key.strip().lower())
        if match is not None:
            return data[match]
    return None


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, list):
        return "; ".join(_cell(item) for item in value)
    if isinstance(value, dict):
        for key in ("file_name", "name", "url", "file_path"):
            if value.get(key):
                return str(value[key])
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def _column_name(value: Any, fallback: str) -> str:
    text = re.sub(r"[^A-Za-z0-9]+", "_", str(value or "").strip()).strip("_").lower()
    if not text:
        text = fallback
    if text[0].isdigit():
        text = f"field_{text}"
    return text[:80]


def _bids_label(value: Any, fallback: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "", str(value or "").strip())[:64] or fallback


def _safe_export_filename(value: Any, fallback: str) -> str:
    name = Path(str(value or "")).name.strip()
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return name[:160] or fallback


def _field_catalog(schema: Dict[str, Any]) -> List[Tuple[int, int, Dict[str, Any], Dict[str, Any], str]]:
    output = []
    used: Dict[str, int] = {}
    for section_index, section in enumerate(schema.get("selectedModels") or []):
        section_name = _display(section, f"Section {section_index + 1}")
        for field_index, field in enumerate(section.get("fields") or []):
            field_name = field.get("name") or field.get("label") or field.get("title")
            base = _column_name(field_name, f"section_{section_index + 1}_field_{field_index + 1}")
            used[base] = used.get(base, 0) + 1
            column = base if used[base] == 1 else f"{base}_{used[base]}"
            output.append((section_index, field_index, section, field, column))
    return output


def _entry_values(entry: Dict[str, Any], catalog) -> Dict[str, str]:
    data = entry.get("data") or {}
    output: Dict[str, str] = {}
    for section_index, field_index, section, field, column in catalog:
        value = None
        if isinstance(data, list):
            section_data = data[section_index] if section_index < len(data) else []
            if isinstance(section_data, list) and field_index < len(section_data):
                value = section_data[field_index]
        elif isinstance(data, dict):
            section_data = _read_key(data, _candidate_keys(section, section_index, "s"))
            if isinstance(section_data, dict):
                value = _read_key(section_data, _candidate_keys(field, field_index, "f"))
        output[column] = _cell(value)
    return output


def _entry_field_value(
    entry: Dict[str, Any],
    section_index: int,
    field_index: int,
    section: Dict[str, Any],
    field: Dict[str, Any],
) -> Any:
    data = entry.get("data") or {}
    if isinstance(data, list):
        section_data = data[section_index] if section_index < len(data) else []
        if isinstance(section_data, list) and field_index < len(section_data):
            return section_data[field_index]
        return None
    if isinstance(data, dict):
        section_data = _read_key(data, _candidate_keys(section, section_index, "s"))
        if isinstance(section_data, dict):
            return _read_key(section_data, _candidate_keys(field, field_index, "f"))
    return None


def _stable_id(obj: Dict[str, Any]) -> str:
    return str(obj.get("_id") or obj.get("id") or obj.get("uuid") or "").strip()


_VERSIONED_CONSTRAINT_KEYS = {
    "required", "pattern", "min", "max", "minLength", "maxLength", "step",
    "allowMultiple", "dominantOptions", "integerOnly", "dateFormat", "minDate",
    "maxDate", "minTime", "maxTime", "hourCycle", "minDigits", "maxDigits",
}


def _normalized_options(options: Any) -> List[Any]:
    if not isinstance(options, list):
        return []
    normalized = []
    for option in options:
        if isinstance(option, dict):
            normalized.append({
                "value": option.get("value") or option.get("label") or option.get("name") or option.get("title"),
            })
        else:
            normalized.append(str(option))
    return normalized


def _structural_constraints(obj: Dict[str, Any]) -> Dict[str, Any]:
    constraints = obj.get("constraints") or {}
    return {key: constraints.get(key) for key in sorted(_VERSIONED_CONSTRAINT_KEYS) if key in constraints}


def _field_export_signature(field: Dict[str, Any]) -> str:
    """Return the form aspects that require separate data columns when changed."""
    field_type = str(field.get("type") or "").lower()
    signature: Dict[str, Any] = {
        "name": str(field.get("name") or field.get("key") or "").strip(),
        "type": field_type,
        "constraints": _structural_constraints(field),
    }
    if field_type in {"select", "radio", "checkbox"}:
        signature["options"] = _normalized_options(field.get("options") or [])
    if field_type == "table":
        config = field.get("tableConfig") or {}
        signature["table"] = {
            "mode": config.get("mode") or "2d",
            "initialRows": int(config.get("initialRows") or 1),
            "allowAddRows": bool(config.get("allowAddRows", True)),
            "columns": [{
                "id": _stable_id(column),
                "key": str(column.get("key") or column.get("name") or "").strip(),
                "type": str(column.get("type") or "").lower(),
                "options": _normalized_options(column.get("options") or []),
                "constraints": _structural_constraints(column),
            } for column in (config.get("columns") or []) if isinstance(column, dict)],
        }
    return json.dumps(signature, ensure_ascii=False, sort_keys=True, default=str)


def _table_rows(value: Any) -> List[Dict[str, Any]]:
    rows = value.get("rows") if isinstance(value, dict) else value
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _latest_entry_by_subject_visit_version(entries: Iterable[Dict[str, Any]]) -> Dict[Tuple[int, int, int], Dict[str, Any]]:
    latest: Dict[Tuple[int, int, int], Dict[str, Any]] = {}
    for row in entries:
        try:
            key = (int(row["subject_index"]), int(row["visit_index"]), int(row["form_version"]))
        except (KeyError, TypeError, ValueError):
            continue
        previous = latest.get(key)
        sort_key = (str(row.get("updated_at") or ""), str(row.get("created_at") or ""), int(row.get("id") or 0))
        previous_key = (
            str(previous.get("updated_at") or ""),
            str(previous.get("created_at") or ""),
            int(previous.get("id") or 0),
        ) if previous else None
        if previous is None or sort_key > previous_key:
            latest[key] = row
    return latest


def _combined_version_export(
    *,
    versions: Sequence[int],
    schemas_by_version: Dict[int, Dict[str, Any]],
    entries: Sequence[Dict[str, Any]],
    subjects: Sequence[Dict[str, Any]],
    visits: Sequence[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[str], Dict[str, Any]]:
    """Build one wide phenotype table with one row per participant and visit."""
    version_list = sorted(int(version) for version in versions)
    lineages: Dict[Tuple[str, ...], Dict[str, Any]] = {}
    lineage_order: List[Tuple[str, ...]] = []

    for version in version_list:
        schema = schemas_by_version.get(version) or {}
        for section_index, section in enumerate(schema.get("selectedModels") or []):
            for field_index, field in enumerate(section.get("fields") or []):
                field_id = _stable_id(field)
                key = ("id", field_id) if field_id else (
                    "legacy", str(version), str(section_index), str(field_index)
                )
                if key not in lineages:
                    lineages[key] = {"instances": {}}
                    lineage_order.append(key)
                lineages[key]["instances"][version] = (section_index, field_index, section, field)

    used_bases: Dict[str, int] = {}
    for key in lineage_order:
        lineage = lineages[key]
        latest_version = max(lineage["instances"])
        latest_field = lineage["instances"][latest_version][3]
        base = _column_name(
            latest_field.get("name") or latest_field.get("label") or latest_field.get("title"),
            "field",
        )
        used_bases[base] = used_bases.get(base, 0) + 1
        lineage["base"] = base if used_bases[base] == 1 else f"{base}_{used_bases[base]}"

    entry_index = _latest_entry_by_subject_visit_version(entries)
    descriptors: List[Dict[str, Any]] = []
    sidecar: Dict[str, Any] = {
        "MeasurementToolMetadata": {
            "Description": "case-e electronic case report form with selected study versions combined horizontally",
            "VersionsIncluded": version_list,
            "RowRule": "Exactly one row per participant_id and visit",
            "TableRowMatching": "Structurally changed tables use version snapshots; row positions are not matched across versions",
        },
        "visit": {"LongName": "Visit", "Description": "Human-readable study visit name"},
        "group": {"LongName": "Study group", "Description": "Current human-readable study group name"},
    }

    def add_descriptor(column: str, descriptor: Dict[str, Any], metadata: Dict[str, Any]) -> None:
        descriptors.append({"column": column, **descriptor})
        sidecar[column] = metadata

    for key in lineage_order:
        lineage = lineages[key]
        instances = lineage["instances"]
        base = lineage["base"]
        latest_instance = instances[max(instances)]
        latest_section, latest_field = latest_instance[2], latest_instance[3]
        field_id = _stable_id(latest_field) or None
        affected = (
            len(instances) != len(version_list)
            or len({_field_export_signature(instance[3]) for instance in instances.values()}) > 1
        )
        has_scalar = any(str(instance[3].get("type") or "").lower() != "table" for instance in instances.values())
        has_table = any(str(instance[3].get("type") or "").lower() == "table" for instance in instances.values())

        if has_scalar:
            scalar_instances = {
                version: instance for version, instance in instances.items()
                if str(instance[3].get("type") or "").lower() != "table"
            }
            latest_scalar_version = max(scalar_instances)
            latest_scalar_instance = scalar_instances[latest_scalar_version]
            if not affected:
                source_field = latest_scalar_instance[3]
                metadata = {
                    "LongName": _display(source_field, base),
                    "Description": str(source_field.get("description") or f"{_display(latest_section, 'Form')} — {_display(source_field, base)}"),
                    "StudyVersions": version_list,
                    "VersionedBecauseFormChanged": False,
                    "ValueSelection": "Latest available selected version",
                    "SourceFieldID": _stable_id(source_field) or field_id,
                    "SourceType": str(source_field.get("type") or ""),
                }
                constraints = source_field.get("constraints") or {}
                options = source_field.get("options") or constraints.get("options") or []
                if options:
                    metadata["Levels"] = {str(value): str(value) for value in options}
                add_descriptor(base, {
                    "kind": "scalar_common", "instances": scalar_instances,
                }, metadata)
            else:
                for version in version_list:
                    instance = scalar_instances.get(version)
                    available = instance is not None
                    source_field = instance[3] if available else latest_scalar_instance[3]
                    column = f"{base}__v{version:03d}"
                    metadata = {
                        "LongName": f"{_display(source_field, base)} — version {version}",
                        "Description": str(source_field.get("description") or f"{_display(latest_section, 'Form')} — {_display(source_field, base)}"),
                        "StudyVersion": version,
                        "VersionedBecauseFormChanged": True,
                        "FieldAvailableInVersion": available,
                        "SourceFieldID": _stable_id(source_field) or field_id,
                        "SourceType": str(source_field.get("type") or ""),
                    }
                    constraints = source_field.get("constraints") or {}
                    options = source_field.get("options") or constraints.get("options") or []
                    if options:
                        metadata["Levels"] = {str(value): str(value) for value in options}
                    add_descriptor(column, {
                        "kind": "scalar_versioned", "version": version,
                        "instance": instance,
                    }, metadata)

        if has_table:
            table_columns: Dict[Tuple[str, ...], Dict[str, Any]] = {}
            table_column_order: List[Tuple[str, ...]] = []
            max_rows = 1
            for version, instance in instances.items():
                section_index, field_index, section, field = instance
                if str(field.get("type") or "").lower() != "table":
                    continue
                for column_index, table_column in enumerate((field.get("tableConfig") or {}).get("columns") or []):
                    table_column_id = _stable_id(table_column)
                    natural_key = str(table_column.get("key") or table_column.get("name") or "").strip().lower()
                    column_key = (
                        ("id", table_column_id) if table_column_id
                        else ("natural", natural_key) if natural_key
                        else ("legacy", str(version), str(column_index))
                    )
                    if column_key not in table_columns:
                        table_columns[column_key] = {"instances": {}}
                        table_column_order.append(column_key)
                    table_columns[column_key]["instances"][version] = (column_index, table_column)
                for (subject_index, visit_index, entry_version), entry in entry_index.items():
                    if entry_version != version:
                        continue
                    value = _entry_field_value(entry, section_index, field_index, section, field)
                    max_rows = max(max_rows, len(_table_rows(value)))

            used_table_bases: Dict[str, int] = {}
            for column_key in table_column_order:
                table_lineage = table_columns[column_key]
                latest_column_version = max(table_lineage["instances"])
                latest_table_column = table_lineage["instances"][latest_column_version][1]
                table_base = _column_name(
                    latest_table_column.get("key") or latest_table_column.get("name") or latest_table_column.get("label"),
                    "column",
                )
                used_table_bases[table_base] = used_table_bases.get(table_base, 0) + 1
                if used_table_bases[table_base] > 1:
                    table_base = f"{table_base}_{used_table_bases[table_base]}"
                table_lineage["base"] = table_base

            table_instances = {
                version: instance for version, instance in instances.items()
                if str(instance[3].get("type") or "").lower() == "table"
            }
            if not affected:
                for row_index in range(max_rows):
                    for column_key in table_column_order:
                        table_lineage = table_columns[column_key]
                        source_column = table_lineage["instances"][max(table_lineage["instances"])][1]
                        column = f"{base}__row{row_index + 1:02d}__{table_lineage['base']}"
                        metadata = {
                            "LongName": f"{_display(latest_field, base)} — row {row_index + 1}, {_display(source_column, table_lineage['base'])}",
                            "Description": "Flattened repeating-table cell from the latest available selected version",
                            "StudyVersions": version_list,
                            "VersionedBecauseFormChanged": False,
                            "ValueSelection": "Latest available selected version",
                            "SourceFieldID": field_id,
                            "SourceType": str(source_column.get("type") or ""),
                            "TableRowNumber": row_index + 1,
                            "SourceTableColumnID": _stable_id(source_column) or None,
                        }
                        add_descriptor(column, {
                            "kind": "table_common", "instances": table_instances,
                            "table_columns": table_lineage["instances"],
                            "row_index": row_index,
                        }, metadata)
            else:
                for version in version_list:
                    field_instance = table_instances.get(version)
                    table_available = field_instance is not None
                    for row_index in range(max_rows):
                        for column_key in table_column_order:
                            table_lineage = table_columns[column_key]
                            table_column_instance = table_lineage["instances"].get(version)
                            available = bool(table_available and table_column_instance)
                            source_column = table_column_instance[1] if table_column_instance else table_lineage["instances"][max(table_lineage["instances"])][1]
                            column = f"{base}__v{version:03d}__row{row_index + 1:02d}__{table_lineage['base']}"
                            metadata = {
                                "LongName": f"{_display(latest_field, base)} — version {version}, row {row_index + 1}, {_display(source_column, table_lineage['base'])}",
                                "Description": "Flattened repeating-table cell from an independent version snapshot",
                                "StudyVersion": version,
                                "VersionedBecauseFormChanged": True,
                                "FieldAvailableInVersion": table_available,
                                "TableColumnAvailableInVersion": available,
                                "SourceFieldID": _stable_id(field_instance[3]) if field_instance else field_id,
                                "SourceType": str(source_column.get("type") or ""),
                                "TableRowNumber": row_index + 1,
                                "SourceTableColumnID": _stable_id(source_column) or None,
                            }
                            add_descriptor(column, {
                                "kind": "table_versioned", "version": version,
                                "instance": field_instance,
                                "table_column": table_column_instance,
                                "row_index": row_index,
                            }, metadata)

    row_keys = sorted({(subject, visit) for subject, visit, _version in entry_index})
    rows: List[Dict[str, Any]] = []
    for subject_index, visit_index in row_keys:
        subject = subjects[subject_index] if subject_index < len(subjects) else {}
        visit = visits[visit_index] if visit_index < len(visits) else {}
        subject_name = str(subject.get("id") or f"Subject {subject_index + 1}")
        visit_name = _display(visit, f"Visit {visit_index + 1}")
        group_name = str(subject.get("group") or "")
        row: Dict[str, Any] = {
            "participant_id": f"sub-{_bids_label(subject_name, f'{subject_index + 1:05d}')}",
            "visit": visit_name,
            "group": group_name,
        }
        for descriptor in descriptors:
            value: Any = None
            entry = None
            instance = None
            table_column_instance = None
            if descriptor["kind"].endswith("_common"):
                for version in reversed(version_list):
                    candidate_entry = entry_index.get((subject_index, visit_index, version))
                    candidate_instance = descriptor["instances"].get(version)
                    if candidate_entry is not None and candidate_instance is not None:
                        entry = candidate_entry
                        instance = candidate_instance
                        if descriptor["kind"] == "table_common":
                            table_column_instance = descriptor["table_columns"].get(version)
                        break
            else:
                entry = entry_index.get((subject_index, visit_index, descriptor["version"]))
                instance = descriptor.get("instance")
                table_column_instance = descriptor.get("table_column")
            if entry is not None and instance is not None:
                section_index, field_index, section, field = instance
                value = _entry_field_value(entry, section_index, field_index, section, field)
                if descriptor["kind"].startswith("table_"):
                    table_rows = _table_rows(value)
                    row_index = descriptor["row_index"]
                    value = None
                    if row_index < len(table_rows) and table_column_instance:
                        column_index, table_column = table_column_instance
                        value = _read_key(table_rows[row_index], _candidate_keys(table_column, column_index, "column_"))
            row[descriptor["column"]] = _cell(value) if value is not None else "n/a"
        rows.append(row)

    columns = ["participant_id", "visit", "group"] + [descriptor["column"] for descriptor in descriptors]
    return rows, columns, sidecar


def _latest_by_slot(entries: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    latest: Dict[Tuple[int, int, int, int], Dict[str, Any]] = {}
    for row in entries:
        try:
            key = (int(row["subject_index"]), int(row["visit_index"]), int(row["group_index"]), int(row["form_version"]))
        except (KeyError, TypeError, ValueError):
            continue
        previous = latest.get(key)
        sort_key = (str(row.get("updated_at") or ""), str(row.get("created_at") or ""), int(row.get("id") or 0))
        previous_key = (str(previous.get("updated_at") or ""), str(previous.get("created_at") or ""), int(previous.get("id") or 0)) if previous else None
        if previous is None or sort_key > previous_key:
            latest[key] = row
    return sorted(latest.values(), key=lambda row: (int(row.get("form_version") or 0), int(row.get("subject_index") or 0), int(row.get("visit_index") or 0)))


def _write_tsv(path: Path, rows: List[Dict[str, Any]], columns: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), delimiter="\t", extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _read_jsonl(paths: Iterable[Path]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for path in paths:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


@dataclass
class ExportOptions:
    versions: Optional[Set[int]] = None
    subject_indexes: Optional[Set[int]] = None
    group_indexes: Optional[Set[int]] = None
    visit_indexes: Optional[Set[int]] = None
    include_data: bool = True
    include_template: bool = True
    include_files: bool = True
    file_scope: str = "all"
    include_audit: bool = False
    audit_only: bool = False
    include_subject_folders: bool = False


def build_analysis_export(
    *,
    repo: DataladStudyRepo,
    study_id: int,
    study_name: str,
    study_data: Dict[str, Any],
    schemas_by_version: Dict[int, Dict[str, Any]],
    options: ExportOptions,
) -> Tuple[Path, str]:
    """Build a human-labelled, analysis-ready BIDS ZIP."""
    paths = repo.paths(study_id, study_name)
    tmp_dir = Path(tempfile.mkdtemp(prefix=f"casee_export_{study_id}_"))
    root_name = f"study-{study_id}-{_slug(study_name, 'study')}_bids-export"
    root = tmp_dir / root_name
    root.mkdir(parents=True)

    subjects = study_data.get("subjects") or []
    visits = study_data.get("visits") or []
    groups = study_data.get("groups") or []
    versions = sorted(options.versions or set(schemas_by_version))

    def selected(row: Dict[str, Any]) -> bool:
        try:
            subject = int(row.get("subject_index"))
            visit = int(row.get("visit_index"))
            group = int(row.get("group_index"))
            version = int(row.get("form_version"))
        except (TypeError, ValueError):
            return False
        return (
            version in versions
            and (options.subject_indexes is None or subject in options.subject_indexes)
            and (options.visit_indexes is None or visit in options.visit_indexes)
            and (options.group_indexes is None or group in options.group_indexes)
        )

    dataset_description = {
        "Name": study_name,
        "BIDSVersion": "1.10.0",
        "DatasetType": "raw",
        "GeneratedBy": [{"Name": "case-e", "Description": "Human-labelled eCRF analysis export"}],
    }
    (root / "dataset_description.json").write_text(json.dumps(dataset_description, indent=2), encoding="utf-8")
    (root / "CHANGES").write_text("1.0.0 Exported from case-e\n", encoding="utf-8")
    (root / "README").write_text(
        "case-e BIDS analysis export\n\nField and structure UUIDs are replaced by human-readable labels in all TSV data files.\n"
        "The template JSON is retained separately when requested so the original study definition remains reproducible.\n"
        + (
            "\nSelected study versions are combined in phenotype/ecrf.tsv. Each participant and visit appears once. "
            "Unchanged fields remain single columns; only fields affected by a form change expand using __vNNN suffixes. "
            "Repeating tables use __rowNN columns and become versioned only when their structure changes.\n"
            if len(versions) > 1 else ""
        ),
        encoding="utf-8",
    )

    participant_rows = []
    for index, subject in enumerate(subjects):
        if options.subject_indexes is not None and index not in options.subject_indexes:
            continue
        group_name = str(subject.get("group") or "")
        group_index = next(
            (group_idx for group_idx, group in enumerate(groups) if _display(group, "").strip().lower() == group_name.strip().lower()),
            None,
        )
        if options.group_indexes is not None and group_index not in options.group_indexes:
            continue
        participant_rows.append({
            "participant_id": f"sub-{_bids_label(subject.get('id'), f'{index + 1:05d}')}",
            "group": group_name,
        })
    _write_tsv(root / "participants.tsv", participant_rows, ["participant_id", "group"])
    (root / "participants.json").write_text(json.dumps({
        "group": {"Description": "Study group display name"},
    }, indent=2), encoding="utf-8")

    entries = [row for row in _latest_by_slot(repo.list_entries(study_id, study_name)) if selected(row)]
    if options.include_data and not options.audit_only and len(versions) > 1:
        rows, columns, sidecar = _combined_version_export(
            versions=versions,
            schemas_by_version=schemas_by_version,
            entries=entries,
            subjects=subjects,
            visits=visits,
        )
        _write_tsv(root / "phenotype" / "ecrf.tsv", rows, columns)
        (root / "phenotype" / "ecrf.json").write_text(
            json.dumps(sidecar, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        if options.include_subject_folders:
            for row in rows:
                participant_id = row["participant_id"]
                visit_name = row["visit"]
                session_id = f"ses-{_bids_label(visit_name, '01')}"
                subject_name = f"{participant_id}_{session_id}_ecrf"
                subject_dir = root / "sourcedata" / participant_id / session_id / "ecrf"
                _write_tsv(subject_dir / f"{subject_name}.tsv", [row], columns)
                (subject_dir / f"{subject_name}.json").write_text(
                    json.dumps(sidecar, ensure_ascii=False, indent=2), encoding="utf-8"
                )
    elif options.include_data and not options.audit_only:
        for version in versions:
            schema = schemas_by_version.get(version) or study_data
            catalog = _field_catalog(schema)
            columns = ["participant_id", "visit", "group", "study_version"] + [item[4] for item in catalog]
            sidecar = {
                "MeasurementToolMetadata": {
                    "Description": f"case-e electronic case report form, study template version {version}"
                },
                "visit": {"LongName": "Visit", "Description": "Human-readable study visit name"},
                "group": {"LongName": "Study group", "Description": "Human-readable study group name"},
                "study_version": {"LongName": "Study template version", "Description": "case-e template version used for this entry"},
            }
            for _, _, section, field, column in catalog:
                metadata = {
                    "LongName": _display(field, column),
                    "Description": str(field.get("description") or f"{_display(section, 'Form')} — {_display(field, column)}"),
                }
                constraints = field.get("constraints") or {}
                if field.get("options") or constraints.get("options"):
                    metadata["Levels"] = {str(value): str(value) for value in (field.get("options") or constraints.get("options") or [])}
                sidecar[column] = metadata
            rows = []
            for entry in entries:
                if int(entry.get("form_version") or 0) != version:
                    continue
                subject_index = int(entry.get("subject_index") or 0)
                visit_index = int(entry.get("visit_index") or 0)
                group_index = int(entry.get("group_index") or 0)
                subject = subjects[subject_index] if subject_index < len(subjects) else {}
                visit = visits[visit_index] if visit_index < len(visits) else {}
                group = groups[group_index] if group_index < len(groups) else {}
                subject_name = str(subject.get("id") or f"Subject {subject_index + 1}")
                visit_name = _display(visit, f"Visit {visit_index + 1}")
                group_name = _display(group, str(subject.get("group") or f"Group {group_index + 1}"))
                row = {
                    "participant_id": f"sub-{_bids_label(subject_name, f'{subject_index + 1:05d}')}",
                    "visit": visit_name,
                    "group": group_name,
                    "study_version": version,
                    **_entry_values(entry, catalog),
                }
                rows.append(row)
                if options.include_subject_folders:
                    participant_id = row["participant_id"]
                    session_id = f"ses-{_bids_label(visit_name, f'{visit_index + 1:02d}') }"
                    subject_name = f"{participant_id}_{session_id}_version-{version:03d}_ecrf"
                    subject_dir = root / "sourcedata" / participant_id / session_id / "ecrf"
                    _write_tsv(subject_dir / f"{subject_name}.tsv", [row], columns)
                    (subject_dir / f"{subject_name}.json").write_text(
                        json.dumps(sidecar, ensure_ascii=False, indent=2), encoding="utf-8"
                    )
            phenotype_name = f"ecrf_version_{version:03d}"
            _write_tsv(root / "phenotype" / f"{phenotype_name}.tsv", rows, columns)
            (root / "phenotype" / f"{phenotype_name}.json").write_text(
                json.dumps(sidecar, ensure_ascii=False, indent=2), encoding="utf-8"
            )

    if options.include_template and not options.audit_only:
        for version in versions:
            schema = schemas_by_version.get(version)
            if schema is not None:
                target = root / "code" / f"study-template_version-{version}.json"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")

    if options.include_files and not options.audit_only:
        manifest = []
        for record in repo.list_files(study_id, study_name):
            subject_index = record.get("subject_index")
            is_study_file = subject_index is None
            if record.get("form_version") is not None and int(record["form_version"]) not in versions:
                continue
            if options.file_scope == "study" and not is_study_file:
                continue
            if options.file_scope == "subject" and is_study_file:
                continue
            if not is_study_file and options.subject_indexes is not None and int(subject_index) not in options.subject_indexes:
                continue
            if record.get("visit_index") is not None and options.visit_indexes is not None and int(record["visit_index"]) not in options.visit_indexes:
                continue
            if record.get("group_index") is not None and options.group_indexes is not None and int(record["group_index"]) not in options.group_indexes:
                continue
            item = dict(record)
            if str(record.get("storage_option") or "").lower() != "url" and record.get("file_path"):
                source = (paths.dataset_path / str(record["file_path"])).resolve()
                try:
                    source.relative_to(paths.dataset_path.resolve())
                except ValueError:
                    source = Path()
                if source.is_file():
                    if is_study_file:
                        file_dir = root / "sourcedata" / "study"
                    else:
                        subject_number = int(subject_index)
                        participant_id = f"sub-{_bids_label(subjects[subject_number].get('id') if subject_number < len(subjects) else subject_number, str(subject_number))}"
                        file_dir = root / "sourcedata" / participant_id
                        if options.include_subject_folders and record.get("visit_index") is not None:
                            visit_number = int(record["visit_index"])
                            visit = visits[visit_number] if visit_number < len(visits) else {}
                            visit_name = _display(visit, f"Visit {visit_number + 1}")
                            file_dir = file_dir / f"ses-{_bids_label(visit_name, f'{visit_number + 1:02d}') }"
                    modalities = record.get("modalities") or []
                    if isinstance(modalities, str):
                        modalities = [modalities]
                    modality = _slug(modalities[0] if modalities else "misc", "misc")
                    file_dir = file_dir / modality
                    filename = _safe_export_filename(record.get("file_name"), f"file-{record.get('id')}")
                    target = file_dir / f"file-{record.get('id')}_{filename}"
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
                    item["export_path"] = str(target.relative_to(root))
            manifest.append(item)
        manifest_path = root / "sourcedata" / "files_manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    if options.include_audit or options.audit_only:
        audit_paths = [paths.audit_system_study_dir / "events.jsonl"]
        if paths.audit_subject_dir.exists():
            for subject_dir in paths.audit_subject_dir.glob("subject_*"):
                match = re.match(r"subject_(\d+)", subject_dir.name)
                if options.subject_indexes is not None and (not match or int(match.group(1)) not in options.subject_indexes):
                    continue
                audit_paths.append(subject_dir / "events.jsonl")
        audit_rows = _read_jsonl(audit_paths)
        audit_target = root / "sourcedata" / "case-e" / "audit_log.jsonl"
        audit_target.parent.mkdir(parents=True, exist_ok=True)
        audit_target.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in audit_rows), encoding="utf-8")

    archive = shutil.make_archive(str(tmp_dir / root_name), "zip", root_dir=str(tmp_dir), base_dir=root_name)
    return Path(archive), f"{root_name}.zip"
