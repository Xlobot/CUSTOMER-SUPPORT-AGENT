"""
diagnostics/network_tools.py — NetCare AI
Safe Local Network Diagnostics and Telemetry Probing for Windows 11.
Safety & Reliability Guarantees:
- Read-only queries only. Never modifies Windows network adapter or router configuration.
- Distinguishes clearly between [REAL LOCAL DIAGNOSTIC] and [SIMULATED SCENARIO].
- Never collects customer credentials, keys, or passwords.
"""

import os
import sys
import subprocess
import socket
import time
import re

from monitoring.temporary_logs import log_event


def ping_host(host: str = "8.8.8.8", count: int = 1, timeout_ms: int = 1000) -> dict:
    """Safely pings an IP address or hostname using native OS ping (Windows/Linux)."""
    start_time = time.time()
    try:
        if sys.platform == "win32":
            cmd = ["ping", "-n", str(count), "-w", str(timeout_ms), host]
        else:
            timeout_sec = max(1, timeout_ms // 1000)
            cmd = ["ping", "-c", str(count), "-W", str(timeout_sec), host]

        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3)
        duration_ms = round((time.time() - start_time) * 1000, 1)

        output = res.stdout + ("\n" + res.stderr if res.stderr else "")
        is_success = ("ttl=" in output.lower() or "reply from" in output.lower() or "bytes from" in output.lower()) and res.returncode == 0

        # Extract round trip time if present (e.g. time=14ms or time=14.2 ms)
        match = re.search(r"time[<=]?(\d+(?:\.\d+)?) ?ms", output, re.IGNORECASE)
        latency_ms = float(match.group(1)) if match else (duration_ms if is_success else None)
        if latency_ms is not None:
            latency_ms = round(latency_ms, 1)

        result = {
            "check": f"Ping ({host})",
            "type": "REAL_LOCAL_DIAGNOSTIC",
            "target": host,
            "status": "PASS" if is_success else "FAIL",
            "latency_ms": latency_ms,
            "packet_loss_pct": 0 if is_success else 100,
            "raw_output": output.strip()[:180]
        }
        log_event("INFO", "Diagnosis Agent", f"Safe ping executed to {host}", result="PASS" if is_success else "FAIL")
        return result
    except Exception as e:
        log_event("WARN", "Diagnosis Agent", f"Ping failed: {str(e)}")
        return {
            "check": f"Ping ({host})",
            "type": "REAL_LOCAL_DIAGNOSTIC",
            "target": host,
            "status": "FAIL",
            "latency_ms": None,
            "packet_loss_pct": 100,
            "error": str(e)
        }


def check_dns_resolution(domain: str = "google.com") -> dict:
    """Tests socket-level DNS resolution speed and reachability."""
    start_time = time.time()
    try:
        resolved_ip = socket.gethostbyname(domain)
        duration_ms = round((time.time() - start_time) * 1000, 2)
        result = {
            "check": f"DNS Resolution ({domain})",
            "type": "REAL_LOCAL_DIAGNOSTIC",
            "domain": domain,
            "resolved_ip": resolved_ip,
            "status": "PASS",
            "latency_ms": duration_ms
        }
        log_event("INFO", "Diagnosis Agent", f"DNS query for {domain} resolved to {resolved_ip}", result="PASS")
        return result
    except Exception as e:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        log_event("WARN", "Diagnosis Agent", f"DNS query for {domain} failed: {str(e)}")
        return {
            "check": f"DNS Resolution ({domain})",
            "type": "REAL_LOCAL_DIAGNOSTIC",
            "domain": domain,
            "status": "FAIL",
            "latency_ms": duration_ms,
            "error": "Resolution timed out or NXDOMAIN"
        }


def check_default_gateway() -> dict:
    """Checks default gateway IP reachability via local routing."""
    # Test local gateway probe safely
    gw_result = ping_host("192.168.1.1", count=1, timeout_ms=500)
    if gw_result["status"] == "FAIL":
        # Check alternate standard gateway 192.168.0.1
        gw_result2 = ping_host("192.168.0.1", count=1, timeout_ms=500)
        if gw_result2["status"] == "PASS":
            return gw_result2
    return gw_result


def run_comprehensive_diagnostics(scenario_override: str = None) -> dict:
    """
    Executes real safe local checks and incorporates transparent scenario conditions
    when evaluating specific simulated faults.
    """
    real_ping_dns = ping_host("8.8.8.8", count=1, timeout_ms=800)
    real_dns_query = check_dns_resolution("google.com")
    real_gateway = check_default_gateway()

    # Distinguish simulated scenario test if requested
    checks = [
        real_gateway,
        real_dns_query,
        real_ping_dns
    ]

    # If testing a known scenario, append scenario telemetry
    if scenario_override == "isp_outage":
        checks.append({
            "check": "ISP Feeder Optical Link",
            "type": "SIMULATED_SCENARIO",
            "target": "OLT Backbone Optical Fiber",
            "status": "FAIL",
            "details": "Optical Loss of Signal (LOS blinking red) detected on area node."
        })
    elif scenario_override == "dhcp_ip_configuration":
        checks.append({
            "check": "DHCP Lease Status",
            "type": "SIMULATED_SCENARIO",
            "target": "Router DHCP Server",
            "status": "FAIL",
            "details": "Client self-assigned APIPA 169.254.x.x; DHCPOffer timed out."
        })
    else:
        checks.append({
            "check": "ISP Backbone Connectivity",
            "type": "SIMULATED_SCENARIO",
            "target": "ISP Upstream Gateway",
            "status": "PASS",
            "details": "Upstream aggregation router is operational."
        })

    all_passed = all(c["status"] == "PASS" for c in checks if c["type"] == "REAL_LOCAL_DIAGNOSTIC")

    return {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "overall_status": "HEALTHY" if all_passed else "ATTENTION_REQUIRED",
        "checks": checks,
        "summary": "Local network diagnostics completed safely without configuration changes."
    }
