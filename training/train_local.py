"""
training/train_local.py — NetCare AI
Local Supervised Training Pipeline for Domain-Adapted NetCare AI Classification Engine.
- Employs hybrid feature representation:
    1. Statistical Word & Subword TF-IDF Feature Union
    2. Domain Telecommunications & Diagnostic Feature Extractors
- Tracks multi-epoch loss & validation convergence over 5 epochs
- Saves trained checkpoint to checkpoints/netcare_intent_model.joblib
- Generates training history artifact for the Model Performance Dashboard
"""

import os
import sys
import json
import re
import joblib
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import FeatureUnion
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, log_loss

PROCESSED_DIR = os.path.join(BASE_DIR, "datasets", "processed")
CHECKPOINTS_DIR = os.path.join(BASE_DIR, "checkpoints")
EVAL_RESULTS_DIR = os.path.join(BASE_DIR, "evaluation_results")

os.makedirs(CHECKPOINTS_DIR, exist_ok=True)
os.makedirs(EVAL_RESULTS_DIR, exist_ok=True)

DOMAIN_DIAGNOSTIC_RULES = {
    "dhcp_ip_configuration": [
        r"\bdhcp\b", r"169\.254", r"\bapipa\b", r"no ip\b", r"ip config",
        r"ip conflict", r"valid ip", r"obtaining ip", r"lease", r"dora"
    ],
    "isp_outage": [
        r"\blos\b", r"optical", r"fiber cut", r"society", r"colony",
        r"neighbor", r"neighborhood", r"\bpon\b", r"area-wide", r"area outage", r"backbone"
    ],
    "dns_resolution": [
        r"\bdns\b", r"dns_probe", r"resolve", r"domain name", r"err_name",
        r"nameserver", r"nxdomain", r"numeric ip", r"host name", r"nslookup"
    ],
    "packet_loss_latency": [
        r"packet loss", r"ping spike", r"latency", r"jitter", r"\blag\b",
        r"buffering", r"zoom", r"freezing", r"robotic", r"round-trip"
    ],
    "wifi_signal_issue": [
        r"weak\b", r"2\.4g", r"5g", r"\bbars\b", r"attenuation",
        r"bedroom", r"range\b", r"signal\b", r"cutting out", r"balcony"
    ],
    "device_connectivity": [
        r"one computer", r"only my", r"other devices", r"work laptop",
        r"roommate", r"specific", r"adapter disabled", r"toggle in windows", r"single device"
    ],
    "router_wan_issue": [
        r"\bwan\b", r"internet light", r"router led", r"pppoe",
        r"broadband stopped", r"completely dead", r"modem wan", r"red light on router"
    ]
}


def extract_domain_features(texts):
    """Extracts dense diagnostic feature indicators for telecom error patterns."""
    feature_matrix = []
    for t in texts:
        tl = t.lower()
        row = []
        for cat, patterns in DOMAIN_DIAGNOSTIC_RULES.items():
            score = sum(3.0 for p in patterns if re.search(p, tl))
            row.append(score)
        feature_matrix.append(row)
    return np.array(feature_matrix, dtype=np.float32)


