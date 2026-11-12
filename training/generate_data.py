"""Generate a synthetic, labelled support-ticket dataset.

Run from the repo root:  python -m training.generate_data

Design (so the test score means something):
- Each priority has its own TRAIN templates and separate, held-out TEST templates.
  The test set never contains a sentence structure the model was trained on.
- Systems, teams and times are shared by all priorities, so the model must learn
  urgency and impact signals, not "which system was mentioned".
- Seeded RNG: the same seed always produces the same files.

Limitation: template data is cleaner than real tickets, so scores here will
overstate real-world accuracy. Results are labelled "synthetic" wherever reported.
"""

import argparse
import csv
import random
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent / "data"

SHARED = {
    "system": [
        "payment API", "checkout page", "VPN", "email server", "customer database",
        "login service", "CRM", "HR portal", "shared drive", "build pipeline",
        "mobile app", "invoice service", "Wi-Fi", "Kubernetes cluster", "reporting dashboard",
        "SSO", "order service", "file upload", "search page", "billing system",
    ],
    "team": [
        "sales", "finance", "support", "engineering", "marketing", "HR", "operations", "legal",
    ],
    "time": [
        "since this morning", "for the last hour", "since the last deploy", "since yesterday",
        "after the update", "since 9am",
    ],
}

SLOTS = {
    "high": {
        "scope": [
            "all users", "every customer", "the whole company", "all regions",
            "the entire {team} team", "everyone",
        ],
        "symptom": [
            "completely down", "returning 500 errors", "not responding at all",
            "rejecting every request", "crashing on startup", "unreachable",
        ],
        "impact": [
            "we are losing revenue", "customers cannot pay", "nobody can work",
            "orders are failing", "this is a production outage", "we are breaching our SLA",
        ],
        "urgent": ["URGENT", "Critical", "P1", "Emergency", "Outage"],
    },
    "medium": {
        "scope": [
            "a few users", "some customers", "two people on the {team} team",
            "one office", "users in one region", "several users",
        ],
        "symptom": [
            "slow", "timing out sometimes", "failing intermittently",
            "showing errors now and then", "taking minutes to load", "dropping connections",
        ],
        "impact": [
            "there is a workaround", "people can still work but it is annoying",
            "it slows the team down", "retrying usually works", "it is affecting productivity",
            "we can manage for today",
        ],
        "urgent": ["Issue", "Problem", "Degraded", "Heads up", "Bug"],
    },
    "low": {
        "scope": ["me", "my account", "one user", "a new starter", "my laptop", "our intern"],
        "symptom": [
            "showing a typo", "using the old logo", "missing a dark mode option",
            "sorting names oddly", "showing the wrong timezone label",
            "asking me to log in once a week",
        ],
        "impact": [
            "no rush", "whenever you have time", "it is only cosmetic",
            "nothing is blocked", "just a suggestion", "low priority",
        ],
        "urgent": ["Question", "Request", "Suggestion", "FYI", "Small thing"],
    },
}

TEMPLATES = {
    "high": {
        "train": [
            "{urgent}: {system} is {symptom} for {scope}",
            "{system} {symptom} {time}, {impact}",
            "{urgent} - {scope} cannot use the {system}, {impact}",
            "The {system} has been {symptom} {time} and {impact}",
            "{urgent}! {system} {symptom} for {scope}. {impact}",
            "Production {system} is {symptom}, {impact}",
            "{scope} are blocked because the {system} is {symptom}",
            "{urgent} incident: {system} {symptom} {time}",
        ],
        "test": [
            "Please escalate: {system} {symptom} and {impact}",
            "We have a major problem, {system} is {symptom} for {scope}",
            "{system} outage affecting {scope} {time}",
        ],
    },
    "medium": {
        "train": [
            "{urgent}: {system} is {symptom} for {scope}",
            "The {system} has been {symptom} {time}, {impact}",
            "{scope} report the {system} is {symptom}",
            "{urgent} with {system}: {symptom} {time}",
            "{system} keeps {symptom} for {scope}, {impact}",
            "Can someone look at the {system}? It is {symptom}",
            "{urgent} - {system} {symptom}, {impact}",
            "Noticed the {system} is {symptom} for {scope}",
        ],
        "test": [
            "Not urgent but the {system} is {symptom} {time}",
            "{scope} say {system} is {symptom}; {impact}",
            "Could you check {system}, it has been {symptom} {time}",
        ],
    },
    "low": {
        "train": [
            "{urgent}: the {system} is {symptom} for {scope}",
            "{urgent} about the {system}, it is {symptom}, {impact}",
            "The {system} is {symptom}. {impact}",
            "{urgent} - could the {system} stop {symptom}? {impact}",
            "Minor: {system} {symptom} for {scope}",
            "{urgent}: how do I change the {system} settings for {scope}?",
            "When you get a chance, the {system} is {symptom}",
            "{urgent} for {system}: {impact}, but it is {symptom}",
        ],
        "test": [
            "Small request, {system} is {symptom}, {impact}",
            "Would it be possible to update the {system}? It is {symptom}",
            "Just letting you know the {system} is {symptom} for {scope}",
        ],
    },
}

# Class mix for each split: medium is the most common, as in most real queues.
CLASS_SHARE = {"high": 0.3, "medium": 0.4, "low": 0.3}


def fill(template: str, priority: str, rng: random.Random) -> str:
    values = {k: rng.choice(v) for k, v in SHARED.items()}
    values.update({k: rng.choice(v) for k, v in SLOTS[priority].items()})
    text = template.format(**values)
    return text.format(team=values["team"])  # resolves {team} inside scope phrases


def generate(split: str, n: int, rng: random.Random) -> list[tuple[str, str]]:
    rows, seen = [], set()
    for priority, share in CLASS_SHARE.items():
        target = round(n * share)
        attempts = 0
        while sum(1 for _, p in rows if p == priority) < target:
            attempts += 1
            if attempts > target * 50:
                raise RuntimeError(f"Not enough unique {split}/{priority} combinations")
            text = fill(rng.choice(TEMPLATES[priority][split]), priority, rng)
            if text not in seen:
                seen.add(text)
                rows.append((text, priority))
    rng.shuffle(rows)
    return rows


def write_csv(path: Path, rows: list[tuple[str, str]]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["text", "priority"])
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-size", type=int, default=600)
    parser.add_argument("--test-size", type=int, default=150)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    train = generate("train", args.train_size, rng)
    test = generate("test", args.test_size, rng)

    overlap = {t for t, _ in train} & {t for t, _ in test}
    if overlap:
        raise RuntimeError(f"{len(overlap)} tickets appear in both train and test")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(OUT_DIR / "tickets_train.csv", train)
    write_csv(OUT_DIR / "tickets_test.csv", test)
    print(f"seed={args.seed} train={len(train)} test={len(test)} -> {OUT_DIR}")


if __name__ == "__main__":
    main()
