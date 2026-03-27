from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from .datalad_config import get_datalad_config, is_datalad_enabled
from .datalad_worker import DataladWorker
from .logger import logger

if TYPE_CHECKING:
    from .datalad_store import DataladStudyStore


_worker: Optional[DataladWorker] = None
_store: Optional["DataladStudyStore"] = None


def init_datalad_runtime() -> None:
    global _worker, _store

    if _store is not None:
        return

    cfg = get_datalad_config()
    if not is_datalad_enabled(cfg):
        logger.info("DataLad runtime disabled")
        return

    _worker = DataladWorker(cfg, log=lambda s: logger.info(s))
    _worker.start()

    # lazy import to avoid circular import:
    # bids_exporter -> versions -> datalad_repo -> datalad_runtime
    from .datalad_store import DataladStudyStore

    _store = DataladStudyStore(cfg, worker=_worker)
    logger.info("DataLad runtime initialized")


def shutdown_datalad_runtime() -> None:
    global _worker, _store

    if _worker is not None:
        _worker.stop()

    _worker = None
    _store = None


def get_datalad_store() -> Optional["DataladStudyStore"]:
    return _store


def get_datalad_worker() -> Optional[DataladWorker]:
    return _worker