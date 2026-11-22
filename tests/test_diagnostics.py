"""
tests/test_diagnostics.py — NetCare AI
Unit tests for safe local network diagnostics on Windows (ping, DNS, gateway).
"""

import os
import sys
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from diagnostics.network_tools import (
    ping_host,
    check_dns_resolution,
    check_default_gateway,
    run_comprehensive_diagnostics
)


def test_safe_dns_resolution():
    """Verify socket DNS lookup."""
    res = check_dns_resolution("google.com")
    assert "status" in res
    assert res["type"] == "REAL_LOCAL_DIAGNOSTIC"
    assert "latency_ms" in res


def test_safe_ping():
    """Verify Windows ping command execution."""
    res = ping_host("127.0.0.1", count=1, timeout_ms=500)
    assert res["type"] == "REAL_LOCAL_DIAGNOSTIC"
    assert res["status"] in ["PASS", "FAIL"]
    assert "packet_loss_pct" in res


def test_comprehensive_diagnostics():
    """Verify composite diagnostic routine with transparent telemetry."""
    res = run_comprehensive_diagnostics(scenario_override="isp_outage")
    assert "checks" in res
    assert len(res["checks"]) >= 3
    # Check that simulated scenarios are labeled transparently
    simulated_checks = [c for c in res["checks"] if c["type"] == "SIMULATED_SCENARIO"]
    assert len(simulated_checks) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
