"""Summarise k6 results (loadtest/results/<label>/*.json) as markdown tables.

    python tools/loadtest_report.py local-m1
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def ms(seconds_ms: float) -> str:
    return f"{seconds_ms:.0f} ms" if seconds_ms < 1000 else f"{seconds_ms / 1000:.2f} s"


def row(name: str, m: dict, seconds: float, duration_key: str = "http_req_duration",
        failed_key: str = "http_req_failed", count: float = None) -> str:
    """Throughput = completed requests / planned test duration. (k6's own rate divides
    by total run time, including draining stuck requests, which understates it.)"""
    d = m[duration_key]
    completed = m["http_reqs"]["count"] if count is None else count
    dropped = m.get("dropped_iterations", {}).get("count", 0)
    failed = m[failed_key]["value"]
    return (f"| {name} | {completed / seconds:.2f} | {ms(d['med'])} | {ms(d['p(95)'])} | "
            f"{ms(d['p(99)'])} | {ms(d['max'])} | {failed:.1%} | {dropped:.0f} |")


def main() -> None:
    label = sys.argv[1]
    results = ROOT / "loadtest" / "results" / label
    load = {p.stem: json.loads(p.read_text())["metrics"]
            for p in results.glob("*.json") if not p.name.endswith(".meta.json")}
    secs = {p.name[: -len(".meta.json")]: json.loads(p.read_text())["duration_s"]
            for p in results.glob("*.meta.json")}

    def level(name: str) -> int:
        return int(re.sub(r"\D", "", name) or 0)

    header = ("| Test | Completed req/s | p50 | p95 | p99 | max | Errors | Dropped |\n"
              "|---|---|---|---|---|---|---|---|")
    print(f"### {label}\n\n**/predict (fixed arrival rate)**\n\n{header}")
    for name in sorted((n for n in load if n.startswith("predict-")), key=level):
        print(row(f"{level(name)} req/s offered", load[name], secs[name]))
    print(f"\n**/ask (fixed concurrency)**\n\n{header}")
    for name in sorted((n for n in load if n.startswith("ask-")), key=level):
        print(row(f"{level(name)} concurrent users", load[name], secs[name]))
    if "mixed" in load:
        m = load["mixed"]
        root = json.loads((results / "mixed.json").read_text())["root_group"]
        checks = root.get("checks") or {}
        checks = checks.values() if isinstance(checks, dict) else checks
        per_endpoint = {c["name"].split()[0]: c["passes"] + c["fails"] for c in checks}
        params = json.loads((results / "mixed.meta.json").read_text()).get("params", "")
        print(f"\n**Mixed ({params or '5 req/s /predict + 1 /ask every 4 s'})**\n\n{header}")
        for ep in ("predict", "ask"):
            n = per_endpoint[ep]  # every request runs exactly one check
            print(row(f"/{ep}", m, secs["mixed"], f"http_req_duration{{endpoint:{ep}}}",
                      f"http_req_failed{{endpoint:{ep}}}", count=n))


if __name__ == "__main__":
    main()
