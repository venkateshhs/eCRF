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
        return []


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
        description = json.loads(bundle.read(root + "dataset_description.json"))
        assert description["DatasetType"] == "raw"
        table = bundle.read(root + "phenotype/ecrf_version_002.tsv").decode()
        participants = bundle.read(root + "participants.tsv").decode()
        assert "heart_rate" in table
        assert "a-field-uuid" not in table
        assert "sub-SUBJA" in table
        assert "subject_name" not in table.splitlines()[0]
        assert participants.splitlines()[0] == "participant_id\tgroup"


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
