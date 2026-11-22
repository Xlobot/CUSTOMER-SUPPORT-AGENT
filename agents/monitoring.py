"""
agents/monitoring.py — NetCare AI
Agent 4: Monitoring Agent
Responsibilities:
- Observe troubleshooting outcome via customer feedback and post-fix diagnostic verification
- Implement the ACT -> OBSERVE -> REFLECT -> ADJUST feedback loop
- Evaluate whether the proposed solution succeeded or if further adaptation is needed
- Alert Coordinator Agent with structured adjustment recommendations
"""

import time
from model.inference import generate_agent_response
from diagnostics.network_tools import check_dns_resolution, ping_host
from monitoring.temporary_logs import log_event
import database as db


class MonitoringAgent:
    NAME = "Monitoring Agent"

    def __init__(self):
        self.system_instructions = (
            "You are the NetCare AI Monitoring Agent. You manage the feedback loop: "
            "ACT -> OBSERVE -> REFLECT -> ADJUST. You verify whether remediation worked, "
            "compare diagnostic state before and after, and trigger adaptation or escalation."
        )

    def observe(self, session_id: str, action: str, feedback: str) -> dict:
        """
        Feedback loop execution:
        ACT -> OBSERVE -> REFLECT -> ADJUST
        """
        start_time = time.time()
        feedback_clean = feedback.lower().strip()

        not_working_phrases = [
            "not working", "not_working", "didn't work", "did not work",
            "still not working", "still broken", "failed", "no change", "doesn't work"
        ]
        working_phrases = [
            "it worked", "it works", "is working", "working now",
            "resolved", "fixed", "back online", "all good", "working"
        ]

        is_failure = any(p in feedback_clean for p in not_working_phrases)
        is_resolved = any(p in feedback_clean for p in working_phrases) and not is_failure

        result_str = "success" if is_resolved else "failure"
        db.update_attempt_result(session_id, action, result_str, feedback)

        log_event("INFO", self.NAME, f"OBSERVE: Feedback='{feedback}' for action='{action}' (Result: {result_str})")
        db.log_agent(session_id, self.NAME, f"OBSERVE: Feedback='{feedback}' for '{action}'", f"Result: {result_str}")

        # Post-fix connectivity verification if customer reports working
        post_verification = None
        if is_resolved:
            post_check = check_dns_resolution("google.com")
            post_verification = {
                "verified": post_check["status"] == "PASS",
                "details": f"DNS query {post_check['status']}"
            }
            reflection = f"Action '{action}' successfully restored connectivity. Post-fix check: {post_check['status']}."
            adaptation_needed = False
        else:
            failed_count = db.count_failed_attempts(session_id)
            reflection = f"Action '{action}' did not resolve the fault. Failed attempts: {failed_count}. Adaptation required."
            adaptation_needed = True

        db.log_agent(session_id, self.NAME, f"REFLECT: {reflection}")
        db.save_message(session_id, "customer", f"[Feedback] {feedback}")

        latency_ms = round((time.time() - start_time) * 1000, 2)
        log_event("SUCCESS", self.NAME, f"Reflection completed. Resolved: {is_resolved}, Adapt: {adaptation_needed}", latency_ms=latency_ms)

        return {
            "resolved": is_resolved,
            "result": result_str,
            "reflection": reflection,
            "adaptation_needed": adaptation_needed,
            "post_verification": post_verification,
            "stage": "OBSERVE -> REFLECT"
        }
