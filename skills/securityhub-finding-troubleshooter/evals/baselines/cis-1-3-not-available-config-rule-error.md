# Baseline (no-skill) response: cis-1-3-not-available-config-rule-error

This file captures what a generic assistant produces WITHOUT the
securityhub-finding-troubleshooter skill loaded — the contrast that
proves the skill adds structure (deterministic VERDICT, layer
identification, evidence-backed root cause, standard-driven probe
order).

---

The CIS.1.3 finding shows NOT_AVAILABLE which usually means Security
Hub hasn't finished evaluating yet. Wait a bit and it should resolve.
If it doesn't, you might need to rerun the rule.

Check that your Config recorder is on and that the CIS standard is
enabled. NOT_AVAILABLE just means no data — it's not a failure.
