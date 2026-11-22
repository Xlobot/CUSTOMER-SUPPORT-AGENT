"""
test_netcare.py -- Automated tests for NetCare AI

Run: python test_netcare.py
"""

import sys
import os
import json
import time

# Fix Windows console Unicode encoding
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# -- Use a dedicated test database (not the production DB) --------------------
_TEST_DB = os.path.join(os.path.dirname(__file__), "netcare_test.db")
# Remove any old test DB so each run is clean
if os.path.exists(_TEST_DB):
    os.remove(_TEST_DB)
os.environ["NETCARE_TEST"] = "1"

# -- Import project modules ---------------------------------------------------
try:
    import database as db
    # Point to test DB BEFORE anything else imports it
    db.DB_PATH = _TEST_DB
    import agents as ag
    ag.GEMINI_ACTIVE = False  # Keep test suite instant, offline, and deterministic
    from app import app
except ImportError as e:
    print(f"FAIL Import error: {e}")
    sys.exit(1)

PASS = "PASS PASS"
FAIL = "FAIL FAIL"
results = []


def test(name, condition, detail=""):
    icon = PASS if condition else FAIL
    msg = f"{icon}  {name}"
    if detail and not condition:
        msg += f"\n      Detail: {detail}"
    print(msg)
    results.append((name, condition))
    return condition


def section(title):
    print(f"\n{'-'*60}")
    print(f"  {title}")
    print(f"{'-'*60}")


# ===============================================================
# SETUP
# ===============================================================

section("1. Database Initialisation")
try:
    db.init_db()
    test("Database initialises without errors", True)
except Exception as e:
    test("Database initialises without errors", False, str(e))
    sys.exit(1)

# ===============================================================
# CUSTOMER LOOKUP
# ===============================================================

section("2. Customer Lookup")

c1 = db.get_customer("NET1001")
test("Known customer NET1001 found",        c1 is not None)
test("Customer name is correct",            c1 and c1["name"] == "Aarav Sharma")
test("Customer plan populated",             c1 and "Fiber" in c1["plan"])

c_none = db.get_customer("XXXXXX")
test("Unknown customer returns None",       c_none is None)

c2 = db.get_customer("NET1002")
test("Customer NET1002 found",              c2 is not None)

all_c = db.get_all_customers()
test("get_all_customers returns 5 records", len(all_c) == 5)

# ===============================================================
# SESSION
# ===============================================================

section("3. Session Management")

sid = db.create_session("NET1001", "router_disconnected")
test("Session created with valid ID",       bool(sid) and len(sid) > 10)

sess = db.get_session(sid)
test("Session retrieved from DB",           sess is not None)
test("Session status is 'open'",            sess and sess["status"] == "open")

db.close_session(sid, "resolved")
sess2 = db.get_session(sid)
test("Session can be closed",               sess2 and sess2["status"] == "closed")
test("Resolution recorded",                 sess2 and sess2["resolution"] == "resolved")

# ===============================================================
# AGENT START SESSION (Scenario 1 — successful)
# ===============================================================

section("4. Agent: Start Session")

result = ag.start_session("NET1001", "My internet is not working", "resolved_quickly")
test("start_session returns dict",          isinstance(result, dict))
test("No error in result",                  "error" not in result)
test("session_id present",                  "session_id" in result)
test("customer info present",               "customer" in result)
test("diagnosis present",                   "diagnosis" in result)
test("next_action present",                 "next_action" in result)
test("next_action has 'action' key",        "action" in (result.get("next_action") or {}))
test("welcome_message present",             bool(result.get("welcome_message")))

s1_sid = result["session_id"]
s1_action = result["next_action"]["action"]

# ===============================================================
# UNKNOWN CUSTOMER HANDLING
# ===============================================================

section("5. Error Handling")

bad = ag.start_session("BADID99", "Internet broken", "router_disconnected")
test("Unknown customer returns error dict", "error" in bad)

# ===============================================================
# FEEDBACK — SUCCESS
# ===============================================================

section("6. Feedback: Successful Resolution (Scenario 1)")

fb_ok = ag.process_feedback(s1_sid, s1_action, "working", "resolved_quickly")
test("Feedback 'working' returns resolved status", fb_ok.get("status") == "resolved")
test("Resolution message present",          bool(fb_ok.get("message")))

