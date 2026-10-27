#!/usr/bin/env bash
set -euo pipefail

results="${1:-}"
if [ -z "$results" ]; then
  echo "uso: report.sh results.bin [standard|conflict]" >&2
  exit 1
fi
mode="${2:-standard}"

report=$(vegeta report -type=json "$results")

p99_ms=$(printf '%s' "$report" | jq -r '.latencies."99th" / 1000000 | floor')

printf 'requests=%s p99=%sms success=%s conflict_ratio=%s\n' \
  "$(printf '%s' "$report" | jq -r '.requests')" \
  "$p99_ms" \
  "$(printf '%s' "$report" | jq -r '.success')" \
  "$(printf '%s' "$report" | jq -r '(.status_codes["409"] // 0) / .requests')"

if [[ "$mode" == "conflict" ]]; then
  if printf '%s' "$report" | jq -e --argjson p99 "$p99_ms" \
    '(.status_codes["409"] // 0) / .requests >= 0.95 and $p99 < 250' > /dev/null; then
    echo "PASS (conflict)"
  else
    echo "FAIL (conflict)" >&2
    exit 1
  fi
else
  if printf '%s' "$report" | jq -e --argjson p99 "$p99_ms" \
    '.success >= 0.99 and $p99 < 250' > /dev/null; then
    echo "PASS"
  else
    echo "FAIL" >&2
    exit 1
  fi
fi
