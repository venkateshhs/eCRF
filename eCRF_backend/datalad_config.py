from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, Set

from .settings import get_settings


@dataclass(frozen=True)
class DataladConfig:
    mode: str                  # off|shadow|primary
    sync_mode: str             # async|sync
    primary_study_ids: Set[int]

    git_name: str
    git_email: str

    push_on_save: bool
    push_data_mode: str        # auto-if-wanted|all|nothing
    verify_push: bool
    drop_after_push: bool
    get_on_open: bool

    ria_url: Optional[str]
    ria_name: str
    ssh_remote_template: Optional[str]

    gpgsign: bool
    gpg_keyid: Optional[str]

    require_ria_for_writes: bool


def _parse_int_set(csv: str) -> Set[int]:
    out: Set[int] = set()
    for part in (csv or "").split(","):
        part = part.strip()
        if part.isdigit():
            out.add(int(part))
    return out


def is_datalad_enabled(cfg: Optional[DataladConfig] = None) -> bool:
    cfg = cfg or get_datalad_config()
    return cfg.mode in {"shadow", "primary"}


def is_study_primary(cfg: Optional[DataladConfig], study_id: int) -> bool:
    cfg = cfg or get_datalad_config()
    return cfg.mode == "primary" and int(study_id) in cfg.primary_study_ids


def get_datalad_config() -> DataladConfig:
    settings = get_settings()

    mode = (os.getenv("ECRF_DATALAD_MODE", "off") or "off").strip().lower()
    if mode not in ("off", "shadow", "primary"):
        mode = "off"

    sync_mode = (os.getenv("ECRF_DATALAD_SYNC_MODE", "async") or "async").strip().lower()
    if sync_mode not in ("async", "sync"):
        sync_mode = "async"

    push_data_mode = (
        os.getenv("ECRF_DATALAD_PUSH_DATA_MODE", "auto-if-wanted") or "auto-if-wanted"
    ).strip().lower()
    if push_data_mode not in ("auto-if-wanted", "all", "nothing"):
        push_data_mode = "auto-if-wanted"

    cfg = DataladConfig(
        mode=mode,
        sync_mode=sync_mode,
        primary_study_ids=_parse_int_set(os.getenv("ECRF_DATALAD_PRIMARY_STUDY_IDS", "")),
        git_name=os.getenv("ECRF_DATALAD_GIT_NAME", "case-e service"),
        git_email=os.getenv("ECRF_DATALAD_GIT_EMAIL", "case-e@localhost"),
        push_on_save=(os.getenv("ECRF_DATALAD_PUSH_ON_SAVE", "0") == "1"),
        push_data_mode=push_data_mode,
        verify_push=(os.getenv("ECRF_DATALAD_VERIFY_PUSH", "1") == "1"),
        drop_after_push=(os.getenv("ECRF_DATALAD_DROP_AFTER_PUSH", "0") == "1"),
        get_on_open=(os.getenv("ECRF_DATALAD_GET_ON_OPEN", "1") == "1"),
        ria_url=os.getenv("ECRF_DATALAD_RIA_URL") or None,
        ria_name=os.getenv("ECRF_DATALAD_RIA_NAME", "ria"),
        ssh_remote_template=os.getenv("ECRF_DATALAD_SSH_REMOTE_TEMPLATE") or None,
        gpgsign=(os.getenv("ECRF_DATALAD_GPGSIGN", "0") == "1"),
        gpg_keyid=os.getenv("ECRF_DATALAD_GPG_KEYID") or None,
        require_ria_for_writes=(
            os.getenv("ECRF_DATALAD_REQUIRE_RIA_FOR_WRITES", "1" if settings.is_production else "0") == "1"
        ),
    )

    if (
        settings.is_production
        and cfg.require_ria_for_writes
        and not cfg.ria_url
        and not cfg.ssh_remote_template
    ):
        raise RuntimeError(
            "ECRF_DATALAD_REQUIRE_RIA_FOR_WRITES=1 but neither "
            "ECRF_DATALAD_RIA_URL nor ECRF_DATALAD_SSH_REMOTE_TEMPLATE is configured."
        )

    return cfg
