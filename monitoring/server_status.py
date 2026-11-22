"""
monitoring/server_status.py — NetCare AI
Server status, uptime, request counter, error tracker, and active model metrics.
"""

import time
import os

_SERVER_START_TIME = time.time()
_REQUEST_COUNTERS = {
    "total_requests": 0,
    "api_requests": 0,
    "agent_invocations": 0,
    "errors": 0
}


def record_request(is_api: bool = True, is_agent: bool = False, is_error: bool = False):
    """Tracks global server activity counters."""
    _REQUEST_COUNTERS["total_requests"] += 1
    if is_api:
        _REQUEST_COUNTERS["api_requests"] += 1
    if is_agent:
        _REQUEST_COUNTERS["agent_invocations"] += 1
    if is_error:
        _REQUEST_COUNTERS["errors"] += 1


def get_uptime_seconds() -> float:
    return time.time() - _SERVER_START_TIME


def get_formatted_uptime() -> str:
    secs = int(get_uptime_seconds())
    hours, remainder = divmod(secs, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}h {minutes:02d}m {seconds:02d}s"


def get_server_status():
    from model.model_loader import get_model_status
    model_st = get_model_status()

    return {
        "status": "online",
        "uptime": get_formatted_uptime(),
        "uptime_seconds": round(get_uptime_seconds(), 1),
        "server_start_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(_SERVER_START_TIME)),
        "counters": _REQUEST_COUNTERS,
        "model_status": {
            "loaded": model_st.get("loaded", False),
            "model_name": model_st.get("model_name", "Unknown"),
            "val_accuracy": model_st.get("val_accuracy", 0.0),
            "last_loaded_at": model_st.get("last_loaded_at"),
            "load_duration_ms": model_st.get("load_duration_ms", 0)
        }
    }
