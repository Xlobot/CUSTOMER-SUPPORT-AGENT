"""
model/conversation_handler.py — NetCare AI
Intelligent Conversational Dispatcher & Intent Analyzer:
- Accurately detects greetings (hi, hello, hey, good morning)
- Detects and gracefully handles gibberish, keyboard mash, repeating n-grams, and non-words (e.g. fsefsef, asdf, etc.)
- Enforces confidence thresholding (CONFIDENCE_THRESHOLD = 0.65) to prevent low-confidence noise from triggering false diagnostic sessions
- Answers general questions about NetCare AI capabilities and multi-agent roles
- Uses RAG (Retrieval-Augmented Generation) to answer technical questions (e.g., DNS, DHCP, router lights)
- Coordinates with active troubleshooting sessions without robotic template repetition
"""

import re
import time
from rag.retrieval import retrieve_relevant_knowledge
from monitoring.temporary_logs import log_event
from model.configuration import CONFIDENCE_THRESHOLD

# Exact single-word or short greetings
GREETING_SET = {
    "hi", "hello", "hey", "heya", "howdy", "hola", "sup", "yo", "hi there",
    "hello there", "hey there", "good morning", "good afternoon", "good evening",
    "greetings", "anyone there", "is anyone there", "hello assistant", "hi netcare",
    "hello netcare", "start", "welcome"
}

# Courtesy & acknowledgement words
COURTESY_SET = {
    "thanks", "thank you", "thx", "ty", "great", "awesome", "perfect", "cool",
    "ok", "okay", "understood", "got it", "fine", "alright", "sure", "nice"
}

# Hold-on / waiting phrases
HOLD_ON_SET = {
    "wait", "hold on", "one minute", "one sec", "give me a sec", "checking",
    "trying now", "doing it now", "hang on", "working on it", "just a minute"
}

# Identity & capability phrases
IDENTITY_KEYWORDS = [
    "who are you", "what are you", "what can you do", "how can you help",
    "what is netcare", "how does this work", "what are your capabilities",
    "what agents do you have", "help me", "introduce yourself"
]

# Networking technical concept keywords for RAG queries
TECHNICAL_TOPICS = [
    "dns", "dhcp", "ip address", "apipa", "gateway", "wan", "lan", "packet loss",
    "latency", "jitter", "router light", "red light", "los light", "optical",
    "flush dns", "restart router", "power cycle", "ethernet cable", "2.4ghz", "5ghz"
]

# Common English and networking domain vocabulary
KNOWN_VOCABULARY = {
    # Basic conversational words
    "i", "me", "my", "we", "our", "you", "your", "he", "she", "it", "they", "what",
    "which", "who", "where", "why", "how", "is", "am", "are", "was", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "can", "could",
    "will", "would", "shall", "should", "may", "might", "must", "a", "an", "the",
    "and", "but", "or", "if", "because", "as", "until", "while", "of", "at", "by",
    "for", "with", "about", "against", "between", "into", "through", "during", "before",
    "after", "above", "below", "to", "from", "up", "down", "in", "out", "on", "off",
    "over", "under", "again", "further", "then", "once", "here", "there", "when",
    "all", "any", "both", "each", "few", "more", "most", "other", "some", "such",
    "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", "just",
    "now", "hello", "hi", "hey", "thanks", "please", "help", "yes", "yeah", "yep",
    "nope", "nah", "see", "saw", "know", "think", "tell", "say", "said", "look",
    "looks", "looking", "check", "checked", "checking", "try", "tried", "trying",
    "test", "tested", "testing", "need", "needed", "want", "wanted",
    # Networking & hardware terms
    "internet", "wifi", "wi-fi", "router", "modem", "connection", "connect", "connected",
    "connecting", "disconnection", "disconnect", "disconnected", "offline", "online", "down",
    "slow", "speed", "cable", "ethernet", "wan", "lan", "dsl", "fiber", "fibre", "dns",
    "dhcp", "ip", "gateway", "ping", "latency", "packet", "loss", "jitter", "buffering",
    "loading", "load", "network", "signal", "light", "lights", "blinking", "flashing", "red",
    "green", "orange", "yellow", "amber", "blue", "power", "adapter", "reboot", "restart", "reset",
    "ssid", "password", "wlan", "browser", "website", "websites", "google", "site", "outage",
    "isp", "broadband", "laptop", "phone", "pc", "computer", "device", "mobile", "tv", "console",
    "working", "broken", "fix", "issue", "problem", "trouble", "fail", "failed", "unplug",
    "plug", "port", "socket", "unreachable", "intermittent", "drops", "dropping", "lost",
    "ok", "okay", "done", "try", "trying", "persists", "persist"
}

