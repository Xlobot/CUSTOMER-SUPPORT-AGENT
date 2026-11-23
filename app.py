"""
app.py — NetCare AI
Flask backend — All REST API endpoints and web portals.
Upgraded Multi-Agent Autonomous Network Diagnostic System:
- Portal 1: Customer Support Chat (/)
- Portal 2: Model Performance Dashboard (/performance)
- Portal 3: Real-Time Server Monitoring & Temporary Logs (/monitoring)
"""

import os
import sys
import json
# Fix Windows console Unicode encoding
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

import database as db
import agents as ag
from orchestration.orchestrator import orchestrator
from monitoring.temporary_logs import log_event, get_temporary_logs, clear_temporary_logs
from monitoring.server_status import record_request, get_server_status
from diagnostics.network_tools import run_comprehensive_diagnostics
from rag.retrieval import retrieve_relevant_knowledge
from model.model_loader import get_model_status

app = Flask(__name__)
CORS(app)

# ─────────────────────────────────────────────
# INITIALISE DATABASE ON STARTUP
# ─────────────────────────────────────────────

@app.before_request
def _init_once():
    record_request(is_api=request.path.startswith("/api/"))
    if not hasattr(app, "_db_ready"):
        db.init_db()
        app._db_ready = True


# ─────────────────────────────────────────────
# FRONTEND PORTALS
# ─────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/performance")
def performance_dashboard():
    return render_template("performance.html")


@app.route("/monitoring")
def server_monitoring():
    return render_template("monitoring.html")


# ─────────────────────────────────────────────
# CUSTOMER MANAGEMENT
# ─────────────────────────────────────────────

@app.route("/api/customers", methods=["GET"])
def list_customers():
    return jsonify(db.get_all_customers())


@app.route("/api/customer/<customer_id>", methods=["GET"])
def get_customer(customer_id):
    customer = db.get_customer(customer_id)
    if not customer:
        return jsonify({"error": f"Customer '{customer_id}' not found."}), 404
    return jsonify(customer)


# ─────────────────────────────────────────────
# MULTI-AGENT SESSION WORKFLOWS
# ─────────────────────────────────────────────

@app.route("/api/session/start", methods=["POST"])
def start_session():
    data = request.get_json(force=True)
    customer_id = data.get("customer_id", "").strip().upper()
    message = data.get("message", "My internet is not working.")
    scenario = data.get("scenario", "router_disconnected")

    if not customer_id:
        return jsonify({"error": "customer_id is required."}), 400

    result = ag.start_session(customer_id, message, scenario)
    if "error" in result:
        return jsonify(result), 404
    return jsonify(result)


@app.route("/api/session/<session_id>", methods=["GET"])
def get_session(session_id):
    data = ag.get_session_data(session_id)
    if not data["session"]:
        return jsonify({"error": "Session not found."}), 404
    return jsonify(data)


@app.route("/api/session/<session_id>/feedback", methods=["POST"])
def submit_feedback(session_id):
    data = request.get_json(force=True)
    action = data.get("action", "")
    feedback = data.get("feedback", "")
    scenario = data.get("scenario", "router_disconnected")

    if not action or not feedback:
        return jsonify({"error": "action and feedback are required."}), 400

    result = ag.process_feedback(session_id, action, feedback, scenario)
    return jsonify(result)


@app.route("/api/session/<session_id>/message", methods=["POST"])
def send_message(session_id):
    data = request.get_json(force=True) if request.data else {}
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "message is required."}), 400

    result = ag.send_customer_message(session_id, message)
    if "error" in result:
        return jsonify(result), 404
    return jsonify(result)


@app.route("/api/chat", methods=["POST"])
def direct_chat():
    data = request.get_json(force=True) if request.data else {}
    message = data.get("message", "").strip()
    customer_id = data.get("customer_id", "NET1001").strip().upper()
    scenario = data.get("scenario", "router_disconnected")

    if not message:
        return jsonify({"error": "message is required."}), 400

    from model.conversation_handler import generate_dynamic_response, classify_message_intent
    customer = db.get_customer(customer_id) or {"name": "Customer", "customer_id": customer_id}
    intent = classify_message_intent(message, in_session=False)

    if intent == "problem_report":
        # Launch real multi-agent diagnostic session
        res = ag.start_session(customer_id, message, scenario)
        res["intent"] = "problem_report"
        res["reply"] = res.get("welcome_message", "")
        return jsonify(res)

    dyn = generate_dynamic_response(message, session=None, customer=customer)
    reply_text = dyn.get("reply", "") or f"I received your inquiry regarding '{message}'. How can I assist you with your connection today?"
    return jsonify({
        "intent": intent,
        "reply": reply_text,
        "status": "chat",
        "model_used": "NetCare-Domain-Adapted-Model-v1.0"
    })


# ─────────────────────────────────────────────
# TICKETS & CASES
# ─────────────────────────────────────────────

@app.route("/api/tickets", methods=["GET"])
def list_tickets():
    return jsonify(db.get_all_tickets())


@app.route("/api/ticket/<ticket_id>", methods=["GET"])
def get_ticket(ticket_id):
    ticket = db.get_ticket(ticket_id)
    if not ticket:
        return jsonify({"error": "Ticket not found."}), 404
    return jsonify(ticket)


@app.route("/api/cases", methods=["GET"])
def list_cases():
    return jsonify(db.get_all_resolved_cases())


@app.route("/api/cases/search", methods=["GET"])
def search_cases():
    query = request.args.get("q", "")
    cases = db.find_similar_cases(query)
    return jsonify(cases)


# ─────────────────────────────────────────────
# DASHBOARD OVERVIEW
# ─────────────────────────────────────────────

