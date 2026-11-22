"""
tests/test_temporary_logs.py — NetCare AI
Unit tests verifying that runtime backend logs are stored strictly in-memory (volatile RAM)
and NEVER persisted to SQLite database or permanent disk files.
"""

import os
import sys
import sqlite3
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from monitoring.temporary_logs import log_event, get_temporary_logs, clear_temporary_logs
import database as db


def test_temporary_logging_in_memory():
    """Verify log events appear in RAM buffer."""
    clear_temporary_logs()
    log_event("INFO", "Test Agent", "Sample test activity", "Success")

    logs = get_temporary_logs(limit=10)
    assert len(logs) >= 1
    assert any(l["activity"] == "Sample test activity" for l in logs)


def test_logs_not_persisted_to_sqlite():
    """Verify that runtime debug logs do not pollute permanent SQLite tables."""
    clear_temporary_logs()
    test_msg = "UNIQUE_IN_MEMORY_PROBE_998877"
    log_event("INFO", "Coordinator Agent", test_msg)

    # Check that this log was NOT inserted into SQLite database
    conn = db.get_connection()
    row = conn.execute("SELECT COUNT(*) FROM agent_logs WHERE activity = ?", (test_msg,)).fetchone()
    conn.close()

    assert row[0] == 0, "Temporary backend logs must NOT be permanently written to SQLite."


def test_clear_temporary_logs():
    """Verify RAM clearing resets in-memory buffer."""
    log_event("WARN", "Test Agent", "Before clear")
    clear_temporary_logs()
    logs = get_temporary_logs()
    assert len(logs) <= 1  # Only the clear notification itself remains


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
