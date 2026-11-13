#!/usr/bin/env bash
# Run the full load-test plan with a pinned k6 container; one JSON summary per run.
#   loadtest/run.sh <label> <base_url> [docker_network]
# Local (compose stack):  loadtest/run.sh local-m1 http://app:8000 llmops-support-assistant_default
# EC2 (on the node):      loadtest/run.sh ec2-t3large http://localhost host
# Override levels/durations with env vars, e.g. PREDICT_RATES="10 50" ASK_VUS="1 2".
set -euo pipefail

LABEL=$1
BASE_URL=$2
NETWORK=${3:-host}
K6_IMAGE=grafana/k6:0.52.0
OUT=loadtest/results/$LABEL
PREDICT_RATES=${PREDICT_RATES:-"10 25 50 100 200"}
PREDICT_DURATION=${PREDICT_DURATION:-45s}
ASK_VUS=${ASK_VUS:-"1 2 4"}
ASK_DURATION=${ASK_DURATION:-90s}
MIXED_DURATION=${MIXED_DURATION:-3m}
mkdir -p "$OUT"

run() {  # run <result-name> <script> [ENV=VALUE ...]
  local name=$1 script=$2; shift 2
  local envs=(-e "BASE_URL=$BASE_URL")
  for kv in "$@"; do envs+=(-e "$kv"); done
  echo "$(date -u +%H:%M:%S) $name"
  docker run --rm --network "$NETWORK" -v "$PWD":/repo -w /repo "${envs[@]}" "$K6_IMAGE" \
    run -q --summary-export="$OUT/$name.json" "$script" > "$OUT/$name.log" 2>&1 \
    || echo "  (k6 exited non-zero; see $OUT/$name.log)"
  sleep 10  # let the service settle between levels
}

for r in $PREDICT_RATES; do
  run "predict-rate${r}" loadtest/predict.js "RATE=$r" "DURATION=$PREDICT_DURATION"
done
for v in $ASK_VUS; do
  run "ask-vus${v}" loadtest/ask.js "VUS=$v" "DURATION=$ASK_DURATION"
done
run "mixed" loadtest/mixed.js "PREDICT_RATE=5" "ASK_EVERY=4" "DURATION=$MIXED_DURATION"

echo "$(date -u +%H:%M:%S) done -> $OUT"
