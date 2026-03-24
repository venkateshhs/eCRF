# tests/test_datalad_worker_smoke.py
import pytest
from pathlib import Path

from eCRF_backend.datalad_config import get_datalad_config
from eCRF_backend.datalad_worker import DataladWorker

pytest.importorskip("datalad")

from datalad.api import Dataset  # type: ignore


def test_worker_can_save(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("ECRF_DATALAD_MODE", "shadow")
    cfg = get_datalad_config()

    ds_path = tmp_path / "ds"
    Dataset(str(ds_path)).create(cfg_proc="text2git")

    logs = []
    w = DataladWorker(cfg, log=logs.append)
    w.start()
    (ds_path / "hello.txt").write_text("hi", encoding="utf-8")
    w.enqueue_save(ds_path, "test save")
    w._q.join()
    w.stop()

    assert any("Saved dataset" in x for x in logs)
