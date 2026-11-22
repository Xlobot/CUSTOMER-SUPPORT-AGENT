# JURY_GUIDE.md — NetCare AI Presentation Guide

## Project Title
**NetCare AI — Intelligent Internet Customer Support Agent**

---

## Problem Statement

> "My internet connection has stopped working. Help me fix it."

Most internet customers cannot resolve technical issues without calling a support hotline. NetCare AI provides an intelligent, always-available virtual support agent that guides customers through structured troubleshooting, learns from previous cases, and escalates unresolved issues automatically.

---

## Architecture Overview

```
Customer Browser (HTML + CSS + JS)
        │ HTTP (REST)
        ▼
Flask Backend (app.py)
        │
        ▼
Coordinator Agent ────► Diagnosis Agent
        │                    │ diagnosis
        │               Troubleshooting Agent
        │                    │ instructions
        │               Monitoring Agent
        │                    │ feedback
        │               Escalation Agent
        │                    │ ticket
        ▼
SQLite Database (netcare.db)
```

---

## Technology Stack

| Component     | Technology            | Purpose                            |
|---------------|-----------------------|------------------------------------|
| Frontend      | HTML5, CSS3, JS       | User interface and chat            |
| Backend       | Python Flask          | REST API and routing               |
| AI Model      | Google Gemini 1.5     | Natural language responses         |
| Database      | SQLite                | Persistent storage                 |
| Agents        | Python classes        | Role-based agent system            |

---

## Unit III — Feedback-Based Adaptation

### Concept
The agent must not follow a fixed script. It adapts its behaviour based on whether each action succeeded or failed.

### The Cycle
```
ACT → OBSERVE → REFLECT → ADJUST
```

### Implementation

| Stage   | Implementation                                                        |
|---------|-----------------------------------------------------------------------|
| ACT     | Troubleshooting Agent recommends a step (e.g., restart router)       |
| OBSERVE | Monitoring Agent collects customer feedback (working / not working)   |
| REFLECT | Monitoring Agent evaluates the result and logs it to the database     |
| ADJUST  | Coordinator Agent selects the next action from the remaining list     |

### Key behaviours
- Each failed action is recorded in `troubleshooting_attempts`
- The next recommended action is always one not yet tried
- After 3 failed attempts, the Escalation Agent is triggered
- ISP outages bypass troubleshooting and escalate immediately
- The cycle is visible in the UI using the stage indicator

---

## Unit IV — Role-Based Agents

### The Five Agents

#### 1. Coordinator Agent
- **File**: `agents.py → CoordinatorAgent`
- **Role**: Entry point. Receives the customer problem, fetches account details, delegates to other agents, and produces the final response.
- **Key methods**: `handle_new_session()`, `handle_feedback()`

#### 2. Diagnosis Agent
- **File**: `agents.py → DiagnosisAgent`
- **Role**: Runs simulated network checks (ping, DNS, WAN port, Wi-Fi) and identifies the root cause.
- **Key method**: `diagnose()`

#### 3. Troubleshooting Agent
- **File**: `agents.py → TroubleshootingAgent`
- **Role**: Selects the appropriate troubleshooting action based on diagnosis and previously failed actions.
- **Key method**: `get_next_action()`

#### 4. Monitoring Agent
- **File**: `agents.py → MonitoringAgent`
- **Role**: Implements the OBSERVE and REFLECT stages. Records customer feedback and determines whether adaptation is needed.
- **Key method**: `observe()`

#### 5. Escalation Agent
- **File**: `agents.py → EscalationAgent`
- **Role**: Creates a support ticket with full context when troubleshooting fails or an ISP outage is detected.
- **Key method**: `escalate()`

### How they work together
All agents are orchestrated by the Coordinator Agent. The customer never interacts with individual agents directly — the coordinator routes work to the correct agent and combines the results.

---

## Case-Based Learning

When a case is resolved:
- Symptoms, diagnosis, and successful action are saved to `resolved_cases`

When a new session starts:
- The system searches `resolved_cases` using keyword matching on the customer's message and scenario
- If a similar case is found, it is shown in the UI and used to prioritise recommendations
- This uses **real stored data** — not hardcoded claims

---

## Demo Scenarios

### Scenario 1 — Successful Troubleshooting
**Goal**: Show a complete, successful support interaction.

**Steps**:
1. Demo Controls → **Run Scenario 1**
2. Click **▶ Start Session**
3. Read the diagnosis shown (Quick Resolution — router firmware glitch)
4. The agent recommends: restart router
5. Click **✅ Internet is Working!**
6. The case is marked resolved; a resolved case entry is created
7. Show the **Previous Cases** tab — the resolved case appears

**Points to mention**:
- Customer account retrieved from SQLite
- Diagnosis is simulated and clearly labelled
- ACT stage is active on the stage indicator
- RESOLVED status confirmed in dashboard

---

### Scenario 2 — Feedback-Based Adaptation
**Goal**: Demonstrate the full ACT → OBSERVE → REFLECT → ADJUST cycle.

