#!/usr/bin/env bash
# Rollback-drill recorder: every 5 s, one line per sample with UTC time, each app pod's
# image commit and readiness, and Prometheus alert states. Runs ON the k3s node.
#
#   ssh ubuntu@<node> 'bash -s' < tools/drill_watch.sh > drill-timeline.log
#
# The drill's "detected at" / "recovered at" times are read from this log, not from memory.
set -uo pipefail
export KUBECONFIG=${KUBECONFIG:-/home/ubuntu/.kube/config}
ns=llmops
prom="http://$(kubectl -n $ns get svc prometheus -o jsonpath='{.spec.clusterIP}'):9090"

while true; do
  pods=$(kubectl -n $ns get pods -l app=support-assistant -o jsonpath='{range .items[*]}{.spec.containers[0].image}{" "}{.status.containerStatuses[0].ready}{"\n"}{end}' \
    | sed -E 's|.*:([0-9a-f]{7})[0-9a-f]*|\1|' | sort | uniq -c | awk '{printf "%s(ready=%s)x%s ", $2, $3, $1}')
  alerts=$(curl -s --max-time 3 "$prom/api/v1/alerts" \
    | python3 -c 'import json,sys
a=json.load(sys.stdin)["data"]["alerts"]
out = []
for x in a:
    labels = x["labels"]
    out.append(labels["alertname"] + labels.get("handler", "") + "=" + x["state"])
print(" ".join(out) or "none")' 2>/dev/null || echo "prometheus-unreachable")
  echo "$(date -u +%FT%TZ) pods: ${pods:-none} | alerts: $alerts"
  sleep 5
done
