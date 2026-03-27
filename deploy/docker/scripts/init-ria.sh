#!/usr/bin/env bash
set -euo pipefail

export BIDS_ROOT="${BIDS_ROOT:-/srv/casee/bids_datasets}"
export ECRF_DATALAD_RIA_URL="${ECRF_DATALAD_RIA_URL:-ria+file:///ria-store}"
export ECRF_DATALAD_RIA_NAME="${ECRF_DATALAD_RIA_NAME:-ria}"
export ECRF_DATALAD_PUSH_DATA_MODE="${ECRF_DATALAD_PUSH_DATA_MODE:-auto-if-wanted}"

mkdir -p "$BIDS_ROOT"
mkdir -p /ria-store

if [ ! -f /ria-store/ria-layout-version ]; then
  printf "1\n" > /ria-store/ria-layout-version
fi

python - <<'PY'
import os
import shutil
from pathlib import Path
from datalad.api import Dataset, create_sibling_ria

root = Path(os.environ["BIDS_ROOT"])
test_ds = root / "_casee_ria_probe"
ria_url = os.environ["ECRF_DATALAD_RIA_URL"]
ria_name = os.environ["ECRF_DATALAD_RIA_NAME"]
push_data_mode = os.environ["ECRF_DATALAD_PUSH_DATA_MODE"]

if test_ds.exists():
    shutil.rmtree(test_ds)

ds = Dataset(str(test_ds))
ds.create(force=True, cfg_proc="text2git")
create_sibling_ria(
    dataset=str(test_ds),
    url=ria_url,
    name=ria_name,
    new_store_ok=True,
    existing="reconfigure",
    result_renderer="disabled",
)
ds.save(message="case-e: init ria probe")

kwargs = {"to": ria_name}
if push_data_mode != "nothing":
    kwargs["data"] = push_data_mode

ds.push(**kwargs)
print("[case-e] RIA probe OK:", test_ds)
PY