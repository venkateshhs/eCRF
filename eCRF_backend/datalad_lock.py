# eCRF_backend/datalad_lock.py
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional

from filelock import FileLock, Timeout


@dataclass(frozen=True)
class LockSpec:
    dataset_path: Path
    name: str = "dataset"
    timeout_s: float = 120.0


def _lockfile_path(dataset_path: Path, name: str) -> Path:
    # Keep lock file outside .git to avoid accidental staging
    return dataset_path / f".casee.{name}.lock"


@contextmanager
def dataset_lock(spec: LockSpec) -> Iterator[None]:
    spec.dataset_path.mkdir(parents=True, exist_ok=True)
    lock_path = _lockfile_path(spec.dataset_path, spec.name)
    lock = FileLock(str(lock_path))
    try:
        lock.acquire(timeout=spec.timeout_s)
        yield
    except Timeout as e:
        raise RuntimeError(f"Timeout acquiring lock: {lock_path}") from e
    finally:
        try:
            lock.release()
        except Exception:
            # best effort
            pass
