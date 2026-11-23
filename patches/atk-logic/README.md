# ATK-Logic GUI hardening patches

Patches for the upstream ATK-Logic GUI ([alientek-openedv/atk-logic](https://github.com/alientek-openedv/atk-logic), GPL-3.0). They close a path-traversal hole and code-execution paths, switch off the unsigned updater and firmware download, and let the GUI accept DL16 Plus units on FPGA 2.22. They were used for a Release x64 build with Qt 5.15.2 (msvc2019_64) and vcpkg glib and libusb. The headless CLI and MCP server in this repository don't need them.

| File | Apply in | Purpose |
| --- | --- | --- |
| `atk-logic-source-edits.diff` | atk-logic checkout | Security fixes, update and firmware stubs, FPGA 2.22 acceptance, MSVC build wiring |
| `atk_libsigrokdecode.diff` | atk_libsigrokdecode source | Initializes `num_conditions` in `_skip_process` (`instance.c`) |
| `atk_libsigrokdecode-msvc-CMakeLists.txt` | its own folder next to the decoder source | Out-of-tree MSVC build of atk_libsigrokdecode, which upstream only builds with autotools |
| `build-release.cmd` | work dir | Rebuilds the decoder library and the app, Release only |

Apply each diff from the root of its source tree with `git apply <file>`.

## What the source edits change

- **Zip-slip in `.atkdl` loading** (`pv/static/zip_helper.cpp`): archive entries whose names contain `..` or `:`, start with a slash or are absolute, or resolve outside the target folder are skipped instead of written.
- **Firmware download and auto-flash stubbed** (`pv/thread/thread_download.cpp`, `pv/draw/frameless_window.cpp`, `pv/static/data_service.h`): the HTTP firmware download, MCU and FPGA flashing and bootloader entry are no-ops, and the plain-HTTP download address is blanked. `pv/thread/connect.cpp` no longer pushes a device into the bootloader when its MCU cache looks wrong, and a device already in bootloader mode is reported but never flashed. This also removes a read of `data2->buf` right after `delete[]`.
- **Unsigned self-updater removed** (`frameless_window.cpp`, `resource.qrc`): `updateApp()` no longer extracts and launches the embedded `update_x64.exe` or `update_x86.exe`, and both are dropped from the resources.
- **Automatic HTTP version checks disabled** (`connect.cpp`, `frameless_window.cpp`, `qml/main.qml`): no software or firmware update check at startup or on connect.
- **FPGA 2.22 accepted** (`ATK-Logic.pro`): `VERSION` 1.1.0.8 and `APP_VERSION_NUM=1108`. FPGA 2.22 units ask for app version 1108 or newer, so this bypasses that minimum-version check rather than adding anything new.
- **MSVC build fixes** (`ATK-Logic.pro`, `main.cpp`): adds the platform `qtlockedfile` source, takes headers and libraries from `ATK_DEPS_DIR` (`qmake ATK_DEPS_DIR=<dir>`), and drops the Breakpad crash handler, which this build doesn't include.

## Decoders that can run commands or Python

Three bundled sigrok decoders execute code taken from decoder settings, which can come from an `.atkdl` project file as well as from the UI. Delete them from the GUI's `runtime/decoders/` folder:

- `arm_etmv3` and `arm_itm` run their `objdump` and `objdump_opts` options through `subprocess`, so a settings value can launch any program.
- `numbers_and_state` runs `exec()` on the user-supplied mapping text, which is arbitrary Python.

```powershell
Remove-Item -Recurse -Force runtime\decoders\arm_etmv3, runtime\decoders\arm_itm, runtime\decoders\numbers_and_state
```

This only loses ARM ETMv3 and ITM trace decoding and the numbers-and-state decoder. It isn't shipped as a diff, because the diff would just contain the deleted upstream files.

## Building

`build-release.cmd` expects this work dir layout and an existing Visual Studio 2026 Community install (it calls its `vcvars64.bat` and bundled CMake; edit the paths for other editions):

| Path | Contents |
| --- | --- |
| `src\` | atk-logic checkout with `atk-logic-source-edits.diff` applied |
| `srd\` | atk_libsigrokdecode source with `atk_libsigrokdecode.diff` applied |
| `srd-msvc\CMakeLists.txt` | copy of `atk_libsigrokdecode-msvc-CMakeLists.txt` |
| `vcpkg\installed\x64-windows-rel\` | vcpkg glib and libusb |
| `python-nuget\tools\` | Python from the NuGet `python` package (`include\`, `libs\python3.lib`) |
| `Qt\5.15.2\msvc2019_64\` | Qt 5.15.2 |
| `jom\jom.exe` | jom |
| `deps\include\`, `deps\lib\` | headers and import libraries for libusb, glib and Python; the script copies `atk_decoder.lib` into `deps\lib\` |

The script builds `atk_decoder.lib` (static) and `irmp.dll`, then `build-app\release\ATK-Logic.exe`. To run it, deploy with `windeployqt` and copy the glib, libusb and Python DLLs and `irmp.dll` next to the exe.
