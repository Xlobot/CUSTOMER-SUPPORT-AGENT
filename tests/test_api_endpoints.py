"""
tests/test_api_endpoints.py — NetCare AI
Integration tests for Flask API endpoints and web portals.
"""

import os
import sys
import json
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import app
import database as db


@pytest.fixture
def client():
    app.config["TESTING"] = True
    db.init_db()
    with app.test_client() as c:
        yield c


def test_portal_routes(client):
    """Verify all 3 portals render HTTP 200."""
    r1 = client.get("/")
    assert r1.status_code == 200

    r2 = client.get("/performance")
    assert r2.status_code == 200

    r3 = client.get("/monitoring")
    assert r3.status_code == 200


def test_model_performance_endpoint(client):
    """Verify /api/model/performance endpoint returns structured evaluation metrics."""
    r = client.get("/api/model/performance")
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data["status"] == "success"
    assert "model_metrics" in data
    assert "training_history" in data
    assert "agent_evaluations" in data


def test_monitoring_status_and_logs(client):
    """Verify live monitoring endpoints."""
    r1 = client.get("/api/monitoring/status")
    assert r1.status_code == 200
    status = json.loads(r1.data)
    assert "uptime" in status
    assert "counters" in status

    r2 = client.get("/api/monitoring/logs")
    assert r2.status_code == 200
    logs = json.loads(r2.data)
    assert isinstance(logs, list)


def test_diagnostics_and_rag_endpoints(client):
    """Verify /api/diagnostics/run and /api/rag/query endpoints."""
    r_diag = client.post("/api/diagnostics/run", json={"scenario": "router_disconnected"})
    assert r_diag.status_code == 200
    diag_data = json.loads(r_diag.data)
    assert "checks" in diag_data

    r_rag = client.post("/api/rag/query", json={"query": "dns flush cache"})
    assert r_rag.status_code == 200
    rag_data = json.loads(r_rag.data)
    assert "citations" in rag_data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
