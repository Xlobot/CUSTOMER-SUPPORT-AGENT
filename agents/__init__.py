"""
agents/__init__.py — NetCare AI
Exposes the five specialized agents and the orchestration interface:
- CoordinatorAgent
- DiagnosisAgent
- TroubleshootingAgent
- MonitoringAgent
- EscalationAgent
"""

from agents.coordinator import CoordinatorAgent
from agents.diagnosis import DiagnosisAgent
from agents.troubleshooting import TroubleshootingAgent
from agents.monitoring import MonitoringAgent
from agents.escalation import EscalationAgent

from orchestration.orchestrator import (
    orchestrator,
    start_session,
    process_feedback,
    send_customer_message,
    get_session_data,
    SCENARIOS,
    AVAILABLE_MODELS,
    get_current_model,
    set_current_model,
    test_model_connection
)
from model.configuration import MODEL_NAME

GEMINI_ACTIVE = False
LAST_MODEL_USED = MODEL_NAME

def _gemini(prompt: str, fallback: str) -> str:
    return fallback
