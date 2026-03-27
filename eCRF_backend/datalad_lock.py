# eCRF_backend/datalad_lock.py
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional

from filelock import FileLock, Timeout

from .settings import get_settings


@dataclass(frozen=True)
class LockSpec:
    dataset_path: Path
    name: str = "dataset"
    timeout_s: Optional[float] = None


def _resolved_dataset_path(dataset_path: Path) -> Path:
    return Path(dataset_path).expanduser().resolve()


def _lockfile_path(dataset_path: Path, name: str) -> Path:
    # Keep lock file outside .git to avoid accidental staging.
    # Lock file is per dataset and per logical lock name.
    return dataset_path / f".casee.{name}.lock"


def _effective_timeout(timeout_s: Optional[float]) -> float:
    if timeout_s is not None:
        return float(timeout_s)
    settings = get_settings()
    return float(settings.datalad_lock_timeout_seconds)


@contextmanager
def dataset_lock(spec: LockSpec) -> Iterator[None]:
    dataset_path = _resolved_dataset_path(spec.dataset_path)
    dataset_path.mkdir(parents=True, exist_ok=True)

    lock_path = _lockfile_path(dataset_path, spec.name)
    timeout_s = _effective_timeout(spec.timeout_s)
    lock = FileLock(str(lock_path))

    acquired = False
    try:
        lock.acquire(timeout=timeout_s)
        acquired = True
        yield
    except Timeout as e:
        raise RuntimeError(
            f"Timeout acquiring lock '{spec.name}' for dataset '{dataset_path}' "
            f"using lock file '{lock_path}' after {timeout_s} seconds"
        ) from e
    finally:
        if acquired:
            try:
                lock.release()
            except Exception:
                # best effort
                pass