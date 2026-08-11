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
    include_files: bool = False
    file_scope: str = "all"
    include_audit: bool = False
    audit_only: bool = False


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
        "The template JSON is retained separately when requested so the original study definition remains reproducible.\n",
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
    if options.include_data and not options.audit_only:
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
                    scope = "study" if is_study_file else f"sub-{_bids_label(subjects[int(subject_index)].get('id') if int(subject_index) < len(subjects) else subject_index, str(subject_index))}"
                    filename = _safe_export_filename(record.get("file_name"), f"file-{record.get('id')}")
                    target = root / "sourcedata" / scope / f"file-{record.get('id')}_{filename}"
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
