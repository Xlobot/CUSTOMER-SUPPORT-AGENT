"""
database.py — NetCare AI
All SQLite database operations: schema, seeding, and CRUD helpers.
"""

import sqlite3
import os
import uuid
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "netcare.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ─────────────────────────────────────────────
# SCHEMA
# ─────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    customer_id   TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    plan          TEXT NOT NULL,
    email         TEXT,
    phone         TEXT,
    account_status TEXT DEFAULT 'Active',
    address       TEXT,
    joined_date   TEXT
);

CREATE TABLE IF NOT EXISTS support_sessions (
    session_id    TEXT PRIMARY KEY,
    customer_id   TEXT NOT NULL,
    scenario      TEXT,
    status        TEXT DEFAULT 'open',
    started_at    TEXT NOT NULL,
    closed_at     TEXT,
    resolution    TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE IF NOT EXISTS messages (
    message_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    TEXT NOT NULL,
    sender        TEXT NOT NULL,        -- 'customer' or 'agent'
    content       TEXT NOT NULL,
    timestamp     TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES support_sessions(session_id)
);

CREATE TABLE IF NOT EXISTS troubleshooting_attempts (
    attempt_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    TEXT NOT NULL,
    action        TEXT NOT NULL,
    stage         TEXT NOT NULL,        -- ACT / OBSERVE / REFLECT / ADJUST
    result        TEXT,                 -- success / failure / pending
    feedback      TEXT,
    timestamp     TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES support_sessions(session_id)
);

CREATE TABLE IF NOT EXISTS agent_logs (
    log_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    TEXT NOT NULL,
    agent_name    TEXT NOT NULL,
    activity      TEXT NOT NULL,
    result        TEXT,
    timestamp     TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES support_sessions(session_id)
);

CREATE TABLE IF NOT EXISTS support_tickets (
    ticket_id         TEXT PRIMARY KEY,
    session_id        TEXT NOT NULL,
    customer_id       TEXT NOT NULL,
    issue_description TEXT NOT NULL,
    diagnosis         TEXT,
    steps_attempted   TEXT,
    escalation_reason TEXT,
    priority          TEXT DEFAULT 'Medium',
    status            TEXT DEFAULT 'Open',
    created_at        TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE IF NOT EXISTS resolved_cases (
    case_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id        TEXT NOT NULL,
    customer_id       TEXT NOT NULL,
    symptoms          TEXT NOT NULL,
    diagnosis         TEXT NOT NULL,
    successful_action TEXT NOT NULL,
    outcome           TEXT NOT NULL,
    resolved_at       TEXT NOT NULL
);
"""


def init_db():
    """Create all tables and seed demo data."""
    conn = get_connection()
    with conn:
        for statement in SCHEMA.strip().split(";"):
            s = statement.strip()
            if s:
                conn.execute(s)
        _seed_customers(conn)
    conn.close()
    print("[DB] Database initialised successfully.")


def _seed_customers(conn):
    demo_customers = [
        ("NET1001", "Aarav Sharma",  "Fiber 100 Mbps",    "aarav@example.com",  "+91-9876543210", "Active",   "12 MG Road, Bengaluru",      "2023-01-15"),
        ("NET1002", "Priya Patel",   "Fiber 300 Mbps",    "priya@example.com",  "+91-9123456780", "Active",   "45 Nehru Street, Mumbai",    "2022-06-20"),
        ("NET1003", "Rohan Mehta",   "Broadband 50 Mbps", "rohan@example.com",  "+91-9988776655", "Active",   "7 Park Avenue, Delhi",       "2021-11-08"),
        ("NET1004", "Sneha Iyer",    "Fiber 100 Mbps",    "sneha@example.com",  "+91-9001234567", "Suspended","23 Lake View, Chennai",       "2023-03-10"),
        ("NET1005", "Vikram Singh",  "Broadband 50 Mbps", "vikram@example.com", "+91-9876001234", "Active",   "88 Station Road, Hyderabad", "2020-09-05"),
    ]
    for row in demo_customers:
        conn.execute(
            """INSERT OR IGNORE INTO customers
               (customer_id,name,plan,email,phone,account_status,address,joined_date)
               VALUES (?,?,?,?,?,?,?,?)""",
            row
        )


# ─────────────────────────────────────────────
# CUSTOMER
# ─────────────────────────────────────────────

def get_customer(customer_id: str):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM customers WHERE customer_id = ?", (customer_id.upper(),)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_customers():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM customers ORDER BY customer_id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────
# SESSION
# ─────────────────────────────────────────────

def create_session(customer_id: str, scenario: str = "router_disconnected") -> str:
    session_id = str(uuid.uuid4())
    conn = get_connection()
    with conn:
        conn.execute(
            "INSERT INTO support_sessions (session_id,customer_id,scenario,status,started_at) VALUES (?,?,?,?,?)",
            (session_id, customer_id, scenario, "open", _now())
        )
    conn.close()
    return session_id


def get_session(session_id: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM support_sessions WHERE session_id=?", (session_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def close_session(session_id: str, resolution: str):
    conn = get_connection()
    with conn:
        conn.execute(
            "UPDATE support_sessions SET status=?,closed_at=?,resolution=? WHERE session_id=?",
            ("closed", _now(), resolution, session_id)
        )
    conn.close()


def get_dashboard_stats():
    conn = get_connection()
    total    = conn.execute("SELECT COUNT(*) FROM support_sessions").fetchone()[0]
    resolved = conn.execute("SELECT COUNT(*) FROM support_sessions WHERE status='closed' AND resolution='resolved'").fetchone()[0]
    tickets  = conn.execute("SELECT COUNT(*) FROM support_tickets WHERE status='Open'").fetchone()[0]
    conn.close()
    rate = round((resolved / total * 100) if total else 0, 1)
    return {"total_sessions": total, "resolved_cases": resolved,
            "open_tickets": tickets, "resolution_rate": rate}


# ─────────────────────────────────────────────
# MESSAGES
# ─────────────────────────────────────────────

def save_message(session_id: str, sender: str, content: str):
    conn = get_connection()
    with conn:
        conn.execute(
            "INSERT INTO messages (session_id,sender,content,timestamp) VALUES (?,?,?,?)",
            (session_id, sender, content, _now())
        )
    conn.close()


def get_messages(session_id: str):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM messages WHERE session_id=? ORDER BY timestamp", (session_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────
# TROUBLESHOOTING ATTEMPTS
# ─────────────────────────────────────────────

def save_attempt(session_id: str, action: str, stage: str,
                 result: str = "pending", feedback: str = ""):
    conn = get_connection()
    with conn:
        conn.execute(
            "INSERT INTO troubleshooting_attempts (session_id,action,stage,result,feedback,timestamp) VALUES (?,?,?,?,?,?)",
            (session_id, action, stage, result, feedback, _now())
        )
    conn.close()


def update_attempt_result(session_id: str, action: str, result: str, feedback: str):
    conn = get_connection()
    with conn:
        conn.execute(
            """UPDATE troubleshooting_attempts SET result=?,feedback=?
               WHERE session_id=? AND action=? AND result='pending'""",
            (result, feedback, session_id, action)
        )
    conn.close()


def get_attempts(session_id: str):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM troubleshooting_attempts WHERE session_id=? ORDER BY timestamp",
        (session_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def count_failed_attempts(session_id: str) -> int:
    conn = get_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM troubleshooting_attempts WHERE session_id=? AND result='failure'",
        (session_id,)
    ).fetchone()[0]
    conn.close()
    return count


def get_attempted_actions(session_id: str):
    conn = get_connection()
    rows = conn.execute(
        "SELECT action FROM troubleshooting_attempts WHERE session_id=? AND result='failure'",
        (session_id,)
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


# ─────────────────────────────────────────────
# AGENT LOGS
# ─────────────────────────────────────────────

def log_agent(session_id: str, agent_name: str, activity: str, result: str = ""):
    conn = get_connection()
    with conn:
        conn.execute(
            "INSERT INTO agent_logs (session_id,agent_name,activity,result,timestamp) VALUES (?,?,?,?,?)",
            (session_id, agent_name, activity, result, _now())
        )
    conn.close()


def get_agent_logs(session_id: str):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM agent_logs WHERE session_id=? ORDER BY timestamp",
        (session_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────
# SUPPORT TICKETS
# ─────────────────────────────────────────────

def create_ticket(session_id: str, customer_id: str, issue: str,
                  diagnosis: str, steps: str, reason: str, priority: str = "Medium") -> str:
    ticket_id = "TKT-" + str(uuid.uuid4())[:8].upper()
    conn = get_connection()
    with conn:
        conn.execute(
            """INSERT INTO support_tickets
               (ticket_id,session_id,customer_id,issue_description,diagnosis,
                steps_attempted,escalation_reason,priority,status,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (ticket_id, session_id, customer_id, issue, diagnosis,
             steps, reason, priority, "Open", _now())
        )
    conn.close()
    return ticket_id


def get_all_tickets():
    conn = get_connection()
    rows = conn.execute(
        "SELECT t.*, c.name as customer_name FROM support_tickets t "
        "LEFT JOIN customers c ON t.customer_id=c.customer_id "
        "ORDER BY t.created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_ticket(ticket_id: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM support_tickets WHERE ticket_id=?", (ticket_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ─────────────────────────────────────────────
# RESOLVED CASES
# ─────────────────────────────────────────────

def save_resolved_case(session_id: str, customer_id: str, symptoms: str,
                       diagnosis: str, successful_action: str, outcome: str):
    conn = get_connection()
    with conn:
        conn.execute(
            """INSERT INTO resolved_cases
               (session_id,customer_id,symptoms,diagnosis,successful_action,outcome,resolved_at)
               VALUES (?,?,?,?,?,?,?)""",
            (session_id, customer_id, symptoms, diagnosis, successful_action, outcome, _now())
        )
    conn.close()


def find_similar_cases(symptoms: str, limit: int = 3):
    """Simple keyword matching against stored cases."""
    keywords = [w.lower() for w in symptoms.split() if len(w) > 3]
    conn = get_connection()
    all_cases = conn.execute(
        "SELECT rc.*, c.name as customer_name FROM resolved_cases rc "
        "LEFT JOIN customers c ON rc.customer_id=c.customer_id "
        "ORDER BY rc.resolved_at DESC"
    ).fetchall()
    conn.close()
    scored = []
    for case in all_cases:
        text = (case["symptoms"] + " " + case["diagnosis"]).lower()
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scored.append((score, dict(case)))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:limit]]


def get_all_resolved_cases():
    conn = get_connection()
    rows = conn.execute(
        "SELECT rc.*, c.name as customer_name FROM resolved_cases rc "
        "LEFT JOIN customers c ON rc.customer_id=c.customer_id "
        "ORDER BY rc.resolved_at DESC LIMIT 20"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────
# DEMO RESET
# ─────────────────────────────────────────────

def reset_demo():
    """Clear all session/operational data but keep customers."""
    conn = get_connection()
    with conn:
        for tbl in ["agent_logs", "troubleshooting_attempts", "messages",
                    "support_tickets", "resolved_cases", "support_sessions"]:
            conn.execute(f"DELETE FROM {tbl}")
    conn.close()


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _now():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
