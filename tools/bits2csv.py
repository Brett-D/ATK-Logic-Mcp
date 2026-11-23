"""Convert an atk-dl16 capture folder to a change-only CSV.

Usage:
    python tools/bits2csv.py <capture_dir> [-o out.csv]

Writes a row at the first sample, one per sample where any channel changes and one at the last
sample, under a sigrok/PulseView-style header ("Time(s),<ch>,<ch>,...").
"""
import argparse
from pathlib import Path

import numpy as np

from capture_files import load_channel, load_meta


def convert(cap: Path, out_csv: Path) -> int:
    meta = load_meta(cap)
    fs = float(meta["sample_rate"])
    n = int(meta["actual_samples"])
    chans = [int(c) for c in meta["channels"]]
    if n == 0:
        raise SystemExit(f"{cap}: capture has no samples")
    # Keep only each channel's initial level and edge positions, so long captures stay small in memory.
    inits, edges = [], []
    for c in chans:
        bits = load_channel(cap, c, n)
        inits.append(int(bits[0]))
        edges.append(np.flatnonzero(bits[1:] != bits[:-1]) + 1)
    rows = np.unique(np.concatenate([[0, n - 1], *edges]))
    # The level at sample i is the initial level flipped once per edge at or before i.
    levels = [(init + np.searchsorted(e, rows, side="right")) % 2 for init, e in zip(inits, edges)]
    with open(out_csv, "w", newline="\n", encoding="utf-8") as f:
        f.write(f"; Sample rate: {fs / 1e6:g} MHz\n; Sample count: {n}\n")
        f.write("Time(s)," + ",".join(str(c) for c in chans) + "\n")
        np.savetxt(f, np.column_stack([rows / fs, *levels]), fmt=["%.10f"] + ["%d"] * len(chans), delimiter=",")
    return len(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description="Convert an atk-dl16 capture folder to a change-only CSV.")
    ap.add_argument("capture_dir", type=Path)
    ap.add_argument("-o", "--out", type=Path, help="output CSV (default: <capture_dir>/<folder name>.csv)")
    args = ap.parse_args()
    out = args.out or args.capture_dir / f"{args.capture_dir.resolve().name}.csv"
    rows = convert(args.capture_dir, out)
    print(f"{out}: {rows} rows")


if __name__ == "__main__":
    main()
