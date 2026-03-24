# eCRF_backend/datalad_worker.py
from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from .datalad_config import DataladConfig
from .datalad_lock import dataset_lock, LockSpec

try:
    from datalad.api import Dataset  # type: ignore
except Exception:  # pragma: no cover
    Dataset = None  # type: ignore


@dataclass
class DataladJob:
    dataset_path: Path
    op: str  # "save" | "push" | "ensure_ria"
    message: Optional[str] = None
    to: Optional[str] = None
    attempt: int = 0
    max_attempts: int = 5


class DataladWorker:
    def __init__(self, cfg: DataladConfig, log: Callable[[str], None]) -> None:
        self.cfg = cfg
        self.log = log
        self._q: "queue.Queue[DataladJob]" = queue.Queue()
        self._stop = threading.Event()
        self._t: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._t and self._t.is_alive():
            return
        self._t = threading.Thread(target=self._run, name="datalad-worker", daemon=True)
        self._t.start()
        self.log("DataLad worker started")

    def stop(self, timeout_s: float = 5.0) -> None:
        self._stop.set()
        if self._t:
            self._t.join(timeout=timeout_s)
        self.log("DataLad worker stopped")

    def enqueue(self, job: DataladJob) -> None:
        self._q.put(job)

    def enqueue_save(self, dataset_path: Path, message: str) -> None:
        self.enqueue(DataladJob(dataset_path=dataset_path, op="save", message=message))

    def enqueue_push(self, dataset_path: Path, to: str) -> None:
        self.enqueue(DataladJob(dataset_path=dataset_path, op="push", to=to))

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                job = self._q.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                self._execute(job)
            except Exception as e:
                job.attempt += 1
                if job.attempt < job.max_attempts:
                    backoff = min(2 ** job.attempt, 30)
                    self.log(f"Job failed ({job.op}) attempt={job.attempt}, retry in {backoff}s: {e}")
                    time.sleep(backoff)
                    self._q.put(job)
                else:
                    self.log(f"Job permanently failed ({job.op}) after {job.attempt} attempts: {e}")
            finally:
                self._q.task_done()

    def _execute(self, job: DataladJob) -> None:
        if Dataset is None:
            raise RuntimeError("DataLad not installed in this environment")

        ds_path = job.dataset_path
        with dataset_lock(LockSpec(dataset_path=ds_path, timeout_s=300.0)):
            ds = Dataset(str(ds_path))
            if not ds.is_installed():
                # dataset creation is handled elsewhere; fail loudly for operator attention
                raise RuntimeError(f"Dataset not installed at {ds_path}")

            # Ensure repo identity (avoids common warnings)
            try:
                ds.repo.set_config("user.name", self.cfg.git_name, where="local")
                ds.repo.set_config("user.email", self.cfg.git_email, where="local")
                if self.cfg.gpgsign:
                    ds.repo.set_config("commit.gpgsign", "true", where="local")
                    if self.cfg.gpg_keyid:
                        ds.repo.set_config("user.signingkey", self.cfg.gpg_keyid, where="local")
            except Exception:
                # best effort; do not fail job
                pass

            if job.op == "save":
                msg = job.message or "case-e: save"
                ds.save(message=msg)
                self.log(f"Saved dataset: {ds_path} msg={msg}")

                if self.cfg.push_on_save and self.cfg.ria_name:
                    # push data auto-if-wanted; you may tune to "all"
                    ds.push(to=self.cfg.ria_name, data="auto-if-wanted")
                    self.log(f"Pushed dataset: {ds_path} to={self.cfg.ria_name}")

            elif job.op == "push":
                if not job.to:
                    raise ValueError("push requires 'to' sibling name")
                ds.push(to=job.to, data="auto-if-wanted")
                self.log(f"Pushed dataset: {ds_path} to={job.to}")

            else:
                raise ValueError(f"Unknown job op: {job.op}")
