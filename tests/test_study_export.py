import json
import zipfile
from pathlib import Path
from types import SimpleNamespace

from eCRF_backend.study_export import ExportOptions, build_analysis_export


class FakeRepo:
    def __init__(self, root: Path):
        self.root = root
        self.dataset = root / "dataset"
        self.audit_study = self.dataset / "canonical" / "audit" / "system" / "study"
        self.audit_subject = self.dataset / "canonical" / "audit" / "subject"
        self.dataset.mkdir(parents=True)
        self.uploaded_file = self.dataset / "canonical" / "files" / "heart-scan.txt"
        self.uploaded_file.parent.mkdir(parents=True)
        self.uploaded_file.write_text("scan payload", encoding="utf-8")
        self.study_file = self.dataset / "canonical" / "files" / "protocol.pdf"
        self.study_file.write_text("study protocol", encoding="utf-8")

    def paths(self, study_id, study_name):
        return SimpleNamespace(
            dataset_path=self.dataset,
            audit_system_study_dir=self.audit_study,
            audit_subject_dir=self.audit_subject,
        )

    def list_entries(self, study_id, study_name):
        return [
            {
                "id": 1,
                "subject_index": 0,
                "visit_index": 0,
                "group_index": 0,
                "form_version": 2,
                "updated_at": "2026-01-01T00:00:00Z",
                "data": {"a-section-uuid": {"a-field-uuid": 72}},
            },
            {
                "id": 2,
                "subject_index": 1,
                "visit_index": 0,
                "group_index": 1,
                "form_version": 2,
                "updated_at": "2026-01-01T00:00:00Z",
                "data": {"a-section-uuid": {"a-field-uuid": 65}},
            },
        ]

    def list_files(self, study_id, study_name):
        return [{
            "id": 7,
            "study_id": study_id,
            "file_name": "heart-scan.txt",
            "file_path": "canonical/files/heart-scan.txt",
            "storage_option": "bids",
            "subject_index": 0,
            "visit_index": 0,
            "group_index": 0,
            "modalities": ["imaging"],
            "form_version": 2,
        }, {
            "id": 8,
            "study_id": study_id,
            "file_name": "protocol.pdf",
            "file_path": "canonical/files/protocol.pdf",
            "storage_option": "bids",
            "subject_index": None,
            "visit_index": None,
            "group_index": None,
            "modalities": ["documents"],
            "form_version": 2,
        }]


def _schema():
    return {
        "subjects": [{"id": "SUBJ-A", "group": "Control"}, {"id": "SUBJ-B", "group": "Treatment"}],
        "visits": [{"name": "Baseline"}],
        "groups": [{"name": "Control"}, {"name": "Treatment"}],
        "selectedModels": [{
            "_id": "a-section-uuid",
            "title": "Vitals",
            "fields": [{"_id": "a-field-uuid", "name": "heart_rate", "label": "Heart rate", "type": "number"}],
        }],
    }


def test_bids_export_has_required_root_files_and_human_columns(tmp_path):
    repo = FakeRepo(tmp_path)
    archive, _ = build_analysis_export(
        repo=repo,
        study_id=4,
        study_name="Heart Study",
        study_data=_schema(),
        schemas_by_version={2: _schema()},
        options=ExportOptions(versions={2}),
    )

    with zipfile.ZipFile(archive) as bundle:
        root = "study-4-heart-study_bids-export/"
        names = set(bundle.namelist())
        assert root + "dataset_description.json" in names
        assert root + "participants.tsv" in names
        assert root + "phenotype/ecrf_version_002.tsv" in names
        assert root + "sourcedata/sub-SUBJA/imaging/file-7_heart-scan.txt" in names
        assert root + "sourcedata/study/documents/file-8_protocol.pdf" in names
        assert root + "sourcedata/files_manifest.json" in names
        description = json.loads(bundle.read(root + "dataset_description.json"))
        assert description["DatasetType"] == "raw"
        table = bundle.read(root + "phenotype/ecrf_version_002.tsv").decode()
        participants = bundle.read(root + "participants.tsv").decode()
        assert "heart_rate" in table
        assert "a-field-uuid" not in table
        assert "sub-SUBJA" in table
        assert "subject_name" not in table.splitlines()[0]
        assert participants.splitlines()[0] == "participant_id\tgroup"
        assert bundle.read(root + "sourcedata/sub-SUBJA/imaging/file-7_heart-scan.txt").decode() == "scan payload"
        assert bundle.read(root + "sourcedata/study/documents/file-8_protocol.pdf").decode() == "study protocol"


