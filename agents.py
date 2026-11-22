"""
agents.py — NetCare AI
Bridge module exposing the upgraded Multi-Agent Orchestration Architecture
while maintaining backwards-compatibility with existing tests and routes.
Five specialized agents powered by a single shared fine-tuned foundation model:
- Coordinator Agent
- Diagnosis Agent
- Troubleshooting Agent
- Monitoring Agent
- Escalation Agent
"""

import os
import database as db
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
from agents.coordinator import CoordinatorAgent
from agents.diagnosis import DiagnosisAgent
from agents.troubleshooting import TroubleshootingAgent
from agents.monitoring import MonitoringAgent
from agents.escalation import EscalationAgent
from model.configuration import MODEL_NAME
from model.inference import classify_issue, generate_agent_response

# Global flags
GEMINI_ACTIVE = False
LAST_MODEL_USED = MODEL_NAME


def _gemini(prompt: str, fallback: str) -> str:
    """Offline domain-adapted generation fallback (Gemini removed as primary intelligence)."""
    return fallback


coordinator = CoordinatorAgent()
