#!/usr/bin/env bash
set -euo pipefail

: "${API_URL:?Set API_URL to the deployed API URL}"
: "${API_KEY:?Set API_KEY to the deployed API key}"

API_URL="${API_URL%/}"
response_file="$(mktemp)"
trap 'rm -f "$response_file"' EXIT

failed=0

call_api() {
  local method="$1"
  local path="$2"
  local status

  if [[ "$method" == "POST" ]]; then
    status="$(curl --silent --show-error \
      --max-time 70 \
      --output "$response_file" \
      --write-out '%{http_code}' \
      --request POST \
      --header "x-api-key: ${API_KEY}" \
      --header 'Content-Type: application/json' \
      --data '{}' \
      "${API_URL}${path}")"
  else
    status="$(curl --silent --show-error \
      --max-time 70 \
      --output "$response_file" \
      --write-out '%{http_code}' \
      --header "x-api-key: ${API_KEY}" \
      "${API_URL}${path}")"
  fi

  printf '%s %s -> %s\n' "$method" "$path" "$status"
  python -c \
    'import pathlib,sys; print(pathlib.Path(sys.argv[1]).read_text()[:300])' \
    "$response_file"
  printf '\n'

  if [[ "$status" != "200" ]]; then
    failed=1
  fi
}

call_api GET /bills
call_api POST /analysis/run
call_api GET /analysis
call_api POST /summary/generate
call_api GET /summary
call_api POST /report

if [[ "$failed" != "0" ]]; then
  printf 'FAIL: one or more endpoints returned a non-200 response.\n'
  exit 1
fi

printf 'PASS: all endpoints returned HTTP 200.\n'