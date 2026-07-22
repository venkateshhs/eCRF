from types import SimpleNamespace

from eCRF_backend import datalad_config
from eCRF_backend.datalad_repo import DataladStudyRepo
from eCRF_backend.settings import _detect_profile


def test_profile_is_local_by_default(monkeypatch):
    monkeypatch.delenv("ECRF_PROFILE", raising=False)
    monkeypatch.delenv("ECRF_DATALAD_RIA_URL", raising=False)
    monkeypatch.delenv("ECRF_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    assert _detect_profile("development") == "local"


def test_profile_is_server_for_hosted_signals(monkeypatch):
    monkeypatch.delenv("ECRF_PROFILE", raising=False)
    monkeypatch.setenv("ECRF_DATABASE_URL", "postgresql://casee@db/casee")

    assert _detect_profile("development") == "server"


def test_datalad_mode_defaults_from_profile(monkeypatch):
    monkeypatch.delenv("ECRF_DATALAD_MODE", raising=False)
    monkeypatch.setattr(
        datalad_config,
        "get_settings",
        lambda: SimpleNamespace(is_local_profile=True, is_production=False),
    )
    assert datalad_config.get_datalad_config().mode == "off"

    monkeypatch.setattr(
        datalad_config,
        "get_settings",
        lambda: SimpleNamespace(is_local_profile=False, is_production=True),
    )
    monkeypatch.setenv("ECRF_DATALAD_REQUIRE_RIA_FOR_WRITES", "0")
    assert datalad_config.get_datalad_config().mode == "primary"


def test_filesystem_mode_writes_canonical_study_without_datalad(tmp_path, monkeypatch):
    repo = DataladStudyRepo(root=str(tmp_path))
    monkeypatch.setattr(repo, "_cfg", lambda: SimpleNamespace(mode="off"))

    result = repo.create_or_replace_published_snapshot(
        study_id=7,
        study_name="Local study",
        study_description="filesystem only",
        study_data={"subjects": [{"id": "SUB-001"}]},
        template_schema={"version": 1, "sections": []},
        created_by=1,
        status="PUBLISHED",
    )

    dataset_path = tmp_path / "study_7_Local_study"
    assert result["version"] == 1
    assert (dataset_path / "canonical" / "study_metadata.json").is_file()
    assert (dataset_path / "canonical" / "study_content.json").is_file()
    assert not (dataset_path / ".datalad").exists()
    assert not (dataset_path / ".git").exists()
