# Capture tools

Scripts for working with the capture folders written by `atk-dl16 capture` and the MCP server's `logic_capture`. A capture folder holds `meta.json` and one `chNN.bits` file per channel, packed eight samples per byte, LSB first.

The scripts need Python 3.10+ and NumPy. `plot.py` also needs matplotlib, and `mcp_probe.py` needs the `mcp` package from `requirements.txt`.

| Script | What it does |
| --- | --- |
| `view.py` | Renders a capture to `viewer.html`, a self-contained, zoomable waveform page. |
| `bits2csv.py` | Writes a change-only CSV with a sigrok/PulseView-style `Time(s),<ch>,...` header. |
| `plot.py` | Draws chosen channels over a time window as a static PNG. |
| `mcp_probe.py` | Calls the MCP server's tools from a shell, without an AI client. |

## view.py

```powershell
python tools\view.py captures\cap_1795413148654_8430
python tools\view.py --config view.json            # newest capture
```

Without a folder argument, `view.py` opens the newest capture under `$ATK_DL16_DATA_DIR\captures`, or `.\captures` if that variable isn't set. It writes `viewer.html` into the capture folder (or the `-o` path). Scroll to zoom, drag to pan and double-click to reset.

The optional config sets labels, row order and the initial window in microseconds. Channels missing from `order` follow in channel-number order:

```json
{"labels": {"1": "DCLK in", "2": "DCLK out", "8": "PWM0 loopback"}, "order": [1, 2, 8], "view_us": [0, 25]}
```

The page embeds every edge, so very busy captures produce large files.

## bits2csv.py

```powershell
python tools\bits2csv.py captures\cap_1795413148654_8430 -o dclk.csv
```

The CSV has a row at the first sample, one at each sample where any channel changes, and one at the last sample. Two `;` comment lines give the sample rate and count. The default output is `<capture folder>\<folder name>.csv`.

## plot.py

```powershell
python tools\plot.py captures\cap_1795413148654_8430 --channels 1,2,8 --start-us 0 --end-us 25 --config view.json -o dclk.png
```

Rows come from `--channels`, else the config's `order`, else every captured channel. `--start-us` and `--end-us` are measured from the start of the capture and override the config's `view_us`; without either, the whole capture is drawn. `--config` takes the same JSON as `view.py`.

## mcp_probe.py

```powershell
python tools\mcp_probe.py                              # list tools
python tools\mcp_probe.py logic_status
python tools\mcp_probe.py logic_capture @capture.json  # arguments from a file
```

`mcp_probe.py` starts `run_mcp_server.py` from this checkout over stdio with the current environment, so set `ATK_DL16_CLI` and `ATK_DL16_DATA_DIR` first if you use them. `--python` picks the interpreter that runs the server, such as the venv your MCP client uses. Arguments can be inline JSON, but `@file.json` avoids shell quoting problems.
