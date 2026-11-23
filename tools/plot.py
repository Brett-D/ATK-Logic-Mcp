"""Draw channels of an atk-dl16 capture folder as a static PNG (needs matplotlib).

Usage:
    python tools/plot.py <capture_dir> [--channels 1,2,8] [--start-us 0] [--end-us 50]
                         [--config view.json] [--title TEXT] [-o out.png]

--config takes the same JSON as view.py ({"labels": {...}, "order": [...], "view_us": [start, end]}).
Rows are --channels, else the config's "order", else every channel in the capture. --start-us and
--end-us (from the start of the capture) override "view_us"; the default is the whole capture.
"""
import argparse
import json
from pathlib import Path

import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError as ex:
    raise SystemExit(f"plot.py needs matplotlib ({ex}); install it with: pip install matplotlib") from None

from capture_files import load_meta, load_window


def steps(seg: np.ndarray, a: int) -> tuple[np.ndarray, np.ndarray]:
    """Step-plot points for a window starting at sample a: its ends plus one point per level change."""
    e = np.flatnonzero(seg[1:] != seg[:-1]) + 1
    return np.r_[0, e, len(seg)] + a, np.r_[seg[0], seg[e], seg[-1]]


def main() -> None:
    ap = argparse.ArgumentParser(description="Draw channels of an atk-dl16 capture as a static PNG.")
    ap.add_argument("capture_dir", type=Path)
    ap.add_argument("--channels", help="comma-separated channels, top row first")
    ap.add_argument("--start-us", type=float, help="window start, µs from the start of the capture")
    ap.add_argument("--end-us", type=float, help="window end, µs from the start of the capture")
    ap.add_argument("--config", type=Path, help="view.py-style JSON with labels, order and view_us")
    ap.add_argument("--title", help="chart title (default: capture id, rate and threshold)")
    ap.add_argument("-o", "--out", type=Path, help="output PNG (default: <capture_dir>/plot.png)")
    args = ap.parse_args()

    cap = args.capture_dir
    cfg = json.loads(args.config.read_text(encoding="utf-8")) if args.config else {}
    meta = load_meta(cap)
    fs = float(meta["sample_rate"])
    n = int(meta["actual_samples"])
    available = [int(c) for c in meta["channels"]]
    if args.channels:
        order = [int(c) for c in args.channels.split(",") if c.strip()]
    else:
        order = [int(c) for c in cfg.get("order", [])] or available
    missing = [c for c in order if c not in available]
    if missing:
        raise SystemExit(f"channels not in this capture: {missing} (captured: {available})")
    labels = {int(k): str(v) for k, v in cfg.get("labels", {}).items()}

    view = cfg.get("view_us") or [0.0, n / fs * 1e6]
    t0 = args.start_us if args.start_us is not None else view[0]
    t1 = args.end_us if args.end_us is not None else view[1]
    a, b = max(0, int(t0 * fs / 1e6)), min(n, int(np.ceil(t1 * fs / 1e6)))
    if b - a < 2:
        raise SystemExit("the time window holds fewer than 2 samples")

    fig, ax = plt.subplots(figsize=(13, max(2.0, 0.8 + 0.45 * len(order))))
    for row, c in enumerate(order):
        x, y = steps(load_window(cap, c, n, a, b), a)
        ax.step(x / fs * 1e6, y * 0.7 + (len(order) - 1 - row), where="post", lw=1.1)
    ax.set_yticks([len(order) - 1 - i + 0.35 for i in range(len(order))])
    ax.set_yticklabels([f"CH{c} {labels.get(c, '')}".strip() for c in order], fontsize=8.5)
    ax.set_xlim(a / fs * 1e6, b / fs * 1e6)
    ax.set_xlabel("time from capture start (µs)")
    ax.grid(axis="x", color="#ddd", lw=0.6)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.tick_params(axis="y", length=0)
    title = args.title or (f"{meta.get('capture_id', cap.name)}, {fs / 1e6:g} MHz, "
                           f"threshold {meta.get('threshold_voltage')} V")
    ax.set_title(title, fontsize=10)
    fig.tight_layout()
    out = args.out or cap / "plot.png"
    fig.savefig(out, dpi=110)
    plt.close(fig)
    print(out)


if __name__ == "__main__":
    main()
