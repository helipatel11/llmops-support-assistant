"""Send gentle, realistic demo traffic so the dashboard has data. NOT a load test (Phase 4).

    python tools/traffic.py --minutes 5 [--base-url http://localhost:8000]

One request at a time: mostly /predict (held-out test tickets), every 4th an /ask
(golden questions, including ones that should be declined). Standard library only.
"""

import argparse
import csv
import json
import random
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def post(base_url: str, path: str, payload: dict, timeout: float = 120) -> int:
    req = urllib.request.Request(
        base_url + path, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except (urllib.error.URLError, TimeoutError):
        return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--minutes", type=float, default=5)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    with (ROOT / "training" / "data" / "tickets_test.csv").open() as f:
        tickets = [row["text"] for row in csv.DictReader(f)]
    golden = (ROOT / "evaluation" / "golden_questions.jsonl").read_text().splitlines()
    questions = [json.loads(line)["question"] for line in golden if line.strip()]

    deadline, sent, statuses = time.time() + args.minutes * 60, 0, {}
    while time.time() < deadline:
        if sent % 4 == 3:
            path, payload = "/ask", {"question": rng.choice(questions)}
        else:
            path, payload = "/predict", {"text": rng.choice(tickets)}
        status = post(args.base_url, path, payload)
        sent += 1
        statuses[f"{path} {status}"] = statuses.get(f"{path} {status}", 0) + 1
        time.sleep(rng.uniform(0.2, 1.0))
    print(f"sent {sent} requests: {dict(sorted(statuses.items()))}")


if __name__ == "__main__":
    main()
