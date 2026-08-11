# Baseline (no-skill) response: kms-rotation-true-failure

This file captures what a generic assistant produces WITHOUT the
securityhub-finding-troubleshooter skill loaded — the contrast that
proves the skill adds structure (deterministic VERDICT, layer
identification, evidence-backed root cause, standard-driven probe
order).

---

Your KMS key doesn't have rotation enabled. Go to the KMS console and
turn on rotation for the key. It's a one-click setting.

Make sure you rotate any data that's already encrypted if needed.
Key rotation just creates a new backing key — it doesn't re-encrypt
existing data.
