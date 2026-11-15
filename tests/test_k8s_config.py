"""The k3s ConfigMaps are generated from monitoring/ (make k8s-prometheus k8s-dashboard).
Fail if someone edits one side only, so the cluster never runs stale rules or dashboards."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def configmap(name):
    return yaml.safe_load((ROOT / "infra/k8s" / name).read_text())["data"]


def test_prometheus_configmap_matches_sources():
    data = configmap("prometheus-config.yaml")
    assert data["prometheus.yml"] == (ROOT / "monitoring/prometheus-k8s.yml").read_text()
    assert data["alerts.yml"] == (ROOT / "monitoring/alerts.yml").read_text()


def test_dashboard_configmap_matches_source():
    data = configmap("grafana-dashboards-configmap.yaml")
    source = ROOT / "monitoring/grafana/dashboards/support-assistant.json"
    assert data["support-assistant.json"] == source.read_text()


def test_deployment_pins_no_image_tag():
    """The tag is chosen at deploy time (infra/k8s/deploy.sh); a committed tag would
    silently roll pods back to it on every `kubectl apply`."""
    text = (ROOT / "infra/k8s/deployment.yaml").read_text()
    docs = yaml.safe_load(text)
    containers = (docs["spec"]["template"]["spec"]["containers"]
                  + docs["spec"]["template"]["spec"]["initContainers"])
    assert all(c["image"] == "support-assistant" for c in containers)
    assert "replicas" not in docs["spec"]  # owned by the HPA