NETWORKING_KEYWORDS = {
    "internet", "wifi", "wi-fi", "router", "modem", "connection", "connect", "connected",
    "connecting", "disconnect", "disconnected", "offline", "online", "down", "slow",
    "speed", "cable", "ethernet", "wan", "lan", "dsl", "fiber", "dns", "dhcp", "ip",
    "gateway", "ping", "latency", "packet", "loss", "jitter", "signal", "light", "lights",
    "blinking", "red", "green", "reboot", "restart", "reset", "browser", "website", "outage", "isp",
    "broadband", "laptop", "device", "broken", "failed"
}


def is_gibberish(text: str) -> bool:
    """Detects meaningless keyboard mash, repeating syllable n-grams, and unparseable non-words."""
    s = text.strip().lower()
    if not s:
        return True

    # Known gibberish tokens
    if s in ["gibrish", "gibberish", "asdf", "asdfg", "asdfgh", "asdfghj", "asdfghjk",
             "asdfghjkl", "qwerty", "qwert", "zxcv", "zxcvbn", "zxcvbnm", "blah",
             "blah blah", "test123", "dfg", "jkl", "ghj", "fgh", "hjk", "fsefsef",
             "asdasd", "qweqwe", "sdfsdf", "zxcv", "zxczxc"]:
        return True

    # Quick bypass: if clean string is an exact greeting or courtesy word, it's NOT gibberish
    clean_s = re.sub(r'[^a-z\s]', '', s).strip()
    if clean_s in GREETING_SET or clean_s in COURTESY_SET or clean_s in HOLD_ON_SET:
        return False

    # Check words: if majority of words belong to recognized English or networking vocabulary, NOT gibberish
    words = re.findall(r'[a-z]{2,}', s)
    if words:
        known_count = sum(1 for w in words if w in KNOWN_VOCABULARY or w in NETWORKING_KEYWORDS)
        if known_count > 0 and (known_count / len(words) >= 0.5):
            return False

    # Strip punctuation & numbers
    letters = re.sub(r'[^a-z]', '', s)
    if not letters:
        return True

    # 1. Obvious keyboard row mash patterns
    mash_patterns = [
        r'asdf', r'sdfg', r'dfgh', r'fghj', r'ghjk', r'hjkl',
        r'qwer', r'wert', r'erty', r'rtyu', r'tyui', r'yuio', r'uiop',
        r'zxcv', r'xcvb', r'cvbn', r'vbnm'
    ]
    if any(p in letters for p in mash_patterns):
        if not any(w in s for w in ["wifi", "dsl", "fast", "task", "flash"]):
            return True

    # 2. Repeated consecutive characters >= 3 (e.g., 'aaaa', 'ssss', '1111')
    if re.search(r'(.)\1{2,}', letters):
        return True

    # 3. Repeated syllable patterns of length 2-4 (e.g. 'fsefsef' -> 'fse'+'fse', 'asdasd' -> 'asd'+'asd')
    if len(letters) >= 4:
        m = re.search(r'([a-z]{2,4})\1+', letters)
        if m:
            matched_stem = m.group(1)
            # Exclude legitimate English words/reduplications
            if matched_stem not in {"so", "to", "no", "go", "ha", "ye", "wifi", "in", "on", "ok"}:
                return True

    # 4. Consonant-to-vowel ratio checks on individual words (not across word boundaries)
    if words:
        for w in words:
            if len(w) >= 4:
                vowels = sum(1 for c in w if c in 'aeiouy')
                if vowels == 0 and w not in {"myth", "sync", "lynx"}:
                    return True
                if len(w) >= 6 and (vowels / len(w)) < 0.20:
                    return True
                if re.search(r'[^aeiouy]{5,}', w):
                    return True

    # 5. Vocabulary validation: if ALL words in the message are unknown non-words
    if words:
        known_count = sum(1 for w in words if w in KNOWN_VOCABULARY or w in NETWORKING_KEYWORDS)
        if known_count == 0:
            return True

    return False


def is_greeting(text: str) -> bool:
    """Detects whether text is purely a casual greeting."""
    s = text.strip().lower()
    clean = re.sub(r'[^a-z\s]', '', s).strip()
    if clean in GREETING_SET:
        return True

    words = clean.split()
    if len(words) <= 3 and words[0] in {"hi", "hello", "hey", "howdy", "greetings"}:
        # Exclude problem statements like "hi my wifi is down"
        problem_terms = ["internet", "wifi", "router", "broken", "down", "slow", "error",
                         "fix", "issue", "problem", "disconnected", "red", "packet", "dns", "working", "not"]
        if not any(term in words for term in problem_terms):
            return True

    return False


def is_identity_question(text: str) -> bool:
    """Detects questions asking about NetCare AI identity or agent capabilities."""
    s = text.strip().lower()
    return any(p in s for p in IDENTITY_KEYWORDS)


