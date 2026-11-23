"""Render an atk-dl16 capture folder as a zoomable waveform page (viewer.html).

Usage:
    python tools/view.py [capture_dir] [--config view.json] [-o out.html]

capture_dir defaults to the newest folder under $ATK_DL16_DATA_DIR/captures (or ./captures).
The optional JSON config sets channel labels, row order and the initial view window in µs:
    {"labels": {"0": "CLK", "1": "DATA"}, "order": [1, 0], "view_us": [100, 250]}
Channels missing from "order" follow in channel-number order.
"""
import argparse
import json
import os
from pathlib import Path

import numpy as np

from capture_files import load_channel, load_meta

TEMPLATE = Path(__file__).resolve().parent / "viewer_template.html"


def newest_capture() -> Path:
    root = Path(os.environ.get("ATK_DL16_DATA_DIR", ".")) / "captures"
    dirs = [d for d in root.iterdir() if (d / "meta.json").is_file()] if root.is_dir() else []
    if not dirs:
        raise SystemExit(f"no capture folders found under {root}")
    return max(dirs, key=lambda d: d.stat().st_mtime)


def build_data(cap: Path, cfg: dict) -> dict:
    meta = load_meta(cap)
    n = int(meta["actual_samples"])
    rate = float(meta["sample_rate"])
    labels = {int(k): str(v) for k, v in cfg.get("labels", {}).items()}
    chans = []
    for ch in (int(c) for c in meta["channels"]):
        bits = load_channel(cap, ch, n)
        edges = np.flatnonzero(bits[1:] != bits[:-1]) + 1
        chans.append({"ch": ch, "label": labels.get(ch, ""), "init": int(bits[0]) if n else 0,
                      "edges": edges.tolist(), "high": float(bits.mean()) if n else 0.0})
    order = cfg.get("order")
    if order:
        rank = {int(c): i for i, c in enumerate(order)}
        chans.sort(key=lambda c: rank.get(c["ch"], len(rank) + c["ch"]))
    data = {"id": str(meta.get("capture_id", cap.name)), "rate": rate, "n": n,
            "thr": meta.get("threshold_voltage"), "chans": chans}
    view_us = cfg.get("view_us")
    if view_us:
        data["view"] = [max(0, int(view_us[0] * rate / 1e6)), min(n, int(view_us[1] * rate / 1e6))]
    return data


def main() -> None:
    ap = argparse.ArgumentParser(description="Render an atk-dl16 capture as a zoomable waveform page.")
    ap.add_argument("capture_dir", nargs="?", type=Path, help="capture folder (default: newest)")
    ap.add_argument("--config", type=Path, help="JSON with labels, order and view_us")
    ap.add_argument("-o", "--out", type=Path, help="output HTML (default: <capture_dir>/viewer.html)")
    args = ap.parse_args()

    cap = args.capture_dir or newest_capture()
    cfg = json.loads(args.config.read_text(encoding="utf-8")) if args.config else {}
    # Escape "</" so a label can't close the <script> element the data is embedded in.
    payload = json.dumps(build_data(cap, cfg)).replace("</", "<\\/")
    html = TEMPLATE.read_text(encoding="utf-8").replace("/*DATA*/null", payload)
    out = args.out or cap / "viewer.html"
    out.write_text(html, encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