def test_subject_scope_filters_participants_and_entries(tmp_path):
    repo = FakeRepo(tmp_path)
    archive, _ = build_analysis_export(
        repo=repo,
        study_id=4,
        study_name="Heart Study",
        study_data=_schema(),
        schemas_by_version={2: _schema()},
        options=ExportOptions(versions={2}, subject_indexes={1}, include_audit=True),
    )

    with zipfile.ZipFile(archive) as bundle:
        root = "study-4-heart-study_bids-export/"
        participants = bundle.read(root + "participants.tsv").decode()
        table = bundle.read(root + "phenotype/ecrf_version_002.tsv").decode()
        assert "sub-SUBJB" in participants and "sub-SUBJA" not in participants
        assert "sub-SUBJB" in table and "sub-SUBJA" not in table
        assert root + "sourcedata/case-e/audit_log.jsonl" in bundle.namelist()


def test_individual_subject_folders_group_visit_data_and_modality_files(tmp_path):
    repo = FakeRepo(tmp_path)
    archive, _ = build_analysis_export(
        repo=repo,
        study_id=4,
        study_name="Heart Study",
        study_data=_schema(),
        schemas_by_version={2: _schema()},
        options=ExportOptions(
            versions={2},
            include_files=True,
            include_subject_folders=True,
        ),
    )

    with zipfile.ZipFile(archive) as bundle:
        root = "study-4-heart-study_bids-export/"
        subject_visit = root + "sourcedata/sub-SUBJA/ses-Baseline/"
        names = set(bundle.namelist())
        subject_tsv = subject_visit + "ecrf/sub-SUBJA_ses-Baseline_version-002_ecrf.tsv"
        subject_json = subject_visit + "ecrf/sub-SUBJA_ses-Baseline_version-002_ecrf.json"
        subject_file = subject_visit + "imaging/file-7_heart-scan.txt"
        assert subject_tsv in names
        assert subject_json in names
        assert subject_file in names
        assert "heart_rate" in bundle.read(subject_tsv).decode()
        assert bundle.read(subject_file).decode() == "scan payload"


class MultiVersionRepo(FakeRepo):
    def list_entries(self, study_id, study_name):
        return [
            {
                "id": 11,
                "subject_index": 0,
                "visit_index": 0,
                "group_index": 0,
                "form_version": 1,
                "updated_at": "2026-01-01T00:00:00Z",
                "data": {
                    "section-vitals": {
                        "field-heart-rate": 72,
                        "field-site-code": "Earlier value",
                        "field-old-score": 8,
                        "field-medications": {"rows": [
                            {"table-drug": "Drug A", "table-dose": "5 mg"},
                        ]},
                    },
                },
            },
            {
                "id": 12,
                "subject_index": 0,
                "visit_index": 0,
                "group_index": 0,
                "form_version": 2,
                "updated_at": "2026-02-01T00:00:00Z",
                "data": {
                    "section-vitals": {
                        "field-heart-rate": 75,
                        "field-site-code": "Latest value",
                        "field-new-measure": 98,
                        "field-medications": {"rows": [
                            {"table-drug": "Drug A", "table-dose": "10 mg"},
                            {"table-drug": "Drug B", "table-dose": "2 mg"},
                        ]},
                    },
                },
            },
        ]