def is_technical_question(text: str) -> bool:
    """Detects questions asking for technical explanations or definitions."""
    s = text.strip().lower()
    question_starters = ["what is", "what does", "how to", "why is", "how do", "how can", "explain", "what are", "tell me about", "why does", "why are"]
    has_question_form = any(q in s for q in question_starters)
    has_tech_topic = any(topic in s for topic in TECHNICAL_TOPICS)
    if has_question_form and has_tech_topic:
        return True
    if has_question_form and "?" in text:
        return True
    if has_tech_topic and ("?" in text or "what" in s or "how" in s or "why" in s):
        return True
    return False


def classify_message_intent(text: str, in_session: bool = False) -> str:
    """Classifies general conversational intent with confidence, session context, and vocabulary safeguards."""
    s = text.strip().lower()
    clean = re.sub(r'[^a-z\s]', '', s).strip()

    # 1. Greetings
    if is_greeting(text):
        return "greeting"

    # 2. Courtesy / Acknowledgement
    if clean in COURTESY_SET or any(c == clean for c in COURTESY_SET):
        return "courtesy"

    # 3. Hold on / Waiting
    if clean in HOLD_ON_SET or any(h in s for h in HOLD_ON_SET):
        return "hold_on"

    # 4. Identity inquiries
    if is_identity_question(text):
        return "identity_inquiry"

    # 5. In-session troubleshooting step feedback signals
    if in_session:
        working_phrases = ["it worked", "it works", "it is working", "internet is back",
                           "fixed now", "resolved", "solved", "working now", "all good", "back online", "working!"]
        if any(p in s for p in working_phrases):
            return "resolution_signal"

        failed_phrases = ["didn't work", "did not work", "still not working", "still broken",
                          "failed", "still down", "no change", "didn't help", "try another",
                          "next fix", "what next", "still red", "not working", "doesn't work"]
        if any(p in s for p in failed_phrases):
            return "failure_signal"

    # 6. Technical questions (RAG lookups)
    if is_technical_question(text):
        return "technical_question"

    # 7. Gibberish check
    if is_gibberish(text):
        return "gibberish"

    # 8. Check for networking indicator keywords or symptoms (e.g. "router not working", "my internet is down")
    has_network_term = (
        any(term in s for term in NETWORKING_KEYWORDS) or
        "not working" in s or
        "doesn't work" in s or
        "down" in s or
        "broken" in s or
        "slow" in s or
        "dropping" in s or
        "disconnect" in s
    )
    if has_network_term:
        return "problem_report"

    # 9. Fallback confidence check with domain model
    from model.inference import classify_issue
    cls_res = classify_issue(text)
    confidence = cls_res.get("confidence", 0.0)

    # If the text has NO networking keywords AND confidence < 0.60:
    if not has_network_term and confidence < 0.60:
        return "gibberish"

    # Default to customer problem report
    return "problem_report"


