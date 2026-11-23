"""Tests for the capture scripts in tools/, run against a small synthetic capture folder."""
import importlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
CH0 = [0, 0, 1, 1, 1, 0, 0, 0, 1, 1]
CH3 = [1, 1, 1, 1, 0, 0, 0, 0, 0, 0]


def _write_capture(root: Path) -> Path:
    cap = root / "cap_test"
    cap.mkdir()
    for ch, bits in ((0, CH0), (3, CH3)):
        np.packbits(np.array(bits, dtype=np.uint8), bitorder="little").tofile(cap / f"ch{ch:02d}.bits")
    meta = {"capture_id": "cap_test", "sample_rate": 1_000_000, "actual_samples": len(CH0),
            "threshold_voltage": 1.6, "channels": [0, 3]}
    (cap / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return cap


def _run(script: str, *args) -> None:
    proc = subprocess.run([sys.executable, str(TOOLS / script), *map(str, args)],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr


def test_bits2csv_writes_change_only_rows(tmp_path):
    cap = _write_capture(tmp_path)
    out = tmp_path / "out.csv"
    _run("bits2csv.py", cap, "-o", out)
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[:3] == ["; Sample rate: 1 MHz", "; Sample count: 10", "Time(s),0,3"]
    assert lines[3:] == [
        "0.0000000000,0,1",
        "0.0000020000,1,1",
        "0.0000040000,1,0",
        "0.0000050000,0,0",
        "0.0000080000,1,0",
        "0.0000090000,1,0",
    ]


def test_bits2csv_batches_match_single_pass(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(TOOLS))
    bits2csv = importlib.import_module("bits2csv")
    cap = _write_capture(tmp_path)
    whole, batched = tmp_path / "whole.csv", tmp_path / "batched.csv"
    bits2csv.convert(cap, whole)
    monkeypatch.setattr(bits2csv, "CHUNK", 8)  # splits the 10 samples across a batch boundary
    bits2csv.convert(cap, batched)
    assert batched.read_text(encoding="utf-8") == whole.read_text(encoding="utf-8")


def test_load_window_handles_bit_offsets(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(TOOLS))
    capture_files = importlib.import_module("capture_files")
    cap = _write_capture(tmp_path)
    assert capture_files.load_window(cap, 0, 10, 3, 9).tolist() == CH0[3:9]
    assert capture_files.load_window(cap, 3, 10, 7, 10).tolist() == CH3[7:10]


def test_view_embeds_edges_labels_and_window(tmp_path):
    cap = _write_capture(tmp_path)
    cfg = tmp_path / "view.json"
    cfg.write_text(json.dumps({"labels": {"3": "</script>CS"}, "order": [3], "view_us": [1, 8]}))
    _run("view.py", cap, "--config", cfg)
    html = (cap / "viewer.html").read_text(encoding="utf-8")
    assert "</script>CS" not in html
    data, _ = json.JSONDecoder().raw_decode(html, html.index("const D=") + len("const D="))
    assert data["chans"] == [
        {"ch": 3, "label": "</script>CS", "init": 1, "edges": [4], "high": 0.4},
        {"ch": 0, "label": "", "init": 0, "edges": [2, 5, 8], "high": 0.5},
    ]
    assert data["view"] == [1, 8]


@pytest.mark.parametrize("view_us", [[10, 20], [20, 30], [5, 5]])
def test_view_rejects_window_without_samples(tmp_path, view_us):
    cap = _write_capture(tmp_path)
    cfg = tmp_path / "view.json"
    cfg.write_text(json.dumps({"view_us": view_us}))
    proc = subprocess.run([sys.executable, str(TOOLS / "view.py"), str(cap), "--config", str(cfg)],
                          capture_output=True, text=True)
    assert proc.returncode != 0
    assert "selects no samples" in proc.stderr
    assert not (cap / "viewer.html").exists()


def test_plot_writes_png(tmp_path):
    pytest.importorskip("matplotlib")
    cap = _write_capture(tmp_path)
    out = tmp_path / "plot.png"
    _run("plot.py", cap, "--channels", "3,0", "--start-us", "1", "--end-us", "9", "-o", out)
    assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


@pytest.mark.parametrize("script", ["bits2csv.py", "view.py", "plot.py"])
def test_tools_reject_truncated_channel_file(tmp_path, script):
    if script == "plot.py":
        pytest.importorskip("matplotlib")
    cap = _write_capture(tmp_path)
    (cap / "ch03.bits").write_bytes(b"\x0f")  # 8 samples; meta.json declares 10
    proc = subprocess.run([sys.executable, str(TOOLS / script), str(cap)], capture_output=True, text=True)
    assert proc.returncode != 0
    assert "holds 8 samples, but meta.json declares 10" in proc.stderr
