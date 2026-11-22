"""
model/configuration.py — NetCare AI
Model configuration parameters, paths, thresholds, and class definitions.
"""

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKPOINTS_DIR = os.path.join(BASE_DIR, "checkpoints")
MODEL_CHECKPOINT_PATH = os.path.join(CHECKPOINTS_DIR, "netcare_intent_model.joblib")

MODEL_NAME = "NetCare-Domain-Adapted-Model-v1.0"
BASE_FOUNDATION_CANDIDATE = "Qwen2.5-3B-Instruct"

CLASSES = [
    "device_connectivity",
    "dhcp_ip_configuration",
    "dns_resolution",
    "isp_outage",
    "packet_loss_latency",
    "router_wan_issue",
    "wifi_signal_issue"
]

CONFIDENCE_THRESHOLD = 0.65
MAX_RETRY_ATTEMPTS = 3
TARGET_ACCURACY = 95.5
