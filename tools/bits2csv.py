"""Convert an atk-dl16 capture folder to a change-only CSV.

Usage:
    python tools/bits2csv.py <capture_dir> [-o out.csv]

Writes a row at the first sample, one per sample where any channel changes and one at the last
sample, under a sigrok/PulseView-style header ("Time(s),<ch>,<ch>,...").
"""
import argparse
from pathlib import Path

import numpy as np

from capture_files import load_meta, map_channel

# Samples per batch. A multiple of 8, so every batch starts on a byte boundary of the packed files.
CHUNK = 1 << 18


def convert(cap: Path, out_csv: Path) -> int:
    meta = load_meta(cap)
    fs = float(meta["sample_rate"])
    n = int(meta["actual_samples"])
    chans = [int(c) for c in meta["channels"]]
    if n == 0 or not chans:
        raise SystemExit(f"{cap}: capture has no samples")
    # Walk memory-mapped files in fixed-size batches, so memory use doesn't grow with the capture.
    packed = [map_channel(cap, c, n) for c in chans]
    fmt = ["%.10f"] + ["%d"] * len(chans)
    prev = None  # levels at the last sample of the previous batch
    total = 0
    with open(out_csv, "w", newline="\n", encoding="utf-8") as f:
        f.write(f"; Sample rate: {fs / 1e6:g} MHz\n; Sample count: {n}\n")
        f.write("Time(s)," + ",".join(str(c) for c in chans) + "\n")
        for start in range(0, n, CHUNK):
            stop = min(n, start + CHUNK)
            bits = np.stack([np.unpackbits(p[start // 8:(stop + 7) // 8], bitorder="little")[:stop - start]
                             for p in packed])
            rows = np.flatnonzero(np.any(bits[:, 1:] != bits[:, :-1], axis=0)) + 1
            if prev is None or np.any(bits[:, 0] != prev):
                rows = np.r_[0, rows]
            if stop == n and (rows.size == 0 or rows[-1] != stop - start - 1):
                rows = np.r_[rows, stop - start - 1]
            if rows.size:
                np.savetxt(f, np.column_stack([(start + rows) / fs, bits[:, rows].T]), fmt=fmt, delimiter=",")
            total += rows.size
            prev = bits[:, -1].copy()
    return total


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