def _versioned_schema(version):
    fields = [{
        "_id": "field-heart-rate",
        "name": "heart_rate" if version == 1 else "pulse_rate",
        "label": "Heart rate" if version == 1 else "Pulse rate",
        "type": "number",
    }, {
        "_id": "field-site-code",
        "name": "site_code",
        "label": "Site code",
        "type": "text",
    }]
    if version == 1:
        fields.append({"_id": "field-old-score", "name": "old_score", "label": "Old score", "type": "number"})
    else:
        fields.append({"_id": "field-new-measure", "name": "new_measure", "label": "New measure", "type": "number"})
    fields.append({
        "_id": "field-medications",
        "name": "medications",
        "label": "Medications",
        "type": "table",
        "tableConfig": {"columns": [
            {"id": "table-drug", "key": "drug", "label": "Drug", "type": "text"},
            {"id": "table-dose", "key": "dose", "label": "Dose", "type": "text"},
        ]},
    })
    return {
        "subjects": [{"id": "SUBJ-A", "group": "Control"}],
        "visits": [{"name": "Baseline"}],
        "groups": [{"name": "Control"}],
        "selectedModels": [{"_id": "section-vitals", "title": "Vitals", "fields": fields}],
    }


def test_all_versions_only_expand_fields_affected_by_form_changes(tmp_path):
    repo = MultiVersionRepo(tmp_path)
    schema_v1 = _versioned_schema(1)
    schema_v2 = _versioned_schema(2)
    archive, _ = build_analysis_export(
        repo=repo,
        study_id=4,
        study_name="Heart Study",
        study_data=schema_v2,
        schemas_by_version={1: schema_v1, 2: schema_v2},
        options=ExportOptions(versions={1, 2}, include_subject_folders=True),
    )

    with zipfile.ZipFile(archive) as bundle:
        root = "study-4-heart-study_bids-export/"
        names = set(bundle.namelist())
        combined_tsv = root + "phenotype/ecrf.tsv"
        combined_json = root + "phenotype/ecrf.json"
        assert combined_tsv in names
        assert combined_json in names
        assert root + "phenotype/ecrf_version_001.tsv" not in names
        assert root + "phenotype/ecrf_version_002.tsv" not in names

        lines = bundle.read(combined_tsv).decode().splitlines()
        assert len(lines) == 2
        headers = lines[0].split("\t")
        values = dict(zip(headers, lines[1].split("\t")))
        assert headers[:3] == ["participant_id", "visit", "group"]
        assert "study_version" not in headers
        assert values["site_code"] == "Latest value"
        assert "site_code__v001" not in headers
        assert "site_code__v002" not in headers
        assert values["pulse_rate__v001"] == "72"
        assert values["pulse_rate__v002"] == "75"
        assert values["old_score__v001"] == "8"
        assert "old_score__v002" not in headers
        assert "new_measure__v001" not in headers
        assert values["new_measure__v002"] == "98"
        assert values["medications__row01__dose"] == "10 mg"
        assert values["medications__row02__drug"] == "Drug B"
        assert values["medications__row02__dose"] == "2 mg"
        assert not any(header.startswith("medications__v") for header in headers)

        sidecar = json.loads(bundle.read(combined_json))
        assert sidecar["new_measure__v002"]["FieldAvailableInVersion"] is True
        assert "new_measure__v001" not in sidecar
        assert sidecar["MeasurementToolMetadata"]["VersionsIncluded"] == [1, 2]

        subject_tsv = root + "sourcedata/sub-SUBJA/ses-Baseline/ecrf/sub-SUBJA_ses-Baseline_ecrf.tsv"
        assert subject_tsv in names
        assert bundle.read(subject_tsv).decode() == bundle.read(combined_tsv).decode()


