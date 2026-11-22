"""
tests/test_agents.py — NetCare AI
Individual unit tests for all FIVE specialized agents:
1. Coordinator Agent
2. Diagnosis Agent
3. Troubleshooting Agent
4. Monitoring Agent
5. Escalation Agent
"""

import os
import sys
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import database as db
from agents.coordinator import CoordinatorAgent
from agents.diagnosis import DiagnosisAgent
from agents.troubleshooting import TroubleshootingAgent
from agents.monitoring import MonitoringAgent
from agents.escalation import EscalationAgent


@pytest.fixture(autouse=True)
def setup_db():
    db.init_db()


def test_coordinator_agent():
    coord = CoordinatorAgent()
    sid = db.create_session("NET1001", "router_disconnected")
    res = coord.process_incoming_query(sid, "NET1001", "My router internet light is off.", "router_disconnected")

    assert "error" not in res
    assert res["customer"]["name"] == "Aarav Sharma"
    assert "classification" in res
    assert res["routed_agent"] in ["Diagnosis Agent", "Escalation Agent"]
    assert len(res["welcome_message"]) > 0


def test_diagnosis_agent():
    diag = DiagnosisAgent()
    sid = db.create_session("NET1002", "device_connectivity")
    cust = db.get_customer("NET1002")
    res = diag.diagnose(sid, "Laptop won't connect to Wi-Fi", "device_connectivity", cust)

    assert "root_cause" in res
    assert res["confidence"] > 0.0
    assert "severity" in res
    assert "checks" in res
    assert isinstance(res["checks"], list)


def test_troubleshooting_agent():
    ts = TroubleshootingAgent()
    sid = db.create_session("NET1001", "router_disconnected")
    step1 = ts.get_next_action(sid, "router_wan_issue", [])

    assert step1 is not None
    assert "action" in step1
    assert "instructions" in step1

    # Anti-looping: step2 must differ from step1
    step2 = ts.get_next_action(sid, "router_wan_issue", [step1["action"]])
    if step2:
        assert step2["action"] != step1["action"]


def test_monitoring_agent():
    mon = MonitoringAgent()
    sid = db.create_session("NET1001", "router_disconnected")

    # Succeeded feedback
    obs_success = mon.observe(sid, "restart_router", "it worked, internet is back")
    assert obs_success["resolved"] is True
    assert obs_success["adaptation_needed"] is False

    # Failed feedback
    obs_fail = mon.observe(sid, "restart_router", "still not working, red light")
    assert obs_fail["resolved"] is False
    assert obs_fail["adaptation_needed"] is True


def test_escalation_agent():
    esc = EscalationAgent()
    sid = db.create_session("NET1003", "isp_outage")
    cust = db.get_customer("NET1003")
    ticket = esc.escalate(sid, cust, "isp_outage", ["restart_router", "check_cables"])

    assert ticket["ticket_id"].startswith("TKT-")
    assert ticket["priority"] == "High"
    assert "steps_attempted" in ticket
    assert "message" in ticket
    # Verify ticket was saved in SQLite
    saved = db.get_ticket(ticket["ticket_id"])
    assert saved is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