# Check resolved case saved
cases = db.get_all_resolved_cases()
test("Resolved case saved in DB",           len(cases) > 0)
test("Correct session_id in case",          any(c["session_id"] == s1_sid for c in cases))

# ===============================================================
# FEEDBACK — ADAPTATION (Scenario 2)
# ===============================================================

section("7. Feedback-Based Adaptation (Scenario 2)")

s2 = ag.start_session("NET1002", "Internet not working", "router_disconnected")
s2_sid    = s2["session_id"]
s2_action = s2["next_action"]["action"]

# First failure
fb1 = ag.process_feedback(s2_sid, s2_action, "not_working", "router_disconnected")
test("After 1st failure, status is in_progress", fb1.get("status") == "in_progress")
test("New next_action provided",            "next_action" in fb1)

s2_action2 = fb1["next_action"]["action"]
test("Next action differs from first",      s2_action2 != s2_action)
test("Adaptation stage returned",          fb1.get("stage") in ("ADJUST", "ESCALATED"))

# Verify failed attempt recorded
failed = db.count_failed_attempts(s2_sid)
test("Failed attempt count = 1",           failed == 1)

# ===============================================================
# ESCALATION (Scenario 3)
# ===============================================================

section("8. Escalation (Scenario 3 — ISP Outage)")

s3 = ag.start_session("NET1003", "No internet at all", "isp_outage")
s3_sid    = s3["session_id"]
s3_action = s3["next_action"]["action"]

fb_isp = ag.process_feedback(s3_sid, s3_action, "not_working", "isp_outage")
test("ISP outage triggers escalation",      fb_isp.get("status") == "escalated")
test("Ticket data in result",               "ticket" in fb_isp)
test("Ticket ID starts with TKT-",         fb_isp.get("ticket", {}).get("ticket_id", "").startswith("TKT-"))

tickets = db.get_all_tickets()
test("Ticket persisted in DB",             len(tickets) > 0)
t = tickets[0]
test("Ticket has customer_id",             bool(t.get("customer_id")))
test("Ticket has priority",                bool(t.get("priority")))

# ===============================================================
# CASE-BASED LEARNING
# ===============================================================

section("9. Case-Based Learning")

similar = db.find_similar_cases("router internet disconnected")
test("Similar cases found using keywords",  len(similar) > 0)

# ===============================================================
# TROUBLESHOOTING — NO INFINITE LOOP
# ===============================================================

section("10. Anti-Loop / Max Attempts")

s4 = ag.start_session("NET1005", "Internet down", "persistent_failure")
s4_sid    = s4["session_id"]
s4_action = s4.get("next_action", {}).get("action", "restart_router")

# Simulate repeated failures until escalation
status = "in_progress"
for i in range(6):   # More than MAX_ATTEMPTS
    if status != "in_progress":
        break
    fbx = ag.process_feedback(s4_sid, s4_action, "not_working", "persistent_failure")
    status = fbx.get("status", "in_progress")
    if "next_action" in fbx and fbx["next_action"]:
        s4_action = fbx["next_action"]["action"]

test("Session eventually escalates (no infinite loop)", status == "escalated")

# ===============================================================
# MESSAGES PERSISTENCE
# ===============================================================

section("11. Message Persistence")

db.save_message(s1_sid, "customer", "Test message")
msgs = db.get_messages(s1_sid)
test("Messages can be saved and retrieved",  any(m["content"] == "Test message" for m in msgs))

# ===============================================================
# AGENT LOGS
# ===============================================================

section("12. Agent Logs")

logs = db.get_agent_logs(s1_sid)
test("Agent logs exist for session",        len(logs) > 0)
agent_names = {l["agent_name"] for l in logs}
test("Coordinator Agent logged",            "Coordinator Agent" in agent_names)
test("Diagnosis Agent logged",              "Diagnosis Agent" in agent_names)
test("Troubleshooting Agent logged",        "Troubleshooting Agent" in agent_names)

# ===============================================================
# DEMO RESET
# ===============================================================

section("13. Demo Reset")

