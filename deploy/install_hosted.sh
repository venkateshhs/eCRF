#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${1:-/opt/casee}"
RUN_USER="${2:-casee}"
RUN_GROUP="${3:-casee}"

echo "[case-e] installing hosted bundle into ${APP_ROOT}"

if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y \
    git git-annex datalad apache2 \
    python3 python3-venv python3-pip
fi

if ! id "$RUN_USER" >/dev/null 2>&1; then
  sudo useradd --system --create-home --shell /bin/bash "$RUN_USER"
fi

sudo mkdir -p "$APP_ROOT"
sudo mkdir -p /srv/casee/bids_datasets
sudo chown -R "$RUN_USER":"$RUN_GROUP" "$APP_ROOT"
sudo chown -R "$RUN_USER":"$RUN_GROUP" /srv/casee

if [ ! -d "${APP_ROOT}/.venv" ]; then
  sudo -u "$RUN_USER" python3 -m venv "${APP_ROOT}/.venv"
fi

sudo -u "$RUN_USER" "${APP_ROOT}/.venv/bin/pip" install --upgrade pip wheel setuptools
sudo -u "$RUN_USER" "${APP_ROOT}/.venv/bin/pip" install -r "${APP_ROOT}/requirements.txt"

sudo install -m 0644 "${APP_ROOT}/deploy/systemd/casee.service" /etc/systemd/system/casee.service

sudo a2enmod proxy proxy_http ssl headers
sudo cp "${APP_ROOT}/deploy/apache/casee.conf" /etc/apache2/sites-available/casee.conf
if [ -f "${APP_ROOT}/deploy/apache/casee-ssl.conf" ]; then
  sudo cp "${APP_ROOT}/deploy/apache/casee-ssl.conf" /etc/apache2/sites-available/casee-ssl.conf
fi

sudo a2ensite casee.conf
sudo systemctl daemon-reload
sudo systemctl enable casee
sudo systemctl restart apache2
sudo systemctl restart casee

echo "[case-e] install complete"
sudo systemctl status casee --no-pager || true