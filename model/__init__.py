"""
model package for NetCare AI.
"""

from model.inference import classify_issue, generate_agent_response
from model.model_loader import load_model, get_model_status
from model.configuration import MODEL_NAME, CLASSES
