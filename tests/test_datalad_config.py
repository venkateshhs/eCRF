# tests/test_datalad_config.py

from eCRF_backend.datalad_config import get_datalad_config, is_study_primary


def test_parse_primary_ids(monkeypatch):
    monkeypatch.setenv("ECRF_DATALAD_MODE", "primary")
    monkeypatch.setenv("ECRF_DATALAD_PRIMARY_STUDY_IDS", "1, 2,foo,003")
    cfg = get_datalad_config()
    assert cfg.mode == "primary"
    assert cfg.primary_study_ids == {1, 2, 3}
    assert is_study_primary(cfg, 2) is True
    assert is_study_primary(cfg, 9) is False
