# eCRF_backend/datalad_config.py
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, Set


@dataclass(frozen=True)
class DataladConfig:
    mode: str  # off|shadow|primary
    sync_mode: str  # async|sync
    primary_study_ids: Set[int]

    git_name: str
    git_email: str

    push_on_save: bool
    ria_url: Optional[str]
    ria_name: str

    gpgsign: bool
    gpg_keyid: Optional[str]


def _parse_int_set(csv: str) -> Set[int]:
    out: Set[int] = set()
    for part in (csv or "").split(","):
        part = part.strip()
        if part.isdigit():
            out.add(int(part))
    return out


def get_datalad_config() -> DataladConfig:
    mode = (os.getenv("ECRF_DATALAD_MODE", "off") or "off").strip().lower()
    if mode not in ("off", "shadow", "primary"):
        mode = "off"

    sync_mode = (os.getenv("ECRF_DATALAD_SYNC_MODE", "async") or "async").strip().lower()
    if sync_mode not in ("async", "sync"):
        sync_mode = "async"

    ids = _parse_int_set(os.getenv("ECRF_DATALAD_PRIMARY_STUDY_IDS", ""))

    git_name = os.getenv("ECRF_DATALAD_GIT_NAME", "case-e service")
    git_email = os.getenv("ECRF_DATALAD_GIT_EMAIL", "case-e@localhost")

    push_on_save = (os.getenv("ECRF_DATALAD_PUSH_ON_SAVE", "0") == "1")
    ria_url = os.getenv("ECRF_DATALAD_RIA_URL") or None
    ria_name = os.getenv("ECRF_DATALAD_RIA_NAME", "ria")

    gpgsign = (os.getenv("ECRF_DATALAD_GPGSIGN", "0") == "1")
    gpg_keyid = os.getenv("ECRF_DATALAD_GPG_KEYID") or None

    return DataladConfig(
        mode=mode,
        sync_mode=sync_mode,
        primary_study_ids=ids,
        git_name=git_name,
        git_email=git_email,
        push_on_save=push_on_save,
        ria_url=ria_url,
        ria_name=ria_name,
        gpgsign=gpgsign,
        gpg_keyid=gpg_keyid,
    )


def is_datalad_enabled(cfg: DataladConfig) -> bool:
    return cfg.mode in ("shadow", "primary")


def is_study_primary(cfg: DataladConfig, study_id: int) -> bool:
    return cfg.mode == "primary" and study_id in cfg.primary_study_ids