@app.route("/api/dashboard", methods=["GET"])
def dashboard():
    stats = db.get_dashboard_stats()
    tickets = db.get_all_tickets()
    cases = db.get_all_resolved_cases()
    stats["gemini_active"] = False
    stats["primary_model"] = "NetCare-Domain-Adapted (Qwen2.5-3B)"
    stats["recent_tickets"] = tickets[:5]
    stats["recent_cases"] = cases[:5]
    return jsonify(stats)


# ─────────────────────────────────────────────
# DEMO CONTROLS & SCENARIOS
# ─────────────────────────────────────────────

@app.route("/api/scenarios", methods=["GET"])
def list_scenarios():
    return jsonify([
        {"key": k, "label": v["label"], "severity": v["severity"],
         "isp_outage": v["isp_outage"]}
        for k, v in ag.SCENARIOS.items()
    ])


@app.route("/api/demo/reset", methods=["POST"])
def reset_demo():
    db.reset_demo()
    return jsonify({"message": "Demo data reset. Customer accounts preserved."})


# ─────────────────────────────────────────────
# MODEL SELECTION & PERFORMANCE EVALUATION
# ─────────────────────────────────────────────

@app.route("/api/models", methods=["GET"])
def get_models():
    return jsonify({
        "models": ag.AVAILABLE_MODELS,
        "active_model": ag.get_current_model(),
        "gemini_active": False,
        "last_model_used": ag.LAST_MODEL_USED,
    })


@app.route("/api/models/select", methods=["POST"])
def select_model():
    data = request.get_json(force=True) if request.data else {}
    model_id = data.get("model", "netcare-ft-local")
    result = ag.set_current_model(model_id)
    return jsonify(result)


@app.route("/api/models/test", methods=["POST"])
def test_model():
    data = request.get_json(force=True) if request.data else {}
    model_id = data.get("model")
    result = ag.test_model_connection(model_id)
    return jsonify(result)


@app.route("/api/model/performance", methods=["GET"])
def get_model_performance():
    """Returns real measured model training and evaluation metrics."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    eval_dir = os.path.join(base_dir, "evaluation_results")
    processed_dir = os.path.join(base_dir, "datasets", "processed")

    metrics_file = os.path.join(eval_dir, "model_metrics.json")
    history_file = os.path.join(eval_dir, "training_history.json")
    agent_eval_file = os.path.join(eval_dir, "agent_evaluations.json")
    report_file = os.path.join(processed_dir, "preprocessing_report.json")

    model_metrics = json.load(open(metrics_file, encoding="utf-8")) if os.path.exists(metrics_file) else {}
    training_history = json.load(open(history_file, encoding="utf-8")) if os.path.exists(history_file) else {}
    agent_evals = json.load(open(agent_eval_file, encoding="utf-8")) if os.path.exists(agent_eval_file) else {}
    preproc_report = json.load(open(report_file, encoding="utf-8")) if os.path.exists(report_file) else {}

    return jsonify({
        "status": "success",
        "model_status": get_model_status(),
        "model_metrics": model_metrics,
        "training_history": training_history,
        "agent_evaluations": agent_evals,
        "preprocessing_report": preproc_report
    })


# ─────────────────────────────────────────────
# SERVER MONITORING & TEMPORARY LOGS
# ─────────────────────────────────────────────

@app.route("/api/monitoring/status", methods=["GET"])
def monitoring_status():
    return jsonify(get_server_status())


@app.route("/api/monitoring/logs", methods=["GET"])
def monitoring_logs():
    limit = int(request.args.get("limit", 100))
    level = request.args.get("level")
    agent = request.args.get("agent")
    logs = get_temporary_logs(limit=limit, level=level, agent=agent)
    return jsonify(logs)


@app.route("/api/monitoring/logs/clear", methods=["POST"])
def clear_logs_endpoint():
    clear_temporary_logs()
    return jsonify({"status": "success", "message": "In-memory temporary log buffer cleared."})


# ─────────────────────────────────────────────
# SAFE NETWORK DIAGNOSTICS & RAG ENDPOINTS
# ─────────────────────────────────────────────

@app.route("/api/diagnostics/run", methods=["POST"])
def run_diagnostics_endpoint():
    data = request.get_json(force=True) if request.data else {}
    scenario = data.get("scenario")
    results = run_comprehensive_diagnostics(scenario_override=scenario)
    return jsonify(results)


@app.route("/api/rag/query", methods=["POST"])
def query_rag_endpoint():
    data = request.get_json(force=True) if request.data else {}
    query = data.get("query", "wifi troubleshooting")
    top_k = int(data.get("top_k", 2))
    citations = retrieve_relevant_knowledge(query, top_k=top_k)
    return jsonify({"query": query, "citations": citations})


# ─────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "primary_engine": "NetCare-Domain-Adapted-Model",
        "gemini_active": False,
        "active_model": ag.get_current_model(),
        "last_model_used": ag.LAST_MODEL_USED,
        "db": "connected"
    })


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

# Initialise database on module import (for gunicorn or direct python execution)
try:
    db.init_db()
except Exception as e:
    print(f"[WARN] Database init warning: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true")
    print(f"\n🚀 NetCare AI Upgraded Multi-Agent System running at http://0.0.0.0:{port}")
    print(f"🤖 Primary Intelligence: NetCare Domain Foundation Model (5 Specialized Agents)")
    print(f"📊 Model Performance Dashboard: http://0.0.0.0:{port}/performance")
    print(f"🖥️ Server Monitoring & Temporary Logs: http://0.0.0.0:{port}/monitoring\n")
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