db.reset_demo()
stats = db.get_dashboard_stats()
test("Sessions cleared after reset",        stats["total_sessions"] == 0)
test("Customers preserved after reset",     len(db.get_all_customers()) == 5)

# ===============================================================
# FLASK API
# ===============================================================

section("14. Flask API Endpoints")

with app.test_client() as client:
    r = client.get("/api/health")
    test("GET /api/health returns 200",     r.status_code == 200)

    data = json.loads(r.data)
    test("Health endpoint has status=ok",   data.get("status") == "ok")

    r2 = client.get("/api/customers")
    test("GET /api/customers returns 200",  r2.status_code == 200)
    custs = json.loads(r2.data)
    test("Returns list of customers",       isinstance(custs, list) and len(custs) == 5)

    r3 = client.get("/api/customer/NET1001")
    test("GET /api/customer/NET1001 = 200", r3.status_code == 200)

    r4 = client.get("/api/customer/BADID")
    test("GET /api/customer/BADID = 404",   r4.status_code == 404)

    r5 = client.post("/api/session/start",
                     data=json.dumps({"customer_id": "NET1001",
                                      "message": "Test",
                                      "scenario": "resolved_quickly"}),
                     content_type="application/json")
    test("POST /api/session/start = 200",   r5.status_code == 200)
    sdata = json.loads(r5.data)
    test("Session start returns session_id", "session_id" in sdata)

    r_msg = client.post(f"/api/session/{sdata['session_id']}/message",
                        data=json.dumps({"message": "Which light should I check on the router?"}),
                        content_type="application/json")
    test("POST /api/session/<id>/message = 200", r_msg.status_code == 200)
    mdata = json.loads(r_msg.data)
    test("Message endpoint returns reply", "reply" in mdata and len(mdata["reply"]) > 0)

    r6 = client.get("/api/dashboard")
    test("GET /api/dashboard returns 200",  r6.status_code == 200)

    r7 = client.get("/api/tickets")
    test("GET /api/tickets returns 200",    r7.status_code == 200)

    r8 = client.get("/api/cases")
    test("GET /api/cases returns 200",      r8.status_code == 200)

    r9 = client.get("/api/scenarios")
    test("GET /api/scenarios returns 200",  r9.status_code == 200)
    scens = json.loads(r9.data)
    test("Returns list of scenarios",       len(scens) >= 5)

    r10 = client.get("/api/models")
    test("GET /api/models returns 200", r10.status_code == 200)
    models_data = json.loads(r10.data)
    test("Models list returned", len(models_data.get("models", [])) >= 4)

    r11 = client.post("/api/models/select",
                      data=json.dumps({"model": "gemini-3.5-flash-lite"}),
                      content_type="application/json")
    test("POST /api/models/select returns 200", r11.status_code == 200)

    r12 = client.post("/api/models/test",
                      data=json.dumps({"model": "fallback"}),
                      content_type="application/json")
    test("POST /api/models/test returns 200", r12.status_code == 200)
    test_res = json.loads(r12.data)
    test("Model test returns status ok", test_res.get("status") == "ok")

# ===============================================================
# FALLBACK MODE
# ===============================================================

section("15. Fallback Mode (no Gemini key)")

# Even if Gemini is active, the fallback strings must be non-empty
fallback = ag._gemini("Test prompt", "Fallback response text")
test("_gemini returns fallback when key missing",
     isinstance(fallback, str) and len(fallback) > 0)

# ===============================================================
# SUMMARY
# ===============================================================

total  = len(results)
passed = sum(1 for _, ok in results if ok)
failed = total - passed

print(f"\n{'='*60}")
print(f"  TEST SUMMARY")
print(f"{'='*60}")
print(f"  Total:  {total}")
print(f"  Passed: {passed}  PASS")
print(f"  Failed: {failed}  {'FAIL' if failed else 'PASS'}")
print(f"  Rate:   {round(passed/total*100)}%")
print(f"{'='*60}\n")

if failed > 0:
    print("Failed tests:")
    for name, ok in results:
        if not ok:
            print(f"  FAIL {name}")
    sys.exit(1)
else:
    print("All tests passed! NetCare AI is ready for demonstration. ")
    sys.exit(0)
