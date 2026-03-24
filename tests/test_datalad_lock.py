# tests/test_datalad_lock.py
from pathlib import Path
import threading
import time

from eCRF_backend.datalad_lock import LockSpec, dataset_lock


def test_dataset_lock_serialises(tmp_path: Path):
    ds = tmp_path / "ds"
    order = []

    def worker(tag: str):
        with dataset_lock(LockSpec(dataset_path=ds, timeout_s=2)):
            order.append(tag)
            time.sleep(0.2)

    t1 = threading.Thread(target=worker, args=("a",))
    t2 = threading.Thread(target=worker, args=("b",))
    t1.start(); t2.start()
    t1.join(); t2.join()

    assert order == ["a", "b"] or order == ["b", "a"]
    assert len(order) == 2
