"""
orchestration/state.py — NetCare AI
State definitions and transitions for multi-agent workflows.
"""

from enum import Enum


class AgentState(str, Enum):
    IDLE = "IDLE"
    INITIALIZING = "INITIALIZING"
    DIAGNOSING = "DIAGNOSING"
    TROUBLESHOOTING = "TROUBLESHOOTING"
    OBSERVING = "OBSERVING"
    ADJUSTING = "ADJUSTING"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"
    FAILED = "FAILED"


VALID_TRANSITIONS = {
    AgentState.IDLE: [AgentState.INITIALIZING],
    AgentState.INITIALIZING: [AgentState.DIAGNOSING, AgentState.ESCALATED],
    AgentState.DIAGNOSING: [AgentState.TROUBLESHOOTING, AgentState.ESCALATED],
    AgentState.TROUBLESHOOTING: [AgentState.OBSERVING],
    AgentState.OBSERVING: [AgentState.ADJUSTING, AgentState.RESOLVED, AgentState.ESCALATED],
    AgentState.ADJUSTING: [AgentState.TROUBLESHOOTING, AgentState.ESCALATED],
    AgentState.RESOLVED: [],
    AgentState.ESCALATED: []
}