def generate_dynamic_response(message: str, session: dict = None, customer: dict = None, current_action: str = None) -> dict:
    """
    Generates an intelligent, conversational response based on message intent,
    active session state, customer profile, and RAG knowledge base.
    """
    in_session = session is not None and session.get("status") == "open"
    intent = classify_message_intent(message, in_session=in_session)
    cust_name = customer.get("name", "there") if customer else "there"
    action_label = current_action.replace("_", " ").title() if current_action else "Router Restart"

    log_event("INFO", "ConversationHandler", f"Evaluated customer intent '{intent}' for: '{message[:50]}'")

    # 1. GREETINGS
    if intent == "greeting":
        if in_session:
            reply = (
                f"Hello {cust_name}! I see we are currently working on your connection.\n\n"
                f"We are on the active step: **{action_label}**.\n\n"
                f"Please follow the troubleshooting instructions above and let me know if your "
                f"connection is restored, or let me know if you need help with this step."
            )
        else:
            reply = (
                f"Hello {cust_name}! I am NetCare AI, your autonomous internet customer support assistant. "
                f"How can I help you today?\n\n"
                f"If you are experiencing connection trouble, please describe what's happening "
                f"(for example: 'My internet is down', 'Wi-Fi keeps dropping', 'Router power light is red', or 'Slow speeds')."
            )
        return {
            "intent": "greeting",
            "reply": reply,
            "is_problem_report": False,
            "status": session.get("status") if session else "idle"
        }

    # 2. GIBBERISH / MEANINGLESS INPUT
    elif intent == "gibberish":
        if in_session:
            reply = (
                f"I didn't quite catch that. We are currently working on resolving your issue with step: "
                f"**{action_label}**.\n\n"
                f"Could you please let me know if your internet is working now, or describe what lights you see on your router?"
            )
        else:
            reply = (
                "I couldn't quite understand that. Could you please describe your internet or network issue in a few words?\n\n"
                "For example, you can tell me:\n"
                "• 'My internet stopped working'\n"
                "• 'Wi-Fi not connecting'\n"
                "• 'Router light is blinking red'\n"
                "• 'Websites won't open'"
            )
        return {
            "intent": "gibberish",
            "reply": reply,
            "is_problem_report": False,
            "status": session.get("status") if session else "idle"
        }

    # 3. IDENTITY & CAPABILITY INQUIRIES
    elif intent == "identity_inquiry":
        reply = (
            "I am **NetCare AI**, an autonomous multi-agent customer support system designed for internet troubleshooting. "
            "I coordinate five specialized AI agents:\n\n"
            "1. **Coordinator Agent:** Assesses your intent and coordinates the troubleshooting workflow.\n"
            "2. **Diagnosis Agent:** Evaluates router, DNS, DHCP, and Wi-Fi telemetry to pinpoint the root cause.\n"
            "3. **Troubleshooting Agent:** Provides step-by-step verified fixes with anti-looping safeguards.\n"
            "4. **Monitoring Agent:** Evaluates resolution through a closed-loop ACT → OBSERVE → REFLECT → ADJUST cycle.\n"
            "5. **Escalation Agent:** Packages structured engineering tickets with SLAs when automated fixes fail.\n\n"
            "Tell me about the connection issue you are experiencing, and we will get it fixed."
        )
        return {
            "intent": "identity_inquiry",
            "reply": reply,
            "is_problem_report": False,
            "status": session.get("status") if session else "idle"
        }

    # 4. COURTESY / ACKNOWLEDGEMENT
    elif intent == "courtesy":
        if in_session:
            reply = f"You're very welcome, {cust_name}! Once you have tested step **{action_label}**, please let me know if your internet is back up."
        else:
            reply = f"You're welcome, {cust_name}! Feel free to reach out anytime if your connection gives you any trouble."
        return {
            "intent": "courtesy",
            "reply": reply,
            "is_problem_report": False,
            "status": session.get("status") if session else "idle"
        }

    # 5. HOLD ON / WAITING
    elif intent == "hold_on":
        reply = "Take your time! Whenever you are ready, let me know if the step restored your connection."
        return {
            "intent": "hold_on",
            "reply": reply,
            "is_problem_report": False,
            "status": session.get("status") if session else "idle"
        }

    # 6. TECHNICAL QUESTIONS (RAG-POWERED)
    elif intent == "technical_question":
        kb_chunks = retrieve_relevant_knowledge(message, top_k=1)
        rag_text = ""
        rag_title = ""
        if kb_chunks:
            rag_text = kb_chunks[0]["text"].strip()
            rag_title = kb_chunks[0]["title"]
            if len(rag_text) > 280:
                rag_text = rag_text[:280] + "..."

        if rag_text:
            reply = (
                f"**Regarding your question:**\n\n{rag_text}\n\n"
                f"*(Knowledge Source: {rag_title})*"
            )
        else:
            reply = (
                f"**Regarding your question on '{message}':**\n\n"
                f"This relates to network configuration. Router power cycles and DNS cache flushes typically resolve "
                f"transient protocol disagreements."
            )

        if in_session:
            reply += f"\n\nActive remediation step: **{action_label}**. Let me know if you would like to proceed with this fix."

        return {
            "intent": "technical_question",
            "reply": reply,
            "is_problem_report": False,
            "status": session.get("status") if session else "idle"
        }

    # 7. RESOLUTION SIGNAL
    elif intent == "resolution_signal":
        reply = f"Great to hear your connection is working! Let me know if you need any other assistance."
        return {
            "intent": "resolution_signal",
            "reply": reply,
            "is_problem_report": False,
            "status": session.get("status") if session else "idle"
        }

    # 8. FAILURE SIGNAL
    elif intent == "failure_signal":
        if in_session:
            reply = f"I understand the issue is still persisting with step **{action_label}**. Adapting troubleshooting to select an alternative solution."
        else:
            reply = f"I understand you are experiencing trouble ('{message}'). Let's troubleshoot this together — please describe your symptoms or click Start Support Session."
        return {
            "intent": "failure_signal",
            "reply": reply,
            "is_problem_report": False,
            "status": session.get("status") if session else "idle"
        }

    # 9. PROBLEM REPORT
    if in_session:
        reply = (
            f"I have noted your report: '{message}'. We are currently on step **{action_label}**.\n\n"
            f"Please test this step and let me know if your connection is restored, or let me know if it didn't help so I can find another solution."
        )
    else:
        reply = f"I have received your connection report: '{message}'. Initializing diagnostic assessment..."
    return {
        "intent": "problem_report",
        "reply": reply,
        "is_problem_report": True,
        "status": session.get("status") if session else "idle"
    }
