#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8003}"
SCENARIO="${1:-health}"
RATE="${RATE:-100}"
DURATION="${DURATION:-60s}"
OUT_DIR="${OUT_DIR:-perf/vegeta/results}"

rendered=""
cleanup_id=""

cleanup() {
  if [[ -n "$rendered" ]]; then
    rm -f "$rendered"
  fi
  if [[ -n "$cleanup_id" ]]; then
    curl --silent -X DELETE "${BASE_URL}/api/v1/documents/${cleanup_id}" > /dev/null || true
  fi
}
trap cleanup EXIT

target_file="perf/vegeta/targets/${SCENARIO}.json"
if [[ ! -f "$target_file" ]]; then
  echo "escenario inexistente: $target_file" >&2
  exit 1
fi

rendered=$(mktemp)

if [[ "$SCENARIO" == "fetch_hit" ]]; then
  seed_checksum="vegeta-seed-$(date +%s)"
  seed_response=$(curl --fail --silent --show-error \
    -X POST "${BASE_URL}/api/v1/store" \
    -H 'Content-Type: application/json' \
    -d "{\"name\": \"vegeta-seed.pdf\", \"text\": \"vegeta seed document\", \"checksum\": \"${seed_checksum}\", \"size\": 21}")
  cleanup_id=$(printf '%s' "$seed_response" | jq -r '.id')
  sed -e "s|__BASE_URL__|${BASE_URL}|g" -e "s|__SEED_CHECKSUM__|${seed_checksum}|g" \
    "$target_file" > "$rendered"
else
  sed -e "s|__BASE_URL__|${BASE_URL}|g" "$target_file" > "$rendered"
fi

mkdir -p "$OUT_DIR"
results="${OUT_DIR}/${SCENARIO}_${RATE}rps_$(printf '%s' "$DURATION" | tr -cd '[:alnum:]').bin"

echo "atacando ${SCENARIO} @ ${RATE} rps durante ${DURATION} -> ${results}"
vegeta attack -rate "${RATE}/s" -duration "$DURATION" -targets "$rendered" -output "$results"

vegeta report -type=json "$results" > "${results%.bin}.json"
echo "reporte: ${results%.bin}.json"
echo "validar con: perf/vegeta/report.sh ${results} $([[ "$SCENARIO" == "store_conflict" ]] && echo conflict)"
