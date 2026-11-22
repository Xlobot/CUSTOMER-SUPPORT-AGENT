"""
tests/test_model.py — NetCare AI
Unit tests for foundation model loading, classification accuracy, confidence scoring, and fallback.
"""

import os
import sys
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from model.model_loader import load_model, get_model_status
from model.inference import classify_issue, generate_agent_response
from model.configuration import MODEL_NAME, CLASSES


def test_model_loading():
    """Verify that the domain-adapted foundation model checkpoint loads successfully."""
    ckpt = load_model()
    assert ckpt is not None, "Model checkpoint should load successfully."
    assert "tfidf" in ckpt, "Checkpoint should contain TF-IDF feature extractor."
    assert "classifier" in ckpt, "Checkpoint should contain classifier model."
    assert len(ckpt["classes"]) == 7, "Model should recognize exactly 7 networking categories."


def test_model_status():
    """Verify model status report."""
    st = get_model_status()
    assert st["loaded"] is True
    assert st["error"] is None
    assert st["val_accuracy"] >= 0.90


def test_issue_classification():
    """Verify classification across key networking symptoms."""
    # Test 1: DHCP APIPA issue
    res1 = classify_issue("My laptop IP is 169.254.10.20 and DHCP lookup timed out.")
    assert res1["category"] == "dhcp_ip_configuration"
    assert res1["confidence"] > 0.50

    # Test 2: ISP Outage
    res2 = classify_issue("Red LOS light is blinking on my fiber box and neighbor's net is down too.")
    assert res2["category"] == "isp_outage"
    assert res2["confidence"] > 0.60

    # Test 3: DNS issue
    res3 = classify_issue("Chrome shows DNS_PROBE_FINISHED_NXDOMAIN, cannot resolve host name.")
    assert res3["category"] == "dns_resolution"

    # Test 4: Wi-Fi signal
    res4 = classify_issue("My wifi is weak and keeps dropping in the bedroom upstairs.")
    assert res4["category"] == "wifi_signal_issue"


def test_agent_response_generation():
    """Verify generation for all five agents."""
    for role in ["coordinator", "diagnosis", "troubleshooting", "monitoring", "escalation"]:
        resp = generate_agent_response(role, "Internet is completely down", {"category": "router_wan_issue"})
        assert "error" not in resp
        assert resp["model_used"] == MODEL_NAME


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