def load_dataset(filename):
    filepath = os.path.join(PROCESSED_DIR, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    texts = [item["text"] for item in data]
    labels = [item["label"] for item in data]
    return texts, labels


def train():
    print("[TRAIN_LOCAL] Loading NetCare AI processed datasets...")
    train_texts, train_labels = load_dataset("classification_train.json")
    val_texts, val_labels = load_dataset("classification_val.json")

    unique_classes = sorted(list(set(train_labels + val_labels)))
    class_to_idx = {c: i for i, c in enumerate(unique_classes)}
    y_train_idx = np.array([class_to_idx[l] for l in train_labels])
    y_val_idx = np.array([class_to_idx[l] for l in val_labels])

    # Feature Union: word (1-3) and subword char_wb (3-6)
    tfidf = FeatureUnion([
        ("word", TfidfVectorizer(ngram_range=(1, 3), max_features=3500, sublinear_tf=True)),
        ("char", TfidfVectorizer(ngram_range=(3, 6), analyzer="char_wb", max_features=4000, sublinear_tf=True))
    ])

    X_train_tfidf = tfidf.fit_transform(train_texts).toarray()
    X_val_tfidf = tfidf.transform(val_texts).toarray()

    F_train = extract_domain_features(train_texts)
    F_val = extract_domain_features(val_texts)

    X_train_all = np.hstack([X_train_tfidf, F_train])
    X_val_all = np.hstack([X_val_tfidf, F_val])

    # Multi-epoch training simulation with SGD warm_start
    clf = SGDClassifier(
        loss="log_loss",
        penalty="l2",
        alpha=2e-5,
        learning_rate="adaptive",
        eta0=0.08,
        max_iter=1,
        warm_start=True,
        random_state=42
    )

    epochs = 5
    history = []
    best_val_acc = 0.0
    best_model_checkpoint = None

    print(f"\n[TRAIN_LOCAL] Training over {epochs} epochs...")
    print("=" * 70)
    print(f"{'Epoch':<8}{'Train Loss':<14}{'Val Loss':<14}{'Val Acc':<12}{'Macro F1':<10}")
    print("-" * 70)

    for epoch in range(1, epochs + 1):
        for _ in range(20):
            clf.partial_fit(X_train_all, y_train_idx, classes=np.arange(len(unique_classes)))

        train_probs = clf.predict_proba(X_train_all)
        val_probs = clf.predict_proba(X_val_all)

        train_loss = float(log_loss(y_train_idx, train_probs, labels=np.arange(len(unique_classes))))
        val_loss = float(log_loss(y_val_idx, val_probs, labels=np.arange(len(unique_classes))))

        val_preds = clf.predict(X_val_all)
        val_acc = float(accuracy_score(y_val_idx, val_preds))
        precision, recall, f1, _ = precision_recall_fscore_support(y_val_idx, val_preds, average="macro", zero_division=0)

        epoch_stats = {
            "epoch": epoch,
            "train_loss": round(train_loss, 4),
            "val_loss": round(val_loss, 4),
            "val_accuracy": round(val_acc * 100, 2),
            "precision": round(float(precision), 4),
            "recall": round(float(recall), 4),
            "macro_f1": round(float(f1), 4)
        }
        history.append(epoch_stats)

        print(f"{epoch:<8}{train_loss:<14.4f}{val_loss:<14.4f}{val_acc*100:<12.1f}%{f1:<10.4f}")

        if val_acc >= best_val_acc:
            best_val_acc = val_acc
            best_model_checkpoint = {
                "tfidf": tfidf,
                "classifier": clf,
                "domain_rules": DOMAIN_DIAGNOSTIC_RULES,
                "classes": unique_classes,
                "epoch": epoch,
                "val_accuracy": val_acc
            }

    print("=" * 70)

    # Save best checkpoint
    model_path = os.path.join(CHECKPOINTS_DIR, "netcare_intent_model.joblib")
    joblib.dump(best_model_checkpoint, model_path)
    print(f"\n[TRAIN_LOCAL] Best validation checkpoint saved to: {model_path} (Val Acc: {best_val_acc*100:.1f}%)")

    # Save training history
    history_path = os.path.join(EVAL_RESULTS_DIR, "training_history.json")
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump({
            "model_name": "NetCare-Domain-Adapted-Classifier",
            "epochs": epochs,
            "best_epoch": best_model_checkpoint["epoch"],
            "best_val_acc": round(best_val_acc * 100, 2),
            "history": history
        }, f, indent=2)
    print(f"[TRAIN_LOCAL] Saved training history: {history_path}")

    return best_model_checkpoint


if __name__ == "__main__":
    train()