def test_only_removed_notes_gets_version_columns_when_everything_else_is_unchanged(tmp_path):
    class NotesRemovedRepo(FakeRepo):
        def list_entries(self, study_id, study_name):
            return [{
                "id": 21,
                "subject_index": 0,
                "visit_index": 0,
                "group_index": 0,
                "form_version": 1,
                "updated_at": "2026-01-01T00:00:00Z",
                "data": {"section": {"temperature": 36.5, "notes": "Initial note"}},
            }, {
                "id": 22,
                "subject_index": 0,
                "visit_index": 0,
                "group_index": 0,
                "form_version": 2,
                "updated_at": "2026-02-01T00:00:00Z",
                "data": {"section": {"temperature": 36.7, "notes": "Initial note"}},
            }]

    common = {"_id": "temperature", "name": "temperature", "label": "Temperature", "type": "number"}
    notes = {"_id": "notes", "name": "notes", "label": "Notes", "type": "textarea"}

    def schema(fields):
        return {
            "subjects": [{"id": "SUBJ-A", "group": "Control"}],
            "visits": [{"name": "Baseline"}],
            "groups": [{"name": "Control"}],
            "selectedModels": [{"_id": "section", "title": "Assessment", "fields": fields}],
        }

    schema_v1 = schema([common, notes])
    schema_v2 = schema([common])
    archive, _ = build_analysis_export(
        repo=NotesRemovedRepo(tmp_path),
        study_id=4,
        study_name="Notes Removed Study",
        study_data=schema_v2,
        schemas_by_version={1: schema_v1, 2: schema_v2},
        options=ExportOptions(versions={1, 2}, include_files=False),
    )

    with zipfile.ZipFile(archive) as bundle:
        root = "study-4-notes-removed-study_bids-export/"
        lines = bundle.read(root + "phenotype/ecrf.tsv").decode().splitlines()
        headers = lines[0].split("\t")
        values = dict(zip(headers, lines[1].split("\t")))
        assert headers == ["participant_id", "visit", "group", "temperature", "notes__v001"]
        assert values["temperature"] == "36.7"
        assert values["notes__v001"] == "Initial note"
        assert "notes__v002" not in headers


def test_added_unentered_field_uses_label_and_only_emits_empty_actual_version(tmp_path):
    class AddedFieldRepo(FakeRepo):
        def list_entries(self, study_id, study_name):
            return [{
                "id": 31,
                "subject_index": 0,
                "visit_index": 0,
                "group_index": 0,
                "form_version": 3,
                "updated_at": "2026-03-01T00:00:00Z",
                "data": {"section": {}},
            }]

    def schema(fields):
        return {
            "subjects": [{"id": "SUBJ-A", "group": "Control"}],
            "visits": [{"name": "Baseline"}],
            "groups": [{"name": "Control"}],
            "selectedModels": [{"_id": "section", "title": "Assessment", "fields": fields}],
        }

    added = {
        "_id": "age-at-assessment",
        "name": "number_2_1787209163717",
        "label": "Age as of assessment date",
        "type": "number",
    }
    archive, _ = build_analysis_export(
        repo=AddedFieldRepo(tmp_path),
        study_id=4,
        study_name="Added Field Study",
        study_data=schema([added]),
        schemas_by_version={1: schema([]), 2: schema([]), 3: schema([added])},
        options=ExportOptions(versions={1, 2, 3}, include_files=False),
    )

    with zipfile.ZipFile(archive) as bundle:
        root = "study-4-added-field-study_bids-export/"
        lines = bundle.read(root + "phenotype/ecrf.tsv").decode().splitlines()
        headers = lines[0].split("\t")
        values = dict(zip(headers, lines[1].split("\t")))
        expected = "age_as_of_assessment_date__v003"
        assert headers == ["participant_id", "visit", "group", expected]
        assert values[expected] == ""
        assert not any(header.startswith("number_2_1787209163717") for header in headers)

        sidecar = json.loads(bundle.read(root + "phenotype/ecrf.json"))
        assert sidecar[expected]["LongName"] == "Age as of assessment date — version 3"
        assert sidecar[expected]["StudyVersion"] == 3
