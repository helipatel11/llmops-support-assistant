"""Generate a synthetic, labelled support-ticket dataset.

Run from the repo root:  python -m training.generate_data

Design (so the test score means something):
- Held-out TEST templates AND held-out TEST phrases: a test ticket never reuses a
  sentence structure or a class-specific phrase from training (single words may overlap).
  A first version held out only templates and scored 1.0, because the shared phrase
  lists gave the label away.
- Systems, teams, times and some openers are shared by all priorities, so the model
  must learn urgency and impact signals, not "which system was mentioned".
- 5% of training labels are flipped to mimic labeller disagreement; test labels are clean.
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

# Openers used by every priority, so the first word is not always a giveaway.
NEUTRAL_OPENERS = ["Hi team", "Ticket", "Help", "Support request", "Hello"]

# Class-specific phrases. TRAIN and TEST lists never share a phrase: test tickets
# use wording the model has not seen, though individual words may overlap.
SLOTS = {
    "high": {
        "scope": {
            "train": ["all users", "every customer", "the whole company", "the entire {team} team"],
            "test": ["everyone in the building", "all of our clients",
                     "the full {team} department"],
        },
        "symptom": {
            "train": ["completely down", "returning 500 errors", "not responding at all",
                      "rejecting every request", "crashing on startup"],
            "test": ["hard down", "throwing 503s", "totally broken", "dead for everyone"],
        },
        "impact": {
            "train": ["we are losing revenue", "customers cannot pay", "nobody can work",
                      "orders are failing", "we are breaching our SLA"],
            "test": ["sales have stopped", "no payments are going through",
                     "the business is at a standstill"],
        },
        "opener": {
            "train": ["URGENT", "Critical", "P1", "Emergency"],
            "test": ["ASAP", "Sev1", "Major incident"],
        },
    },
    "medium": {
        "scope": {
            "train": ["a few users", "some customers", "two people on the {team} team",
                      "one office"],
            "test": ["a handful of people", "a couple of clients", "part of the {team} team"],
        },
        "symptom": {
            "train": ["slow", "timing out sometimes", "failing intermittently",
                      "showing errors now and then", "dropping connections"],
            "test": ["sluggish", "flaky", "erroring every so often", "lagging badly at times"],
        },
        "impact": {
            "train": ["there is a workaround", "it slows the team down", "retrying usually works",
                      "it is affecting productivity", "we can manage for today"],
            "test": ["we found a temporary workaround", "refreshing the page helps",
                     "it is hurting our throughput"],
        },
        "opener": {
            "train": ["Issue", "Problem", "Degraded", "Bug"],
            "test": ["Glitch", "Trouble", "Partial issue"],
        },
    },
    "low": {
        "scope": {
            "train": ["me", "my account", "one user", "a new starter"],
            "test": ["just me", "my profile", "a single colleague"],
        },
        "symptom": {
            "train": ["showing a typo", "using the old logo", "missing a dark mode option",
                      "sorting names oddly", "showing the wrong timezone label"],
            "test": ["misspelling a heading", "showing an outdated icon",
                     "using a hard-to-read font", "listing items in a weird order"],
        },
        "impact": {
            "train": ["no rush", "whenever you have time", "it is only cosmetic",
                      "nothing is blocked", "just a suggestion"],
            "test": ["not important", "purely a nice-to-have", "no impact on work"],
        },
        "opener": {
            "train": ["Question", "Request", "Suggestion", "FYI"],
            "test": ["Idea", "Minor request", "Small question"],
        },
    },
}

# Share of tickets that start with a neutral opener instead of a class-specific one.
NEUTRAL_OPENER_RATE = 0.4
# Share of TRAINING labels flipped at random, to mimic labeller disagreement.
TRAIN_LABEL_NOISE = 0.05

TEMPLATES = {
    "high": {
        "train": [
            "{opener}: {system} is {symptom} for {scope}",
            "{system} {symptom} {time}, {impact}",
            "{opener} - {scope} cannot use the {system}, {impact}",
            "The {system} has been {symptom} {time} and {impact}",
            "{opener}! {system} {symptom} for {scope}. {impact}",
            "Production {system} is {symptom}, {impact}",
            "{scope} are blocked because the {system} is {symptom}",
            "{opener} incident: {system} {symptom} {time}",
        ],
        "test": [
            "Please escalate: {system} {symptom} and {impact}",
            "We have a major problem, {system} is {symptom} for {scope}",
            "{system} outage affecting {scope} {time}",
        ],
    },
    "medium": {
        "train": [
            "{opener}: {system} is {symptom} for {scope}",
            "The {system} has been {symptom} {time}, {impact}",
            "{scope} report the {system} is {symptom}",
            "{opener} with {system}: {symptom} {time}",
            "{system} keeps {symptom} for {scope}, {impact}",
            "Can someone look at the {system}? It is {symptom}",
            "{opener} - {system} {symptom}, {impact}",
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
            "{opener}: the {system} is {symptom} for {scope}",
            "{opener} about the {system}, it is {symptom}, {impact}",
            "The {system} is {symptom}. {impact}",
            "{opener} - could the {system} stop {symptom}? {impact}",
            "Minor: {system} {symptom} for {scope}",
            "{opener}: how do I change the {system} settings for {scope}?",
            "When you get a chance, the {system} is {symptom}",
            "{opener} for {system}: {impact}, but it is {symptom}",
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


def fill(template: str, priority: str, split: str, rng: random.Random) -> str:
    values = {k: rng.choice(v) for k, v in SHARED.items()}
    values.update({k: rng.choice(v[split]) for k, v in SLOTS[priority].items()})
    if rng.random() < NEUTRAL_OPENER_RATE:
        values["opener"] = rng.choice(NEUTRAL_OPENERS)
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
            text = fill(rng.choice(TEMPLATES[priority][split]), priority, split, rng)
            if text not in seen:
                seen.add(text)
                rows.append((text, priority))
    rng.shuffle(rows)
    return rows


def add_label_noise(rows: list[tuple[str, str]], rate: float, rng: random.Random):
    """Flip `rate` of the labels to a different class. Returns (rows, n_flipped)."""
    labels = list(CLASS_SHARE)
    flip = set(rng.sample(range(len(rows)), round(len(rows) * rate)))
    noisy = [
        (text, rng.choice([lbl for lbl in labels if lbl != label]) if i in flip else label)
        for i, (text, label) in enumerate(rows)
    ]
    return noisy, len(flip)


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
    train, flipped = add_label_noise(train, TRAIN_LABEL_NOISE, rng)
    print(f"flipped {flipped} training labels ({TRAIN_LABEL_NOISE:.0%} noise); test labels clean")

    overlap = {t for t, _ in train} & {t for t, _ in test}
    if overlap:
        raise RuntimeError(f"{len(overlap)} tickets appear in both train and test")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(OUT_DIR / "tickets_train.csv", train)
    write_csv(OUT_DIR / "tickets_test.csv", test)
    print(f"seed={args.seed} train={len(train)} test={len(test)} -> {OUT_DIR}")


if __name__ == "__main__":
    main()
