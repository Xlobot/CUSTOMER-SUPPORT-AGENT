"""
agents/coordinator.py — NetCare AI
Agent 1: Coordinator Agent
Responsibilities:
- Receive and parse customer queries
- Infer intent and classify networking issue using the shared model
- Lookup customer profile and past similar cases
- Decide dynamic workflow routing (not a blind sequential pipe)
- Maintain task state and coordinate multi-agent workflow
- Trigger escalation when appropriate
"""

import time
from model.inference import classify_issue, generate_agent_response
from monitoring.temporary_logs import log_event
import database as db


class CoordinatorAgent:
    NAME = "Coordinator Agent"

    def __init__(self):
        self.system_instructions = (
            "You are the NetCare AI Coordinator Agent. Your task is to analyze customer intent, "
            "evaluate urgency, retrieve past case history, and route control dynamically to the appropriate "
            "specialized agent (Diagnosis, Troubleshooting, or Escalation)."
        )

    def process_incoming_query(self, session_id: str, customer_id: str, message: str, scenario: str = "router_disconnected") -> dict:
        """Entry point for handling a customer inquiry."""
        start_time = time.time()
        log_event("INFO", self.NAME, f"Session started for {customer_id}: '{message}'", details={"scenario": scenario})

        # 1. Lookup customer profile
        customer = db.get_customer(customer_id)
        if not customer:
            log_event("WARN", self.NAME, f"Customer lookup failed for {customer_id}")
            return {"error": f"Customer ID '{customer_id}' not found in our system."}

        # 2. Check past resolved cases for RAG case-based reasoning
        past_cases = db.find_similar_cases(message + " " + scenario)
        past_note = ""
        if past_cases:
            top_case = past_cases[0]
            past_note = f"Similar past case #{top_case['case_id']} resolved via: {top_case['successful_action']}"
            log_event("INFO", self.NAME, f"Found similar historical case #{top_case['case_id']}")

        # 3. Classify intent and problem category using the shared fine-tuned model
        from model.conversation_handler import classify_message_intent
        conv_intent = classify_message_intent(message)

        cls_result = classify_issue(message)
        category = cls_result["category"]
        confidence = cls_result["confidence"]

        # 4. Generate welcome and coordination routing
        if conv_intent == "greeting":
            welcome_msg = (
                f"NetCare AI • Customer: {customer['name']} ({customer_id}) • Plan: {customer['plan']}\n\n"
                f"Hello {customer['name']}! I am your support coordinator. Please tell me what connectivity problem "
                f"you are experiencing (e.g. no internet, Wi-Fi dropping, router red light) so our diagnostic agents can help."
            )
            routed_agent = "Diagnosis Agent"
        elif conv_intent == "gibberish":
            welcome_msg = (
                f"NetCare AI • Customer: {customer['name']} ({customer_id}) • Plan: {customer['plan']}\n\n"
                f"I received your message '{message}', but couldn't detect a clear networking issue. "
                f"Could you please describe what is happening with your internet or router in a few words?"
            )
            routed_agent = "Diagnosis Agent"
        else:
            coord_resp = generate_agent_response("coordinator", message, {
                "category": category,
                "customer_id": customer_id,
                "customer_name": customer["name"],
                "plan": customer["plan"]
            })
            welcome_msg = coord_resp["message"]
            routed_agent = coord_resp["routed_agent"]

        if past_note:
            welcome_msg += f"\n\n💡 *Note:* {past_note}"

        db.save_message(session_id, "agent", welcome_msg)
        db.log_agent(session_id, self.NAME, f"Routing to {routed_agent}", f"Intent: {cls_result['intent']}")

        latency_ms = round((time.time() - start_time) * 1000, 2)
        log_event("SUCCESS", self.NAME, f"Coordination completed in {latency_ms}ms. Next: {routed_agent}", latency_ms=latency_ms)

        return {
            "customer": customer,
            "classification": cls_result,
            "welcome_message": welcome_msg,
            "routed_agent": routed_agent,
            "past_case": past_cases[0] if past_cases else None,
            "model_used": cls_result["model_used"],
            "confidence": confidence
        }

    def route_feedback(self, session_id: str, action: str, feedback: str, scenario: str) -> dict:
        """Coordinates feedback evaluation and delegates to Monitoring Agent."""
        log_event("INFO", self.NAME, f"Routing customer feedback '{feedback}' for action '{action}'")
        from agents.monitoring import MonitoringAgent
        from agents.troubleshooting import TroubleshootingAgent
        from agents.escalation import EscalationAgent

        monitor = MonitoringAgent()
        observation = monitor.observe(session_id, action, feedback)

        session = db.get_session(session_id)
        customer = db.get_customer(session["customer_id"])

        if observation["resolved"]:
            # Close session as resolved
            from orchestration.orchestrator import SCENARIOS
            scen_info = SCENARIOS.get(scenario, {"label": scenario.replace("_", " ").title(), "diagnosis": "Diagnosed and resolved via guided remediation"})
            db.close_session(session_id, "resolved")
            db.save_resolved_case(
                session_id, customer["customer_id"],
                f"{scen_info['label']} – customer reported issue router internet disconnected",
                scen_info["diagnosis"],
                action,
                "resolved"
            )
            msg = (
                f"Internet connectivity verified. Successful fix: {action.replace('_', ' ').title()}.\n"
                f"Session resolved and closed. Telemetry recorded."
            )
            db.save_message(session_id, "agent", msg)
            log_event("SUCCESS", self.NAME, f"Session {session_id} resolved successfully by action {action}")
            return {
                "status": "resolved",
                "message": msg,
                "stage": "RESOLVED",
                "adaptation": observation
            }

        # Check for escalation triggers
        failed_count = db.count_failed_attempts(session_id)
        failed_actions = db.get_attempted_actions(session_id)

        must_escalate = (failed_count >= 3) or (scenario == "isp_outage")

        if must_escalate:
            escalator = EscalationAgent()
            ticket = escalator.escalate(session_id, customer, scenario, failed_actions)
            log_event("WARN", self.NAME, f"Issue escalated to ticket {ticket['ticket_id']}")
            return {
                "status": "escalated",
                "ticket": ticket,
                "stage": "ESCALATED",
                "message": ticket["message"],
                "adaptation": observation
            }

        # Delegate next step to Troubleshooting Agent
        troubleshooter = TroubleshootingAgent()
        next_step = troubleshooter.get_next_action(session_id, scenario, failed_actions)

        if not next_step or next_step.get("exhausted"):
            escalator = EscalationAgent()
            ticket = escalator.escalate(session_id, customer, scenario, failed_actions)
            return {
                "status": "escalated",
                "ticket": ticket,
                "stage": "ESCALATED",
                "message": ticket["message"],
                "adaptation": observation
            }

        adjust_msg = (
            f"Action failed to restore connection. Advancing to next step:\n\n"
            f"**Step:** {next_step['label']}\n\n"
            f"{next_step['instructions']}"
        )
        db.save_message(session_id, "agent", adjust_msg)
        log_event("INFO", self.NAME, f"Adapted to next troubleshooting step: {next_step['action']}")

        return {
            "status": "in_progress",
            "next_action": next_step,
            "message": adjust_msg,
            "stage": "ADJUST",
            "adaptation": observation
        }
