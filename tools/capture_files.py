"""Shared loading for atk-dl16 capture folders: meta.json plus chNN.bits (eight samples per byte, LSB first)."""
import json
from pathlib import Path

import numpy as np


def load_meta(cap: Path) -> dict:
    return json.loads((cap / "meta.json").read_text(encoding="utf-8"))


def load_channel(cap: Path, ch: int, n: int) -> np.ndarray:
    """Samples 0..n-1 of one channel. Exits if the file holds fewer than the n samples meta.json declares."""
    path = cap / f"ch{ch:02d}.bits"
    raw = np.fromfile(path, dtype=np.uint8)
    if raw.size * 8 < n:
        raise SystemExit(f"{path}: holds {raw.size * 8} samples, but meta.json declares {n}")
    return np.unpackbits(raw, bitorder="little")[:n]
