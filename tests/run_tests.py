"""
tests/run_tests.py — NetCare AI
Universal automated test runner for the upgraded NetCare AI multi-agent system.
Runs all unit and integration tests without external test runner plugins.
"""

import sys
import os
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Fix Windows console Unicode encoding
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PASS = "✅ PASS"
FAIL = "❌ FAIL"
results = []


def run_test(name, func):
    try:
        func()
        print(f"{PASS}  {name}")
        results.append((name, True, ""))
    except Exception as e:
        print(f"{FAIL}  {name} — {e}")
        results.append((name, False, str(e)))


def section(title):
    print(f"\n{'-'*65}")
    print(f"  {title}")
    print(f"{'-'*65}")


def main():
    print(f"\n{'='*65}")
    print("  NETCARE AI — COMPREHENSIVE MULTI-AGENT TEST SUITE")
    print(f"{'='*65}")

    # 1. Model & Classification Tests
    section("1. Foundation Model & Inference")
    from tests.test_model import (
        test_model_loading,
        test_model_status,
        test_issue_classification,
        test_agent_response_generation
    )
    run_test("Model Checkpoint Loading", test_model_loading)
    run_test("Model Status & Accuracy Reporting", test_model_status)
    run_test("Multi-Category Issue Classification", test_issue_classification)
    run_test("Five-Agent Structured Response Generation", test_agent_response_generation)

    # 2. Individual Specialized Agent Tests
    section("2. Specialized AI Agents (Individual Verification)")
    from tests.test_agents import (
        test_coordinator_agent,
        test_diagnosis_agent,
        test_troubleshooting_agent,
        test_monitoring_agent,
        test_escalation_agent
    )
    run_test("Agent 1: Coordinator (Intent & Routing)", test_coordinator_agent)
    run_test("Agent 2: Diagnosis (Telemetry & Confidence)", test_diagnosis_agent)
    run_test("Agent 3: Troubleshooting (Anti-Loop Remediation)", test_troubleshooting_agent)
    run_test("Agent 4: Monitoring (ACT-OBSERVE-REFLECT-ADJUST)", test_monitoring_agent)
    run_test("Agent 5: Escalation (Ticket & SLA Packaging)", test_escalation_agent)

    # 3. Safe Local Diagnostics Tests
    section("3. Safe Network Diagnostics (Windows 11)")
    from tests.test_diagnostics import (
        test_safe_dns_resolution,
        test_safe_ping,
        test_comprehensive_diagnostics
    )
    run_test("Socket DNS Resolution Probe", test_safe_dns_resolution)
    run_test("Native Windows Ping Probe", test_safe_ping)
    run_test("Comprehensive Diagnostics & Telemetry", test_comprehensive_diagnostics)

    # 4. RAG Knowledge Base Tests
    section("4. RAG Knowledge Base Retrieval")
    from tests.test_rag import (
        test_rag_retrieval_dns,
        test_rag_retrieval_dhcp
    )
    run_test("RAG Context Retrieval: DNS Procedures", test_rag_retrieval_dns)
    run_test("RAG Context Retrieval: DHCP & IP Configurations", test_rag_retrieval_dhcp)

    # 5. In-Memory Temporary Logging Tests
    section("5. Temporary Logging & Privacy Guarantees")
    from tests.test_temporary_logs import (
        test_temporary_logging_in_memory,
        test_logs_not_persisted_to_sqlite,
        test_clear_temporary_logs
    )
    run_test("In-Memory Circular Buffer Recording", test_temporary_logging_in_memory)
    run_test("Zero SQLite / Disk Persistence for Debug Logs", test_logs_not_persisted_to_sqlite)
    run_test("In-Memory Temporary Log Reset on Command", test_clear_temporary_logs)

    # 6. REST API & Multi-Portal Integration Tests
    section("6. REST API & Web Portals Integration")
    from tests.test_api_endpoints import (
        test_portal_routes,
        test_model_performance_endpoint,
        test_monitoring_status_and_logs,
        test_diagnostics_and_rag_endpoints
    )
    from app import app
    app.config["TESTING"] = True
    with app.test_client() as client:
        run_test("Three Portals Available (/, /performance, /monitoring)", lambda: test_portal_routes(client))
        run_test("GET /api/model/performance returns Real Metrics", lambda: test_model_performance_endpoint(client))
        run_test("GET /api/monitoring/status & /logs Live Stream", lambda: test_monitoring_status_and_logs(client))
        run_test("POST /api/diagnostics/run & /api/rag/query Endpoints", lambda: test_diagnostics_and_rag_endpoints(client))

    # Summary
    total = len(results)
    passed = sum(1 for _, ok, _ in results if ok)
    failed = total - passed

    print(f"\n{'='*65}")
    print(f"  TEST SUMMARY")
    print(f"{'='*65}")
    print(f"  Total Executed: {total}")
    print(f"  Passed:         {passed}  PASS")
    print(f"  Failed:         {failed}  {'FAIL' if failed else 'PASS'}")
    print(f"  Success Rate:   {round(passed/total*100)}%")
    print(f"{'='*65}\n")

    if failed > 0:
        print("Failed Tests:")
        for name, ok, err in results:
            if not ok:
                print(f"  ❌ {name}: {err}")
        sys.exit(1)
    else:
        print("🎉 ALL TESTS PASSED! NetCare AI is fully verified and functional.\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
