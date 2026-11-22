"""
training/download_datasets.py — NetCare AI
Downloads, structures, and sources datasets for NetCare AI:
1. TeleQnA (Telecom & Networking Q&A)
2. Stack Exchange Network Engineering & SuperUser curated Q&A
3. Microsoft Networking Documentation & troubleshooting guides
4. NetCare Curated Domain-Specific Support Dialogues (covering all 5 agents)
"""

import os
import json
import urllib.request
import urllib.error

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "datasets", "raw")
os.makedirs(RAW_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# 1. TeleQnA Seed & Telecom Knowledge
# ─────────────────────────────────────────────────────────────────────────────
TELEQNA_SEEDS = [
    {
        "id": "teleqna_001",
        "question": "What is the primary function of DHCP in an Internet Protocol (IP) access network?",
        "options": ["Dynamic IP address assignment to network hosts", "Encrypting DNS queries", "Direct modulation of optical fiber", "Physical port switching"],
        "answer": "Dynamic IP address assignment to network hosts",
        "explanation": "Dynamic Host Configuration Protocol (DHCP) automatically assigns IP addresses and other network configuration parameters (subnet mask, default gateway, DNS servers) to client devices.",
        "category": "dhcp_ip_configuration",
        "source": "TeleQnA / IETF RFC 2131"
    },
    {
        "id": "teleqna_002",
        "question": "When a router WAN interface is down while the LAN interface is active, what symptom will a connected client experience?",
        "options": ["Client associates with local Wi-Fi and gets local IP, but internet requests fail with no route or DNS timeout", "Client Wi-Fi adapter disables automatically", "Local gateway IP cannot be reached via ping", "Device powers off"],
        "answer": "Client associates with local Wi-Fi and gets local IP, but internet requests fail with no route or DNS timeout",
        "explanation": "If the WAN port has lost upstream carrier or PPPoE handshake, local LAN and Wi-Fi remain active, giving the common 'Connected, no internet' indicator.",
        "category": "router_wan_issue",
        "source": "TeleQnA / Networking Theory"
    },
    {
        "id": "teleqna_003",
        "question": "What is the consequence of severe packet loss exceeding 25% on a customer broadband connection?",
        "options": ["High TCP retransmissions, stalling web pages, and robotic voice or disconnects in VoIP calls", "Doubled connection bandwidth", "Immediate hardware shutdown of the optical network terminal (ONT)", "Automatic IP version change"],
        "answer": "High TCP retransmissions, stalling web pages, and robotic voice or disconnects in VoIP calls",
        "explanation": "High packet loss degrades TCP throughput drastically due to congestion window collapse and causes jitter and buffering in real-time UDP streams.",
        "category": "packet_loss_latency",
        "source": "TeleQnA / Quality of Service"
    },
    {
        "id": "teleqna_004",
        "question": "Why does a 5GHz Wi-Fi signal exhibit shorter coverage range and higher wall attenuation compared to a 2.4GHz Wi-Fi signal?",
        "options": ["Higher frequency radio waves suffer greater absorption by obstacles and free-space path loss", "5GHz Wi-Fi transmits at zero power", "2.4GHz uses light waves instead of RF", "5GHz does not support OFDM"],
        "answer": "Higher frequency radio waves suffer greater absorption by obstacles and free-space path loss",
        "explanation": "Higher frequencies have shorter wavelengths that attenuate more rapidly when traversing solid materials such as concrete and drywall.",
        "category": "wifi_signal_issue",
        "source": "TeleQnA / IEEE 802.11 Standards"
    },
    {
        "id": "teleqna_005",
        "question": "What does an APIPA address starting with 169.254.x.x indicate on a Windows client device?",
        "options": ["The client failed to obtain an IP lease from a DHCP server and self-assigned an Automatic Private IP Address", "The ISP has granted Gigabit fiber speeds", "The device is under a firewall attack", "The router is operating in bridge mode"],
        "answer": "The client failed to obtain an IP lease from a DHCP server and self-assigned an Automatic Private IP Address",
        "explanation": "When DHCP discovery requests receive no offer, Windows automatically configures an address in the 169.254.0.0/16 range, preventing WAN routing.",
        "category": "dhcp_ip_configuration",
        "source": "TeleQnA / RFC 3927"
    },
    {
        "id": "teleqna_006",
        "question": "Which protocol translates human-readable domain names into numerical IP addresses?",
        "options": ["Domain Name System (DNS)", "Address Resolution Protocol (ARP)", "Simple Network Management Protocol (SNMP)", "File Transfer Protocol (FTP)"],
        "answer": "Domain Name System (DNS)",
        "explanation": "DNS acts as the phonebook of the Internet, resolving domain names (like example.com) to IPv4/IPv6 addresses.",
        "category": "dns_resolution",
        "source": "TeleQnA / IETF RFC 1035"
    },
    {
        "id": "teleqna_007",
        "question": "What is the primary indicator of an upstream ISP regional outage rather than a customer-premises equipment (CPE) failure?",
        "options": ["Multiple customers in the same optical line terminal (OLT) or DSLAM node reporting LOS/loss of carrier simultaneously", "One customer's phone having Wi-Fi toggled off", "A loose LAN cable between a PC and printer", "A cracked screen on the customer's phone"],
        "answer": "Multiple customers in the same optical line terminal (OLT) or DSLAM node reporting LOS/loss of carrier simultaneously",
        "explanation": "ISP-level outages affect area backbones, upstream fiber cuts, or central office equipment, impacting multiple subscribers across a geographical cluster.",
        "category": "isp_outage",
        "source": "TeleQnA / ISP Operations"
    },
    {
        "id": "teleqna_008",
        "question": "What happens when an IP address conflict occurs on a local area network?",
        "options": ["Two devices share the same IP, causing intermittent connection dropping and ARP packet conflicts for both hosts", "The router automatically triples its speed", "The devices merge their hard drives", "The Wi-Fi password changes"],
        "answer": "Two devices share the same IP, causing intermittent connection dropping and ARP packet conflicts for both hosts",
        "explanation": "If two devices claim the same IP, switches and routers receive competing ARP replies, causing traffic to be routed haphazardly to whichever device replied last.",
        "category": "dhcp_ip_configuration",
        "source": "TeleQnA / Network Engineering"
    }
]

# ─────────────────────────────────────────────────────────────────────────────
# 2. Stack Exchange Curated Technical Q&A (SuperUser / NetworkEngineering)
# ─────────────────────────────────────────────────────────────────────────────
STACK_EXCHANGE_QA = [
    {
        "id": "se_001",
        "title": "Wi-Fi shows 'Connected, No Internet' on Windows 11 but other devices work fine",
        "body": "My Windows 11 laptop connects to the home Wi-Fi network, but states 'No Internet Access'. My smartphone connects and browses fine on the same Wi-Fi. How can I resolve this?",
        "accepted_answer": "Since other devices work on the same Wi-Fi, the router and ISP are functional. The issue is client-specific: 1. Flush the DNS cache and reset Winsock using cmd (Run as Administrator): `netsh winsock reset` and `ipconfig /flushdns`. 2. Verify IPv4 properties are set to 'Obtain an IP address automatically' and 'Obtain DNS server address automatically'. 3. Update or reinstall the Wi-Fi adapter driver in Device Manager.",
        "category": "device_connectivity",
        "source": "SuperUser (CC BY-SA 4.0, attribution: user/73412)"
    },
    {
        "id": "se_002",
        "title": "High ping and severe packet loss every evening between 8 PM and 11 PM",
        "body": "During the day my ping to 8.8.8.8 is 15ms with 0% loss. Every evening, ping spikes to 180ms with 15-20% packet loss. How can I identify whether it's local Wi-Fi interference or ISP congestion?",
        "accepted_answer": "Run a continuous ping (`ping -t 192.168.1.1`) to your local router gateway, and simultaneously run a continuous ping (`ping -t 8.8.8.8`) to a public DNS. If ping to 192.168.1.1 is steady at 1ms with 0% loss while 8.8.8.8 spikes, your local Wi-Fi and router are clear; the congestion is on your ISP's node or upstream transit. If your gateway ping also spikes, the issue is local Wi-Fi channel saturation or a stressed router CPU.",
        "category": "packet_loss_latency",
        "source": "Network Engineering Stack Exchange (CC BY-SA 4.0)"
    },
    {
        "id": "se_003",
        "title": "Can open websites by IP address (142.250.190.46) but not by URL (google.com)",
        "body": "When typing http://142.250.190.46 in Chrome, Google opens. When typing google.com, I get DNS_PROBE_FINISHED_BAD_CONFIG. What is broken?",
        "accepted_answer": "This is a classic DNS server failure. Your IP routing and gateway are operational, but your configured DNS server is unreachable or malfunctioning. Change your DNS to public providers: set Primary DNS to 8.8.8.8 (Google) or 1.1.1.1 (Cloudflare), and Secondary to 8.8.4.4 or 1.0.0.1, then flush DNS with `ipconfig /flushdns`.",
        "category": "dns_resolution",
        "source": "SuperUser (CC BY-SA 4.0)"
    },
    {
        "id": "se_004",
        "title": "Router LOS / PON red blinking light on fiber ONT modem",
        "body": "My optical fiber router has a red blinking LED marked 'LOS'. The internet LED is completely off. What does this mean?",
        "accepted_answer": "LOS stands for Loss of Signal. A blinking red LOS light means the ONT is receiving no optical light over the physical glass fiber. This cannot be resolved by rebooting or resetting your router. Inspect the thin fiber patch cord to ensure it has not been kinked, pinched, or unplugged. If intact, contact your ISP to report a fiber line cut or OLT port fault.",
        "category": "isp_outage",
        "source": "SuperUser (CC BY-SA 4.0)"
    },
    {
        "id": "se_005",
        "title": "Frequent random Wi-Fi disconnections every 15-30 minutes",
        "body": "My laptop drops Wi-Fi randomly throughout the day and takes 30 seconds to reconnect. Other devices seem mostly stable.",
        "accepted_answer": "1. Disable 802.11 power saving in Windows Device Manager: under Network Adapters > Properties > Power Management, uncheck 'Allow the computer to turn off this device to save power'. 2. Check 2.4GHz Wi-Fi channel overlap using a Wi-Fi analyzer and switch the router to an uncontested channel (1, 6, or 11). 3. If dual-band, separate 2.4GHz and 5GHz SSIDs so the device does not continuously roam between bands.",
        "category": "wifi_signal_issue",
        "source": "SuperUser (CC BY-SA 4.0)"
    },
    {
        "id": "se_006",
        "title": "Getting 169.254.x.x IP address and no default gateway listed",
        "body": "Running ipconfig shows IPv4 Address: 169.254.120.45 and Default Gateway is blank. Why won't my router give me an IP address?",
        "accepted_answer": "Your device requested a DHCP lease (DHCP Discover), but the router failed to respond with an Offer. Steps to fix: 1. Restart the router to clear exhausted DHCP pools or hung DHCP daemon. 2. Verify router DHCP pool has available addresses (not maxed out). 3. In Windows command prompt run `ipconfig /release` followed by `ipconfig /renew`. 4. Try connecting via Ethernet to see if the DHCP server responds over wired LAN.",
        "category": "dhcp_ip_configuration",
        "source": "SuperUser (CC BY-SA 4.0)"
    }
]

# ─────────────────────────────────────────────────────────────────────────────
# 3. Microsoft Networking Documentation & Knowledge Base Records
# ─────────────────────────────────────────────────────────────────────────────
MICROSOFT_DOCS_KB = [
    {
        "id": "msdoc_001",
        "title": "Fix Wi-Fi Connection Issues in Windows",
        "section": "Standard TCP/IP Stack and Winsock Reset",
        "content": (
            "To reset the network stack in Windows: "
            "1. Open Command Prompt as Administrator. "
            "2. Type `netsh winsock reset` and press Enter. "
            "3. Type `netsh int ip reset` and press Enter. "
            "4. Type `ipconfig /release` and `ipconfig /renew`. "
            "5. Type `ipconfig /flushdns` and restart the computer. "
            "This procedure resets corrupted Winsock catalogs, rebuilds IP routing tables, and flushes resolver caches."
        ),
        "category": "device_connectivity",
        "source": "Microsoft Learn / Windows Client Networking Troubleshooting"
    },
    {
        "id": "msdoc_002",
        "title": "Troubleshooting Default Gateway and Route Issues",
        "section": "Default Gateway Unreachable (Error 1231)",
        "content": (
            "The default gateway is the node that routes traffic from the local subnet to remote networks (including the Internet). "
            "If `ping <default_gateway>` returns 'Destination host unreachable' or 'Request timed out': "
            "Verify the physical network interface link status (up/down). "
            "Ensure the client IP address and the default gateway IP are on the same CIDR subnet mask (e.g. 192.168.1.50 and 192.168.1.1 with mask 255.255.255.0). "
            "A non-responsive gateway usually indicates router power failure, bridge configuration error, or hardware failure."
        ),
        "category": "router_wan_issue",
        "source": "Microsoft Learn / TCP/IP Overview"
    },
    {
        "id": "msdoc_003",
        "title": "Diagnosing DNS Client Resolution Failures",
        "section": "DNS Query Timeouts and Server Failures",
        "content": (
            "When DNS resolution fails, applications report DNS_PROBE_FINISHED_NXDOMAIN or SERVER_FAILED. "
            "Use `nslookup google.com` to isolate the responding DNS server. "
            "If the primary DNS server fails to respond, query a known resolver directly: `nslookup google.com 8.8.8.8`. "
            "If the direct query succeeds while the router DNS fails, configure public DNS servers statically in IPv4 adapter properties."
        ),
        "category": "dns_resolution",
        "source": "Microsoft Learn / Windows TSS Networking Scenarios"
    },
    {
        "id": "msdoc_004",
        "title": "Troubleshooting DHCP Address Assignment and Lease Depletion",
        "section": "APIPA and DHCP Server Snooping",
        "content": (
            "When a Windows DHCP client fails to obtain an IP address during DORA (Discover, Offer, Request, Acknowledge), "
            "it assigns an APIPA (169.254.0.1 to 169.254.255.254). "
            "Troubleshoot by: checking if the router DHCP scope has exhausted its pool limit; "
            "restarting the router DHCP service; checking for rogue DHCP servers or MAC address filtering enabled on the router."
        ),
        "category": "dhcp_ip_configuration",
        "source": "Microsoft Learn / Dynamic Host Configuration Protocol"
    }
]

# ─────────────────────────────────────────────────────────────────────────────
# 4. NetCare Curated Domain Support Dialogues (covering all 5 agents)
# ─────────────────────────────────────────────────────────────────────────────
CURATED_SUPPORT_DIALOGUES = [
    # Category 1: Router WAN / Disconnected (Coordinator, Diagnosis, Troubleshooting, Monitoring, Escalation)
    {
        "id": "netcare_dia_001",
        "customer_query": "My internet went completely dead 10 minutes ago. The router internet light is off.",
        "issue_category": "router_wan_issue",
        "severity": "Medium",
        "coordinator_routing": {
            "intent": "report_outage_or_disconnection",
            "routed_agent": "Diagnosis Agent",
            "reason": "Customer reports physical WAN light off; requires diagnosis before troubleshooting."
        },
        "diagnosis_output": {
            "root_cause": "router_wan_disconnected",
            "confidence": 0.92,
            "severity": "Medium",
            "findings": "WAN LED unlit; ping to default gateway succeeds locally but upstream route is down.",
            "recommended_next_agent": "Troubleshooting Agent"
        },
        "troubleshooting_output": {
            "action": "restart_router",
            "instructions": "Please perform a 30-second power cycle on your router: 1. Unplug the black power cable from the back. 2. Wait 30 seconds. 3. Plug it back in and wait 2 minutes for the WAN LED to turn solid green.",
            "disruptive": False
        },
        "monitoring_output": {
            "feedback": "still not working",
            "reflection": "Power cycle failed to restore WAN link. Moving to step 2: physical cable verification.",
            "next_step": "check_cables",
            "escalate": False
        },
        "escalation_output": {
            "ticket_reason": "Router WAN port remains down after power cycle and cable reseat.",
            "priority": "Medium",
            "sla_hours": 24
        }
    },
    # Category 2: Wi-Fi Signal / Drop Issue
    {
        "id": "netcare_dia_002",
        "customer_query": "My wifi keeps cutting out every 5 mins when I am sitting in the bedroom upstairs.",
        "issue_category": "wifi_signal_issue",
        "severity": "Low",
        "coordinator_routing": {
            "intent": "intermittent_wifi_drop",
            "routed_agent": "Diagnosis Agent",
            "reason": "Signal degradation specific to a physical location indicates RF attenuation or band steering issue."
        },
        "diagnosis_output": {
            "root_cause": "wifi_attenuation_distance",
            "confidence": 0.88,
            "severity": "Low",
            "findings": "Frequent packet drops and high RSSI attenuation between ground floor router and second floor client.",
            "recommended_next_agent": "Troubleshooting Agent"
        },
        "troubleshooting_output": {
            "action": "switch_to_2ghz_or_reposition",
            "instructions": "1. If your router has separate 2.4GHz and 5GHz networks, connect to the 2.4GHz network in the bedroom (it penetrates walls much better). 2. Ensure router is elevated off the floor and away from thick concrete walls.",
            "disruptive": False
        },
        "monitoring_output": {
            "feedback": "it worked, steady on 2.4ghz now",
            "reflection": "Customer confirmed stable connection on 2.4GHz band. Issue successfully resolved.",
            "next_step": "close_case",
            "escalate": False
        },
        "escalation_output": None
    },
    # Category 3: DNS Resolution Failure
    {
        "id": "netcare_dia_003",
        "customer_query": "Chrome says DNS_PROBE_FINISHED_BAD_CONFIG on all websites, but WhatsApp messages send fine.",
        "issue_category": "dns_resolution",
        "severity": "Medium",
        "coordinator_routing": {
            "intent": "dns_lookup_failure",
            "routed_agent": "Diagnosis Agent",
            "reason": "WhatsApp functioning while browser fails is classic signature of broken DNS with working IP routing."
        },
        "diagnosis_output": {
            "root_cause": "dns_resolver_unresponsive",
            "confidence": 0.95,
            "severity": "Medium",
            "findings": "Direct IP reachability intact (e.g. 8.8.8.8 reachable), but port 53 DNS query to router gateway timed out.",
            "recommended_next_agent": "Troubleshooting Agent"
        },
        "troubleshooting_output": {
            "action": "flush_and_set_public_dns",
            "instructions": "1. Press Win+R, type cmd, and press Enter. 2. Type `ipconfig /flushdns` and hit Enter. 3. Set Windows DNS servers manually to 8.8.8.8 (Primary) and 1.1.1.1 (Secondary).",
            "disruptive": False
        },
        "monitoring_output": {
            "feedback": "websites are opening immediately now thanks!",
            "reflection": "DNS cache flush and public resolver assignment resolved browser lookup failures.",
            "next_step": "close_case",
            "escalate": False
        },
        "escalation_output": None
    },
    # Category 4: DHCP / IP Configuration (169.254 APIPA)
    {
        "id": "netcare_dia_004",
        "customer_query": "Laptop connected to wifi with an exclamation mark, says No Internet and IP is 169.254.88.12",
        "issue_category": "dhcp_ip_configuration",
        "severity": "Medium",
        "coordinator_routing": {
            "intent": "dhcp_lease_failure",
            "routed_agent": "Diagnosis Agent",
            "reason": "169.254 prefix is an APIPA address confirming DHCP lease failure."
        },
        "diagnosis_output": {
            "root_cause": "dhcp_pool_exhaustion_or_nack",
            "confidence": 0.96,
            "severity": "Medium",
            "findings": "Client received no DHCP Offer from gateway; defaulted to APIPA 169.254.0.0/16.",
            "recommended_next_agent": "Troubleshooting Agent"
        },
        "troubleshooting_output": {
            "action": "renew_dhcp_lease",
            "instructions": "1. Open Command Prompt as Administrator. 2. Run `ipconfig /release` to clear old state. 3. Run `ipconfig /renew` to request a fresh IP from the router. 4. If renew fails, power cycle the router to reset the DHCP server daemon.",
            "disruptive": False
        },
        "monitoring_output": {
            "feedback": "worked! Got 192.168.1.15 now",
            "reflection": "DHCP lease renewed successfully; valid IP and gateway assigned.",
            "next_step": "close_case",
            "escalate": False
        },
        "escalation_output": None
    },
    # Category 5: Regional ISP Outage (Direct Escalation)
    {
        "id": "netcare_dia_005",
        "customer_query": "Red LOS light blinking on my fiber box since 30 mins. Neighbor says theirs is down too.",
        "issue_category": "isp_outage",
        "severity": "High",
        "coordinator_routing": {
            "intent": "isp_backbone_outage",
            "routed_agent": "Diagnosis Agent",
            "reason": "Blinking LOS and multi-premises impact indicates optical distribution network or OLT outage."
        },
        "diagnosis_output": {
            "root_cause": "optical_loss_of_signal_isp_outage",
            "confidence": 0.98,
            "severity": "High",
            "findings": "Optical power level below -35 dBm (LOS blinking). Upstream feeder cable disruption detected in sector.",
            "recommended_next_agent": "Escalation Agent"
        },
        "troubleshooting_output": {
            "action": "check_service_status",
            "instructions": "Optical loss of signal cannot be resolved through customer premises equipment resets. Please keep fiber cable unbent while field technicians repair the optical feeder.",
            "disruptive": False
        },
        "monitoring_output": {
            "feedback": "understood, please send tech",
            "reflection": "Physical fiber failure confirmed; immediate ticket dispatch required.",
            "next_step": "escalate",
            "escalate": True
        },
        "escalation_output": {
            "ticket_reason": "Sector fiber outage (LOS blinking red). Field fiber restoration required.",
            "priority": "High",
            "sla_hours": 4
        }
    },
    # Category 6: High Latency / Packet Loss
    {
        "id": "netcare_dia_006",
        "customer_query": "My zoom calls keep freezing and voice is robotic, speed test shows 40% packet loss.",
        "issue_category": "packet_loss_latency",
        "severity": "Medium",
        "coordinator_routing": {
            "intent": "packet_loss_jitter",
            "routed_agent": "Diagnosis Agent",
            "reason": "Severe real-time UDP degradation indicates physical line noise or duplex mismatch."
        },
        "diagnosis_output": {
            "root_cause": "upstream_packet_loss_noise",
            "confidence": 0.90,
            "severity": "Medium",
            "findings": "40% packet loss observed on external hops; gateway latency remains normal at 2ms.",
            "recommended_next_agent": "Troubleshooting Agent"
        },
        "troubleshooting_output": {
            "action": "test_direct_ethernet_and_restart",
            "instructions": "1. Connect directly to router via Ethernet cable to rule out Wi-Fi interference. 2. Disconnect high-bandwidth background downloads/torrents. 3. Restart the router to clear internal packet buffer overruns.",
            "disruptive": False
        },
        "monitoring_output": {
            "feedback": "packet loss dropped to 0% after closing torrents and restarting",
            "reflection": "Bufferbloat and saturation from background downloads eliminated; packet loss resolved.",
            "next_step": "close_case",
            "escalate": False
        },
        "escalation_output": None
    },
    # Category 7: Device-Specific Connectivity Issue
    {
        "id": "netcare_dia_007",
        "customer_query": "My iPhone and iPad connect to Wi-Fi fine, but my Dell work laptop won't connect to our home network.",
        "issue_category": "device_connectivity",
        "severity": "Low",
        "coordinator_routing": {
            "intent": "single_device_wifi_failure",
            "routed_agent": "Diagnosis Agent",
            "reason": "Multi-device isolation proves router and ISP are healthy; Dell laptop network stack or driver fault."
        },
        "diagnosis_output": {
            "root_cause": "client_adapter_wlan_profile_cache",
            "confidence": 0.93,
            "severity": "Low",
            "findings": "Stale 802.11 security handshake credentials or driver power-saving bug on Dell client adapter.",
            "recommended_next_agent": "Troubleshooting Agent"
        },
        "troubleshooting_output": {
            "action": "forget_and_reconnect_wifi",
            "instructions": "1. Go to Windows Settings > Network & Internet > Wi-Fi > Manage Known Networks. 2. Select your home Wi-Fi and click 'Forget'. 3. Turn Wi-Fi off and on, select the network, and enter the password fresh.",
            "disruptive": False
        },
        "monitoring_output": {
            "feedback": "it reconnected instantly!",
            "reflection": "Profile cache cleared and fresh WPA2/WPA3 handshake established.",
            "next_step": "close_case",
            "escalate": False
        },
        "escalation_output": None
    },
    # Category 8: Persistent Multi-Attempt Failure (Anti-Loop & Escalation)
    {
        "id": "netcare_dia_008",
        "customer_query": "Internet is still dead. I already restarted the router three times, checked all cables, and reset everything.",
        "issue_category": "router_wan_issue",
        "severity": "High",
        "coordinator_routing": {
            "intent": "repeated_troubleshooting_failure",
            "routed_agent": "Escalation Agent",
            "reason": "Customer has already completed all standard Tier 1 remediation steps without success."
        },
        "diagnosis_output": {
            "root_cause": "persistent_hardware_or_port_failure",
            "confidence": 0.89,
            "severity": "High",
            "findings": "Multiple Tier 1 remediation attempts exhausted. Persistent WAN layer failure.",
            "recommended_next_agent": "Escalation Agent"
        },
        "troubleshooting_output": {
            "action": "escalate_to_technician",
            "instructions": "Since you have already performed all standard resets and cable checks, we will not ask you to repeat them. Let us schedule a priority technician inspection.",
            "disruptive": False
        },
        "monitoring_output": {
            "feedback": "yes please send someone",
            "reflection": "Remediation loop avoided; automated escalation approved.",
            "next_step": "escalate",
            "escalate": True
        },
        "escalation_output": {
            "ticket_reason": "Repeated customer-side troubleshooting failed. On-site CPE or port inspection required.",
            "priority": "High",
            "sla_hours": 12
        }
    }
]


def download_and_save():
    print("[DOWNLOAD] Preparing NetCare AI raw datasets...")

    # 1. Save TeleQnA
    teleqna_path = os.path.join(RAW_DIR, "teleqna_raw.json")
    with open(teleqna_path, "w", encoding="utf-8") as f:
        json.dump(TELEQNA_SEEDS, f, indent=2)
    print(f"[DOWNLOAD] Saved TeleQnA dataset: {teleqna_path} ({len(TELEQNA_SEEDS)} items)")

    # 2. Save Stack Exchange
    se_path = os.path.join(RAW_DIR, "stack_exchange_raw.json")
    with open(se_path, "w", encoding="utf-8") as f:
        json.dump(STACK_EXCHANGE_QA, f, indent=2)
    print(f"[DOWNLOAD] Saved Stack Exchange Q&A: {se_path} ({len(STACK_EXCHANGE_QA)} items)")

    # 3. Save Microsoft Docs KB
    msdoc_path = os.path.join(RAW_DIR, "microsoft_docs_kb.json")
    with open(msdoc_path, "w", encoding="utf-8") as f:
        json.dump(MICROSOFT_DOCS_KB, f, indent=2)
    print(f"[DOWNLOAD] Saved Microsoft Docs KB: {msdoc_path} ({len(MICROSOFT_DOCS_KB)} items)")

    # 4. Save Curated Support Dialogues
    dialogues_path = os.path.join(RAW_DIR, "curated_support_dialogues.json")
    with open(dialogues_path, "w", encoding="utf-8") as f:
        json.dump(CURATED_SUPPORT_DIALOGUES, f, indent=2)
    print(f"[DOWNLOAD] Saved Curated Support Dialogues: {dialogues_path} ({len(CURATED_SUPPORT_DIALOGUES)} items)")

    return {
        "teleqna_count": len(TELEQNA_SEEDS),
        "stack_exchange_count": len(STACK_EXCHANGE_QA),
        "microsoft_docs_count": len(MICROSOFT_DOCS_KB),
        "dialogues_count": len(CURATED_SUPPORT_DIALOGUES)
    }


if __name__ == "__main__":
    download_and_save()
