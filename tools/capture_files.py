"""Shared loading for atk-dl16 capture folders: meta.json plus chNN.bits (eight samples per byte, LSB first)."""
import json
from pathlib import Path

import numpy as np


def load_meta(cap: Path) -> dict:
    return json.loads((cap / "meta.json").read_text(encoding="utf-8"))


def map_channel(cap: Path, ch: int, n: int) -> np.ndarray:
    """Packed bytes of one channel, memory-mapped. Exits if the file holds fewer than the n samples meta.json declares."""
    path = cap / f"ch{ch:02d}.bits"
    size = path.stat().st_size
    if size * 8 < n:
        raise SystemExit(f"{path}: holds {size * 8} samples, but meta.json declares {n}")
    if size == 0:
        return np.zeros(0, dtype=np.uint8)  # np.memmap can't map an empty file
    return np.memmap(path, dtype=np.uint8, mode="r")


def load_window(cap: Path, ch: int, n: int, a: int, b: int) -> np.ndarray:
    """Samples a..b-1 of one channel, unpacking only the bytes that hold them."""
    packed = map_channel(cap, ch, n)[a // 8:(b + 7) // 8]
    return np.unpackbits(packed, bitorder="little")[a % 8:a % 8 + (b - a)]


def load_channel(cap: Path, ch: int, n: int) -> np.ndarray:
    """All n samples of one channel, unpacked to one uint8 per sample."""
    return load_window(cap, ch, n, 0, n)
