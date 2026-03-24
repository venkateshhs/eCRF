# tests/test_datalad_store_snapshot.py
from pathlib import Path

from eCRF_backend.datalad_store import _study_slug_path


def test_dataset_path_is_stable_for_id(monkeypatch, tmp_path: Path):
    # We only test it returns a Path; actual layout is tested in integration
    p = _study_slug_path(12, "My Study")
    assert isinstance(p, Path)
