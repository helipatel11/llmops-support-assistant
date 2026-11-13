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


def row(name: str, m: dict, duration_key: str = "http_req_duration",
        failed_key: str = "http_req_failed") -> str:
    d = m[duration_key]
    reqs = m["http_reqs"]
    dropped = m.get("dropped_iterations", {}).get("count", 0)
    failed = m[failed_key]["value"]
    return (f"| {name} | {reqs['rate']:.2f} | {ms(d['med'])} | {ms(d['p(95)'])} | "
            f"{ms(d['p(99)'])} | {failed:.1%} | {dropped:.0f} |")


def main() -> None:
    label = sys.argv[1]
    results = ROOT / "loadtest" / "results" / label
    load = {p.stem: json.loads(p.read_text())["metrics"] for p in results.glob("*.json")}

    def level(name: str) -> int:
        return int(re.sub(r"\D", "", name) or 0)

    header = ("| Test | Achieved req/s | p50 | p95 | p99 | Errors | Dropped |\n"
              "|---|---|---|---|---|---|---|")
    print(f"### {label}\n\n**/predict (fixed arrival rate)**\n\n{header}")
    for name in sorted((n for n in load if n.startswith("predict-")), key=level):
        print(row(f"{level(name)} req/s offered", load[name]))
    print(f"\n**/ask (fixed concurrency)**\n\n{header}")
    for name in sorted((n for n in load if n.startswith("ask-")), key=level):
        print(row(f"{level(name)} concurrent users", load[name]))
    if "mixed" in load:
        m = load["mixed"]
        print(f"\n**Mixed (5 req/s /predict + 1 /ask every 4 s)**\n\n{header}")
        for ep in ("predict", "ask"):
            print(row(f"/{ep}", m, f"http_req_duration{{endpoint:{ep}}}",
                      f"http_req_failed{{endpoint:{ep}}}"))
        print("\n(Achieved req/s in the mixed rows is for both endpoints combined.)")


if __name__ == "__main__":
    main()
