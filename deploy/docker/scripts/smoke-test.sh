#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://localhost:8080}"

echo "[case-e] health"
curl -fsS "${BASE_URL}/health" | python -m json.tool

echo "[case-e] login"
LOGIN_JSON='{"username":"admin","password":"Admin123!"}'
TOKEN="$(
  curl -fsS \
    -H 'Content-Type: application/json' \
    -d "$LOGIN_JSON" \
    "${BASE_URL}/users/login" | python - <<'PY'
import json,sys
print(json.load(sys.stdin)["access_token"])
PY
)"

echo "[case-e] token ok"
echo "$TOKEN" | cut -c1-40
echo "..."

echo "[case-e] /users/me"
curl -fsS \
  -H "Authorization: Bearer ${TOKEN}" \
  "${BASE_URL}/users/me" | python -m json.tool

echo "[case-e] smoke test passed"