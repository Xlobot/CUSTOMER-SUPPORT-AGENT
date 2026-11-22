"""
monitoring/temporary_logs.py — NetCare AI
In-Memory Volatile Logging Ring Buffer for Real-Time Backend Monitoring.
CRITICAL DESIGN REQUIREMENT:
- All runtime backend logs and live activity logs are stored in temporary RAM storage ONLY.
- They are NEVER permanently written to SQLite or disk files.
- Resets completely when server shuts down or restarts.
- Provides thread-safe append and retrieval for the /monitoring web view.
"""

import time
from collections import deque
from threading import Lock

# Max entries kept in memory
MAX_TEMPORARY_LOGS = 500

_LOG_LOCK = Lock()
_IN_MEMORY_LOG_BUFFER = deque(maxlen=MAX_TEMPORARY_LOGS)


def log_event(level: str, agent_name: str, activity: str, result: str = "", details: dict = None, latency_ms: float = None):
    """Appends an operational log event to the in-memory circular ring buffer."""
    entry = {
        "id": int(time.time() * 1000),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "level": level.upper(),  # 'INFO' | 'WARN' | 'ERROR' | 'SUCCESS'
        "agent_name": agent_name,
        "activity": activity,
        "result": result,
        "details": details or {},
        "latency_ms": latency_ms
    }

    with _LOG_LOCK:
        _IN_MEMORY_LOG_BUFFER.appendleft(entry)


def get_temporary_logs(limit: int = 100, level: str = None, agent: str = None) -> list:
    """Retrieves the most recent in-memory log events."""
    with _LOG_LOCK:
        logs = list(_IN_MEMORY_LOG_BUFFER)

    filtered = logs
    if level:
        filtered = [l for l in filtered if l["level"] == level.upper()]
    if agent:
        filtered = [l for l in filtered if l["agent_name"].lower() == agent.lower()]

    return filtered[:limit]


def clear_temporary_logs():
    """Clears all in-memory temporary logs."""
    with _LOG_LOCK:
        _IN_MEMORY_LOG_BUFFER.clear()
    log_event("INFO", "Server Monitoring", "Temporary log buffer cleared by administrator.")
