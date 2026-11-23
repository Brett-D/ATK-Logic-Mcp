# DL16 Plus field notes

Notes from using an ATK-DL16 Plus (MCU v1.9, FPGA v2.22) with this CLI and MCP server to debug a real board. They cover a firmware quirk that makes immediate captures look unreliable, a loopback health check, recovery from killed runs, and how to register the MCP server with GitHub Copilot.

## Immediate captures wait for every input to go LOW (FPGA 2.22)

On FPGA 2.22, an immediate capture (`--trigger immediate` in the CLI, "Instant" in the ATK-Logic GUI) doesn't start until **every connected input reads LOW**. That includes inputs on channels that aren't enabled for the capture. A line held HIGH for the whole event, such as an enable, a chip select or an idle-high bus, stalls the capture until it falls. The capture then lands at the end of the event, after the activity you wanted, so the trigger looks unreliable.

Workarounds:

- Don't connect lines that stay HIGH through the event. Unplug them from the probe harness; leaving them out of `--channels` isn't enough.
- Start the capture into the event, and give it enough `--timeout` (`timeout_s` over MCP) to wait.
- If a capture only completes when the event ends, suspect an input that was held HIGH.

## Health check: PWM0 loopback

The DL16 Plus has a PWM0 stimulus output. Jumper PWM0 to a spare channel and pass `--pwm0 100000`:

```powershell
.\build\Release\atk-dl16.exe capture --channels 1,2,8 --sample-rate 50M --duration 40ms --pwm0 100000 --out captures
```

PWM0 runs at 50 % duty for this capture only and is switched off afterwards. Over MCP, pass `pwm0_hz=100000` to `logic_capture`. A flat capture on the other channels is only trustworthy if the loopback channel shows the 100 kHz square wave. If the loopback channel is flat too, the capture didn't record the event (see the quirk above).

The CLI uses upstream ATK-Logic's encoding from `SessionController::pwmStart`: command `0x17` with payload `[0x11, period, high]`, both `uint32` little-endian in 200 MHz ticks (`period = round(200 MHz / f)`). Payload `[0x10]` stops PWM0. See [protocol.md](protocol.md#45-0x17-pwm).

`--pwm0` accepts up to 100 MHz, a two-tick period; higher values are rejected before the device is opened. The output runs at 200 MHz divided by the rounded period, so pick a frequency that divides 200 MHz evenly, such as 100 kHz, when the loopback frequency matters.

## Threshold

The comparator threshold byte is `round(|V| × 10)`, clamped to 50 (5.0 V), with bit 7 set for negative voltages. A negative threshold makes every input read HIGH. Because of the quirk above, an immediate capture at a negative threshold never starts and times out.

## Recovering from killed runs

Upstream ATK-Logic always ends a capture with Stop (`0x15`) and drains the endpoint. A CLI run killed mid-capture skipped that and left the FPGA armed. The next run then failed with `Invalid MCU version header`, or stalled at about 10 % progress. The CLI now:

- sends Stop and drains when it opens the device, before it reads the MCU version;
- skips stale non-version packets while reading the MCU version (up to 20 reads, re-sending the query after every 5 empty reads);
- drains with 16 KB reads at a 50 ms timeout until a read comes back empty (at most 1000 reads or 2 s), like upstream's "clear MCU cache" loop;
- sends Stop and drains before each capture and on every exit path (success, error or timeout).

`--timeout <sec>` (default 30) bounds the capture, including the wait for a trigger. Because every drain is capped at 2 s, the CLI's own work outside that window is bounded too: about 35 s at most to open the device and about 7 s of capture setup and cleanup, plus writing the capture files. Over MCP, `timeout_s` is passed to the CLI as `--timeout`, and the server only kills the CLI if it hasn't exited 90 s after that (45 s for `logic_status`). If calls still hang, unplug and replug the DL16.

Set `ATK_DL16_DEBUG=1` to trace every bulk read and parsed message type to stderr during a capture.

## Registering the MCP server with GitHub Copilot

GitHub Copilot reads local MCP servers from `~/.copilot/mcp-config.json`. Create a venv with the server's dependencies:

```powershell
python -m venv C:\tools\atk-dl16\venv
C:\tools\atk-dl16\venv\Scripts\python.exe -m pip install -r C:\src\ATK-Logic-Mcp\requirements.txt
```

Then add an entry that runs `run_mcp_server.py` from your checkout with that venv's Python:

```json
{
  "mcpServers": {
    "atk-dl16": {
      "type": "local",
      "command": "C:\\tools\\atk-dl16\\venv\\Scripts\\python.exe",
      "args": ["C:\\src\\ATK-Logic-Mcp\\run_mcp_server.py"],
      "env": {
        "ATK_DL16_CLI": "C:\\src\\ATK-Logic-Mcp\\build\\Release\\atk-dl16.exe",
        "ATK_DL16_DATA_DIR": "C:\\tools\\atk-dl16"
      },
      "tools": ["*"]
    }
  }
}
```

- `ATK_DL16_CLI` points at the built CLI.
- `ATK_DL16_DATA_DIR` is where captures are written, as `<dir>\captures\<capture_id>`.

To call the tools from a shell without an AI client, use [`tools/mcp_probe.py`](../tools/README.md#mcp_probepy).

## Windows build

Visual Studio 2026 (version 18) Community ships CMake but doesn't put it on `PATH`:

```powershell
$cmake = 'C:\Program Files\Microsoft Visual Studio\18\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe'
& $cmake -B build -A x64
& $cmake --build build --config Release --target atk-dl16
```

The Release CLI links the C runtime and libusb statically: `dumpbin /dependents build\Release\atk-dl16.exe` lists only `KERNEL32.dll`, so the exe can be copied anywhere on its own.
