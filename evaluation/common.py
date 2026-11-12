"""Helpers shared by the evaluation scripts: run metadata and result files."""

import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "evaluation" / "results"


def git_commit() -> str:
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=PROJECT_ROOT, text=True
        ).strip()
        dirty = subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=no"], cwd=PROJECT_ROOT, text=True
        ).strip()
        return f"{sha}-dirty" if dirty else sha
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:12]


def run_metadata() -> dict:
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_commit": git_commit(),
        "python": platform.python_version(),
        "machine": f"{platform.system()} {platform.machine()}",
    }


def write_result(name: str, result: dict) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / f"{name}.json"
    path.write_text(json.dumps(result, indent=2) + "\n")
    return path
