"""
agents/troubleshooting.py — NetCare AI
Agent 3: Troubleshooting Agent
Responsibilities:
- Generate structured, step-by-step customer-friendly remediation procedures
- Tailor instructions to non-technical users
- Track prior failed steps to prevent repetitive looping (anti-looping safeguard)
- Require affirmative customer confirmation before any potentially disruptive operation
"""

import time
from model.inference import generate_agent_response
from monitoring.temporary_logs import log_event
import database as db


class TroubleshootingAgent:
    NAME = "Troubleshooting Agent"

    def __init__(self):
        self.system_instructions = (
            "You are the NetCare AI Troubleshooting Agent. Your role is to provide clear, "
            "step-by-step, non-repetitive troubleshooting procedures, warn before disruptive actions, "
            "and verify each remediation attempt."
        )

    def get_next_action(self, session_id: str, scenario: str, failed_actions: list) -> dict | None:
        """Determines the next non-failed remediation action."""
        start_time = time.time()
        log_event("INFO", self.NAME, f"Selecting next troubleshooting step for session {session_id}", details={"failed_actions": failed_actions})

        # Call shared model troubleshooting generator
        ts_resp = generate_agent_response("troubleshooting", scenario, {
            "category": scenario,
            "failed_steps": failed_actions
        })

        if ts_resp.get("exhausted") or not ts_resp.get("action"):
            log_event("WARN", self.NAME, f"All remediation actions exhausted for session {session_id}")
            db.log_agent(session_id, self.NAME, "All troubleshooting steps exhausted. Escalation required.", "Exhausted")
            return None

        action_key = ts_resp["action"]
        label = ts_resp["label"]
        instructions = ts_resp["instructions"]
        is_disruptive = ts_resp.get("disruptive", False)

        # Log attempt in DB
        db.save_attempt(session_id, action_key, "ACT")
        db.log_agent(
            session_id, self.NAME,
            f"Recommending action: {label}",
            f"Prior failed: {failed_actions}"
        )

        latency_ms = round((time.time() - start_time) * 1000, 2)
        log_event("SUCCESS", self.NAME, f"Action recommended: {label} (Disruptive: {is_disruptive})", latency_ms=latency_ms)

        return {
            "action": action_key,
            "label": label,
            "instructions": instructions,
            "disruptive": is_disruptive,
            "requires_confirmation": is_disruptive,
            "model_used": ts_resp.get("model_used")
        }
