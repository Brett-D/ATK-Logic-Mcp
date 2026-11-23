"""Contract tests for the MCP server's CLI timeouts and the logic_capture timeout_s / pwm0_hz options."""
import importlib
import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

# The package re-exports the MCPServer instance as `server`, so import the module itself.
srv = importlib.import_module("atk_dl16_mcp.server")
FAKE_CLI = Path("atk-dl16.exe")


@pytest.fixture
def fake_cli():
    with patch.object(srv, "_find_cli", return_value=FAKE_CLI):
        yield


def test_capture_passes_timeout_and_pwm0_to_cli(fake_cli):
    with patch("subprocess.run") as run:
        run.return_value.stdout = '{"success": true}'
        res = srv.logic_capture(channels=[0, 8], duration_ms=10, timeout_s=5, pwm0_hz=100_000)
    assert res == {"success": True}
    cmd = run.call_args.args[0]
    assert cmd[cmd.index("--timeout") + 1] == "5"
    assert cmd[cmd.index("--pwm0") + 1] == "100000"
    assert cmd[-1] == "--json"
    assert run.call_args.kwargs["timeout"] == 5 + srv.CAPTURE_EXIT_MARGIN_S


def test_capture_omits_pwm0_by_default(fake_cli):
    with patch("subprocess.run") as run:
        run.return_value.stdout = '{"success": true}'
        srv.logic_capture(channels=[0])
    cmd = run.call_args.args[0]
    assert "--pwm0" not in cmd
    assert cmd[cmd.index("--timeout") + 1] == "30"


def test_capture_reports_killed_cli(fake_cli):
    hung = subprocess.TimeoutExpired(cmd=[str(FAKE_CLI)], timeout=21, stderr=b"\rProgress: 10% (1/10 samples)")
    with patch("subprocess.run", side_effect=hung):
        res = srv.logic_capture(channels=[0], timeout_s=1)
    assert res["success"] is False
    assert res["error_code"] == "CLI_TIMEOUT"
    assert res["capture_complete_received"] is False
    assert res["warnings"] == ["Progress: 10% (1/10 samples)"]


def test_status_reports_info_timeout(fake_cli):
    hung = subprocess.TimeoutExpired(cmd=[str(FAKE_CLI), "info"], timeout=15)
    with patch("subprocess.run", side_effect=hung):
        res = srv.logic_status()
    assert res["ready"] is False
    assert "timed out" in res["message"]


def test_cli_rejects_pwm0_above_100mhz():
    # The range check runs before the device is opened, so this never touches hardware.
    cli = srv._find_cli()
    if not cli:
        pytest.skip("CLI not built yet")
    proc = subprocess.run([str(cli), "capture", "--json", "--pwm0", "200000000"],
                          capture_output=True, text=True, timeout=30)
    assert proc.returncode == 1
    data = json.loads(proc.stdout)
    assert data["success"] is False
    assert data["error_code"] == "INVALID_CAPTURE_CONFIG"
