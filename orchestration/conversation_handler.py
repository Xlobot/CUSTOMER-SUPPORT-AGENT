"""
orchestration/conversation_handler.py — NetCare AI
Re-exports from model.conversation_handler for clean module layering and zero circular imports.
"""

from model.conversation_handler import (
    is_gibberish,
    is_greeting,
    is_identity_question,
    is_technical_question,
    classify_message_intent,
    generate_dynamic_response,
    GREETING_SET,
    COURTESY_SET,
    HOLD_ON_SET,
    IDENTITY_KEYWORDS,
    TECHNICAL_TOPICS,
    NETWORKING_KEYWORDS
)
