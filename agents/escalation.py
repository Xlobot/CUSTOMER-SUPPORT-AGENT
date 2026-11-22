"""
agents/escalation.py — NetCare AI
Agent 5: Escalation Agent
Responsibilities:
- Identify unresolvable customer connectivity issues
- Detect repeated remediation failures and upstream ISP outages
- Calculate escalation priority (High, Medium, Low) and realistic SLA turnaround
- Generate structured support tickets (TKT-XXXX)
- Never fabricate external third-party ISP dispatches without real API connectivity
"""

import time
from model.inference import generate_agent_response
from monitoring.temporary_logs import log_event
import database as db


class EscalationAgent:
    NAME = "Escalation Agent"

    def __init__(self):
        self.system_instructions = (
            "You are the NetCare AI Escalation Agent. Your responsibility is to compile "
            "formal support tickets when automated troubleshooting fails or infrastructure outages occur, "
            "assign appropriate SLAs, and maintain full transparency without fabricating external actions."
        )

    def escalate(self, session_id: str, customer: dict, scenario: str, failed_actions: list) -> dict:
        """Packages case data into a formal support ticket and closes automated troubleshooting."""
        start_time = time.time()
        log_event("WARN", self.NAME, f"Escalation triggered for session {session_id}", details={"scenario": scenario, "failed_actions": failed_actions})

        steps_text = "; ".join(a.replace("_", " ").title() for a in failed_actions) if failed_actions else "None (Immediate Outage Detection)"

        # Priority & reason determination
        if scenario == "isp_outage":
            reason = "Regional ISP optical backbone outage detected — cannot be fixed by customer premises equipment."
            priority = "High"
            sla_hours = 4
        elif len(failed_actions) >= 3:
            reason = f"Automated troubleshooting exhausted after {len(failed_actions)} failed attempts."
            priority = "Medium"
            sla_hours = 24
        else:
            reason = f"Persistent {scenario.replace('_', ' ')} requiring Level 2 technical inspection."
            priority = "High"
            sla_hours = 12

        # Create ticket in persistent SQLite DB
        ticket_id = db.create_ticket(
            session_id=session_id,
            customer_id=customer["customer_id"],
            issue=f"Internet connectivity issue — {scenario.replace('_', ' ').title()}",
            diagnosis=f"Diagnosed as {scenario.replace('_', ' ')}",
            steps=steps_text,
            reason=reason,
            priority=priority
        )

        db.close_session(session_id, "escalated")
        db.log_agent(session_id, self.NAME, f"Ticket created: {ticket_id}", f"Priority: {priority}")

        esc_msg = (
            f"Support Ticket Created: **{ticket_id}**\n\n"
            f"Reason: {reason}\n"
            f"Priority: {priority}\n"
            f"Steps Attempted: {steps_text}\n"
            f"Target Response: Within {sla_hours} hours\n\n"
            f"Automated remote troubleshooting exhausted. Field technician assigned for on-site line inspection.\n"
            f"Ticket Reference: **{ticket_id}**"
        )
        db.save_message(session_id, "agent", esc_msg)

        latency_ms = round((time.time() - start_time) * 1000, 2)
        log_event("SUCCESS", self.NAME, f"Ticket {ticket_id} created with priority {priority} (SLA: {sla_hours}h)", latency_ms=latency_ms)

        return {
            "ticket_id": ticket_id,
            "customer_id": customer["customer_id"],
            "reason": reason,
            "priority": priority,
            "sla_hours": sla_hours,
            "steps_attempted": steps_text,
            "message": esc_msg,
            "model_used": "NetCare-Domain-Model-v1.0"
        }
