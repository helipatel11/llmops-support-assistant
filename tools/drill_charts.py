"""Charts for the Phase 5 rollback drill, rebuilt from the committed evidence
(loadtest/results/ec2-drill/: Prometheus range exports + drill timeline).

    python tools/drill_charts.py   ->  docs/images/drill-a.png, docs/images/drill-b2.png
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "loadtest" / "results" / "ec2-drill"
OUT = ROOT / "docs" / "images"

SURFACE, INK, INK_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
SLOT_1, SLOT_2 = "#2a78d6", "#eb6834"  # categorical: identity (release A / release B)
CRITICAL = "#d03b3b"  # status: errors (always labelled, never color alone)
PENDING, FIRING = "#f6e3b5", "#f2c4c4"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK_2, "text.color": INK,
    "xtick.color": INK_2, "ytick.color": INK_2, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.8, "axes.spines.top": False, "axes.spines.right": False,
    "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold",
    "axes.titlelocation": "left", "lines.linewidth": 2,
})


def ts(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def prom(name: str) -> list:
    return json.loads((EVIDENCE / "prometheus" / f"prom-{name}.json").read_text())["data"]["result"]


def points(result: dict, scale: float = 1.0):
    xs = [datetime.fromtimestamp(t, tz=timezone.utc) for t, _ in result["values"]]
    ys = [float(v) * scale if v != "NaN" else float("nan") for _, v in result["values"]]
    return xs, ys


def timeline():
    """(time, {commit: (ready, not_ready)}, alerts-string) per recorder sample."""
    rows = []
    for line in (EVIDENCE / "drill-timeline.log").read_text().splitlines():
        m = re.match(r"(\S+) pods: (.*?) \| alerts: (.*)", line)
        if not m:
            continue
        pods = {}
        for commit, ready, n in re.findall(r"(\w{7})\(ready=(\w+)\)x(\d+)", m.group(2)):
            r, nr = pods.get(commit, (0, 0))
            pods[commit] = (r + int(n), nr) if ready == "true" else (r, nr + int(n))
        rows.append((ts(m.group(1)), pods, m.group(3)))
    return rows


def alert_spans(rows, needle):
    """Contiguous spans where the alert string contains `needle`."""
    spans, start, prev = [], None, None
    for t, _, alerts in rows:
        if needle in alerts and start is None:
            start = t
        elif needle not in alerts and start is not None:
            spans.append((start, prev))
            start = None
        prev = t
    return spans


def mark(axes, when: datetime, label: str, top_ax):
    for ax in axes:
        ax.axvline(when, color=INK_2, linewidth=1, linestyle=(0, (3, 3)))
    top_ax.annotate(label, (when, 1.0), xycoords=("data", "axes fraction"),
                    xytext=(3, 4), textcoords="offset points", fontsize=8.5, color=INK_2,
                    rotation=0, va="bottom")


def finish(fig, axes, start, end, path, title, subtitle, top=0.86):
    for ax in axes:
        ax.set_xlim(start, end)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=timezone.utc))
    axes[-1].set_xlabel("UTC, 15 Nov 2026 (EC2 t3.large, k3s)")
    fig.subplots_adjust(top=top)
    fig.suptitle(title, x=0.01, y=0.995, ha="left", fontsize=13, fontweight="bold")
    fig.text(0.01, 0.995 - 0.045 * 8 / fig.get_figheight(), subtitle, ha="left", fontsize=9.5,
             color=INK_2)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("wrote", path.relative_to(ROOT))


def pod_panel(ax, rows, start, end, commits):
    """Ready pods per commit (solid) and not-ready pods (dashed)."""
    sel = [(t, p) for t, p, _ in rows if start <= t <= end]
    for i, (commit, label) in enumerate(commits):
        color = (SLOT_1, SLOT_2)[i]
        xs = [t for t, _ in sel]
        ax.step(xs, [p.get(commit, (0, 0))[0] for _, p in sel], where="post", color=color,
                label=f"{label}: ready")
        nr = [p.get(commit, (0, 0))[1] for _, p in sel]
        if any(nr):
            ax.step(xs, nr, where="post", color=color, linestyle=(0, (2, 2)), linewidth=1.5,
                    label=f"{label}: running, not ready")
    ax.set_ylim(-0.2, 4.4)
    ax.set_yticks([0, 1, 2, 3])
    ax.set_ylabel("pods")
    ax.legend(loc="upper left", frameon=False, fontsize=8.5, ncol=2, bbox_to_anchor=(0, 0.98))


def drill_a(rows):
    start, end = ts("2026-11-15T04:30:00Z"), ts("2026-11-15T04:37:40Z")
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 5.6), sharex=True,
                                   gridspec_kw={"height_ratios": [1.2, 1], "hspace": 0.35})
    pod_panel(ax1, rows, start, end, [("df0f53c", "df0f53c")])
    ax1.set_title("Pods: the new pod (llama3 config) never becomes Ready", pad=22)

    # No 5xx series existed yet in this window (the counter had never been incremented),
    # which means zero; draw it so the absence is visible, not implied.
    ax2.plot([start, end], [0, 0], color=CRITICAL, label="/predict + /ask 5xx (none recorded)")
    for r in prom("requests_by_status"):
        if r["metric"]["handler"] == "/ask" and r["metric"]["status"] == "2xx":
            xs, ys = points(r, 60)
            ax2.plot(xs, ys, color=SLOT_1, label="/ask 2xx")
    ax2.set_ylabel("/ask per minute")
    ax2.set_title("User-facing errors during the stalled rollout: none", pad=22)
    ax2.legend(loc="upper left", frameon=False, fontsize=8.5, ncol=2, bbox_to_anchor=(0, 1.0))
    ax2.set_ylim(-0.3, 6)

    axes = (ax1, ax2)
    mark(axes, ts("2026-11-15T04:32:09Z"), "bad config released", ax1)
    mark(axes, ts("2026-11-15T04:36:11Z"), "ProgressDeadlineExceeded", ax1)
    mark(axes, ts("2026-11-15T04:36:33Z"), "  rollback (2 s)", ax2)
    finish(fig, axes, start, end, OUT / "drill-a.png",
           "Drill A: a bad config release is stopped by the readiness probe",
           "kubectl set env GENERATION_VERSION=llama3; the node has no llama3, so /ready "
           "returns 503 "
           "and the old pods keep serving.", top=0.84)


def drill_b2(rows):
    start, end = ts("2026-11-15T04:52:00Z"), ts("2026-11-15T05:01:00Z")
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 8), sharex=True,
                                        gridspec_kw={"height_ratios": [1, 1, 1], "hspace": 0.45})
    pod_panel(ax1, rows, start, end,
              [("fa9f809", "fa9f809 (good)"), ("07837e1", "07837e1 (bad: 5 s deadline)")])
    ax1.set_title("Pods by image commit", pad=22)

    for r in prom("requests_by_status"):
        if r["metric"]["handler"] != "/ask":
            continue
        xs, ys = points(r, 60)
        ok = r["metric"]["status"] == "2xx"
        ax2.plot(xs, ys, color=SLOT_1 if ok else CRITICAL,
                 label="/ask 2xx (answered)" if ok else "/ask 5xx (deadline exceeded)")
    ax2.set_ylabel("per minute")
    ax2.set_ylim(-0.3, 6.2)
    ax2.set_title("/ask completions", pad=22)
    ax2.legend(loc="upper left", frameon=False, fontsize=8.5, ncol=2, bbox_to_anchor=(0, 0.98))

    for a, b in alert_spans(rows, "EndpointErrorRatioHigh/ask=pending"):
        ax3.axvspan(a, b, color=PENDING, linewidth=0)
    for a, b in alert_spans(rows, "EndpointErrorRatioHigh/ask=firing"):
        ax3.axvspan(a, b, color=FIRING, linewidth=0)
    for r in prom("ask_error_ratio"):
        if r["metric"]["handler"] == "/ask":
            xs, ys = points(r, 100)
            ax3.plot(xs, ys, color=CRITICAL, label="/ask 5xx ratio (1 min window)")
    ax3.axhline(5, color=INK_2, linewidth=1, linestyle=(0, (1, 2)))
    ax3.text(start, 7, " alert threshold 5%", color=INK_2, fontsize=8.5)
    ax3.set_ylim(-5, 135)
    ax3.set_ylabel("% of /ask")
    ax3.set_title("Alert EndpointErrorRatioHigh: pending (yellow) needs 1 min, then firing (red)",
                  pad=22)
    ax3.legend(loc="upper left", frameon=False, fontsize=8.5, bbox_to_anchor=(0, 0.98))

    axes = (ax1, ax2, ax3)
    mark(axes, ts("2026-11-15T04:53:27Z"), "bad release", ax1)
    mark(axes, ts("2026-11-15T04:58:27Z"), "alert fires", ax1)
    mark(axes, ts("2026-11-15T04:59:58Z"), "recovered", ax1)
    finish(fig, axes, start, end, OUT / "drill-b2.png",
           "Drill B: a bad image passes every probe; only monitoring catches it",
           "Bad release live 04:54:48 -> alert fired 04:58:27 (3 min 39 s) -> rollback done "
           "04:59:52 (83 s). Background traffic: 2 req/s /predict + 1 /ask every 20 s.")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    rows = timeline()
    drill_a(rows)
    drill_b2(rows)
