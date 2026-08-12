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