**Steps**:
1. Demo Controls → **Run Scenario 2**
2. Click **▶ Start Session**
3. Stage indicator shows **ACT**: agent recommends "Restart Router"
4. Click **❌ Still Not Working**
5. Stage cycles through OBSERVE → REFLECT → ADJUST
6. Agent recommends a different step: "Check Cables & Connections"
7. Click **❌ Still Not Working** again
8. Agent adapts once more and tries "Factory Reset Router"
9. Show the **Agent Activity** tab — all four stages are logged

**Points to mention**:
- The agent does not repeat the same action
- Each failure is recorded in `troubleshooting_attempts`
- The Monitoring Agent handles OBSERVE and REFLECT
- The stage indicator updates in real time

---

### Scenario 3 — Escalation and Learning
**Goal**: Show escalation and demonstrate case-based learning.

**Steps**:
1. Demo Controls → **Run Scenario 3**
2. Click **▶ Start Session**
3. Diagnosis: ISP Outage detected
4. Agent recommends: Check ISP Service Status
5. Click **❌ Still Not Working**
6. Escalation Agent creates a ticket (ISP outage cannot be fixed remotely)
7. Show the **Tickets** tab — ticket appears with ID, priority, reason
8. Start another session (any customer, same scenario)
9. Observe "📚 Similar past case found" in the chat

**Points to mention**:
- ISP outages skip extended troubleshooting (no point trying to restart router)
- Ticket ID is unique, generated by `uuid`
- All ticket details are stored in SQLite
- Case-based learning uses actual stored data

---

## 10 Likely Jury Questions

### Q1: What problem does NetCare AI solve?
**A**: Internet customers often wait on hold for hours to get help. NetCare AI provides an intelligent, always-available support agent that can diagnose connectivity issues, guide customers step by step, and create a ticket automatically if remote troubleshooting fails. This reduces call centre load and speeds up resolution.

### Q2: What is Feedback-Based Adaptation? Where does it happen?
**A**: It is an AI behaviour pattern where the agent changes its actions based on the results of previous actions. In NetCare AI, it follows four stages: ACT (recommend a step), OBSERVE (collect customer feedback), REFLECT (evaluate the outcome), ADJUST (try a different approach). This is implemented in the `MonitoringAgent.observe()` and `CoordinatorAgent.handle_feedback()` methods.

### Q3: What are Role-Based Agents and why use them?
**A**: Role-Based Agents divide a complex task into specialised sub-agents, each responsible for one thing. This makes the system easier to understand, maintain, and extend. In NetCare AI, the Coordinator orchestrates four specialist agents: Diagnosis, Troubleshooting, Monitoring, and Escalation. Each has a single, clear responsibility.

### Q4: How does the Gemini API integrate?
**A**: The Gemini API is called in the `_gemini()` helper function in `agents.py`. It is used to generate human-friendly explanations, diagnoses, and responses. The API key is read from the `GEMINI_API_KEY` environment variable. If it is missing or fails, the system falls back to pre-written rule-based responses — no features are lost.

### Q5: Is this a real network diagnostic tool?
**A**: No. All network checks are simulated using predefined scenarios selected by the user. This is clearly labelled in the UI with a "SIMULATED" tag. The system is designed for demonstration and does not access real routers, ISPs, or network infrastructure.

### Q6: How does case-based learning work?
**A**: When a troubleshooting session succeeds, the symptoms, diagnosis, and successful action are saved to the `resolved_cases` table in SQLite. When a new session starts, the system performs a keyword search on that table. If a similar case is found, it is shown to the agent and the customer. The Troubleshooting Agent prioritises the action that previously worked.

### Q7: How do you prevent infinite troubleshooting loops?
**A**: The `MAX_ATTEMPTS` constant (set to 3) limits the number of failed actions. Each failed action is recorded in `troubleshooting_attempts`. The `get_next_action()` method skips any action that has already failed. After 3 failures — or if an ISP outage is detected — the Escalation Agent is triggered automatically.

### Q8: What data is stored in the database?
**A**: NetCare AI stores customer accounts, support sessions, messages, troubleshooting attempts (with stage and result), agent activity logs, support tickets, and resolved cases. All records persist after the app restarts. The SQLite database is created automatically on first run.

### Q9: How would you scale this for production?
**A**: Replace SQLite with PostgreSQL or MySQL for concurrent access. Add authentication (JWT tokens) to protect customer data. Use a proper message queue (Redis/Celery) for background processing. Deploy on a cloud platform (e.g., Google Cloud Run). Integrate with real network monitoring APIs for actual diagnostics.

### Q10: What would you add with more time?
**A**: Real-time notifications via WebSockets so the agent can push updates. Integration with a real ticketing system (e.g., Zendesk). Voice interface using the Gemini Live API. Multi-language support. A proper login system for real customer authentication. Analytics dashboard with historical trends.

---

## Quick Start for Jury (30 seconds)

```powershell
# From the project folder:
venv\Scripts\activate
python app.py
# Open http://localhost:5000
# Go to Demo Controls → Run Scenario 1 → Start Session → Internet is Working!
```

---

## AI Disclosure

NetCare AI uses Google Gemini 1.5 Flash to generate natural-language responses. All diagnostic results, customer data retrieval, ticket creation, and case storage are performed by deterministic Python code backed by SQLite — not by the AI model. The AI is only responsible for generating readable, conversational text.
